"""Consumer group read positions: XGROUP CREATE/SETID, `entries-read` and `lag`, compared with real servers.

A group counts the entries it has read (`entries-read`) so that its `lag` is the stream's `entries-added` minus that.
Deleting entries (not trimming them) leaves holes that can make both unknown, which XINFO reports as nil.
"""

from __future__ import annotations

import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test import testtools

pytestmark = [
    pytest.mark.supported_server_versions(min_redis_ver="7"),
    pytest.mark.unsupported_server_types("kividb"),
]


def _add(r: ClientType, count: int, start: int = 1) -> None:
    for i in range(start, start + count):
        r.xadd("s", {"f": i}, id=f"{i}-1")


def _group(r: ClientType, name: str = "g") -> tuple[bytes, int | None, int | None]:
    group = next(g for g in r.xinfo_groups("s") if g["name"] == name.encode())
    return group["last-delivered-id"], group["entries-read"], group["lag"]


def _read(r: ClientType, count: int | None = None, name: str = "g") -> list[bytes]:
    res = r.xreadgroup(name, "c", {"s": ">"}, count=count)
    if not res:
        return []
    entries = res[b"s"][0] if isinstance(res, dict) else res[0][1]  # RESP3 gives {stream: [entries]}
    return [entry[0] for entry in entries]


def test_xgroup_setid_to_zero_rereads_every_entry(r: ClientType):
    _add(r, 3)
    r.xgroup_create("s", "g", id="$")
    r.xgroup_setid("s", "g", id="0")
    assert _group(r) == (b"0-0", None, 3)
    assert _read(r) == [b"1-1", b"2-1", b"3-1"]
    assert _group(r) == (b"3-1", 3, 0)


def test_xgroup_setid_entries_read(r: ClientType, real_server_details):
    _add(r, 3)
    r.xgroup_create("s", "g", id="0")
    _read(r)
    r.xgroup_setid("s", "g", id="2-1")
    if real_server_details.server_type == "dragonfly":
        # Dragonfly keeps the group's count unless given ENTRIESREAD.
        assert _group(r) == (b"2-1", 3, 0)
    else:
        assert _group(r) == (b"2-1", None, None)
    r.xgroup_setid("s", "g", id="2-1", entries_read=1)
    assert _group(r) == (b"2-1", 1, 2)
    r.xgroup_setid("s", "g", id="2-1", entries_read=-1)
    assert _group(r) == (b"2-1", None, None)
    with pytest.raises(Exception) as ctx:
        r.xgroup_setid("s", "g", id="2-1", entries_read=-2)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    r.xgroup_setid("s", "g", id="5")
    assert _group(r) == (b"5-0", None, None)
    r.xgroup_setid("s", "g", id="$")
    assert _group(r) == (b"3-1", None, 0)
    r.xgroup_setid("s", "g", id="1-1")
    assert _read(r) == [b"2-1", b"3-1"]
    assert _group(r) == (b"3-1", 3, 0)


@pytest.mark.supported_server_versions(min_redis_ver="8.2.3")
@pytest.mark.unsupported_server_types("valkey", "dragonfly")
def test_xgroup_entries_read_is_capped_at_entries_added(r: ClientType):
    _add(r, 3)
    r.xgroup_create("s", "g", id="0", entries_read=10)
    assert _group(r) == (b"0-0", 3, 3)  # before the first entry, the whole stream is left to read
    r.xgroup_setid("s", "g", id="2-1", entries_read=7)
    assert _group(r) == (b"2-1", 3, 0)


def test_xgroup_create_after_the_last_entry_was_deleted(r: ClientType):
    _add(r, 5)
    r.xdel("s", "5-1")
    r.xgroup_create("s", "g", id="$")
    # `$` is the last ID the stream handed out, not its last entry.
    assert _group(r) == (b"5-1", None, 0)
    r.xadd("s", {"f": 6}, id="6-1")
    assert _read(r) == [b"6-1"]
    r.xgroup_create("new", "g", id="$", mkstream=True)
    r.xadd("new", {"f": "v"}, id="1-1")
    assert r.xinfo_groups("new")[0]["lag"] == 1


def test_xinfo_groups_lag_with_deleted_entries(r: ClientType, real_server_details):
    _add(r, 10)
    r.xgroup_create("s", "g", id="0")
    r.xgroup_create("s", "h", id="0")
    _read(r, count=3)
    assert _group(r) == (b"3-1", 3, 7)
    r.xdel("s", "6-1")
    # With an entry deleted after where the groups are, their lag cannot be worked out.
    assert _group(r) == (b"3-1", 3, None)
    assert _group(r, "h") == (b"0-0", None, None)
    assert _read(r, count=2) == [b"4-1", b"5-1"]
    assert _group(r) == (b"5-1", None, None)
    assert len(_read(r, name="h")) == 9
    assert _group(r, "h") == (b"10-1", 10, 0)  # read up to the last entry, the count is known again
    r.xdel("s", "1-1", "2-1")
    r.xadd("s", {"f": 11}, id="11-1")
    assert _group(r, "h") == (b"10-1", 10, 1)
    assert _read(r) == [b"7-1", b"8-1", b"9-1", b"10-1", b"11-1"]
    assert _group(r) == (b"11-1", 11, 0)
    r.xdel("s", *[f"{i}-1" for i in range(1, 12)])
    # Redis 7.4 reports no lag for a stream with nothing left in it.
    trim_aware = real_server_details.server_type == "redis" and real_server_details.server_version >= (7, 4)
    assert _group(r, "h") == (b"10-1", 10, 0 if trim_aware else 1)


def test_xinfo_groups_lag_after_trimming_past_the_group(r: ClientType, real_server_details):
    _add(r, 10)
    r.xgroup_create("s", "g", id="0")
    _read(r, count=6)
    r.xtrim("s", maxlen=3, approximate=False)
    # Since Redis 7.4 a group behind the first entry is behind by the whole stream; before, its count still held.
    trim_aware = real_server_details.server_type == "redis" and real_server_details.server_version >= (7, 4)
    assert _group(r) == (b"6-1", 6, 3 if trim_aware else 4)
    assert _read(r, count=1) == [b"8-1"]
    assert _group(r) == (b"8-1", 8, 2)
    r.xtrim("s", maxlen=0, approximate=False)
    assert _group(r) == (b"8-1", 8, 0 if trim_aware else 2)


def _error(r: ClientType, *args) -> str:
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, *args)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    return str(ctx.value)


def test_group_commands_on_a_missing_key(r: ClientType, real_server_details):
    key_needed = (
        "The XGROUP subcommand requires the key to exist. "
        "Note that for CREATE you may want to use the MKSTREAM option to create an empty stream automatically."
    )
    assert _error(r, "XGROUP", "CREATE", "missing", "g", "0") == key_needed
    for args in (("SETID", "missing", "g", "0"), ("DESTROY", "missing", "g"), ("CREATECONSUMER", "missing", "g", "c")):
        assert _error(r, "XGROUP", *args) == key_needed
    assert _error(r, "XGROUP", "DELCONSUMER", "missing", "g", "c") == key_needed
    assert _error(r, "XINFO", "CONSUMERS", "missing", "g") == "no such key"
    assert _error(r, "XAUTOCLAIM", "missing", "g", "c", 0, "0") == "NOGROUP No such key 'missing' or consumer group 'g'"
    if real_server_details.server_type == "dragonfly":
        assert _error(r, "XCLAIM", "missing", "g", "c", 0, "1-1") == "no such key"
    else:
        assert (
            _error(r, "XCLAIM", "missing", "g", "c", 0, "1-1") == "NOGROUP No such key 'missing' or consumer group 'g'"
        )
    assert r.exists("missing") == 0


def test_group_commands_on_a_missing_group(r: ClientType, real_server_details):
    r.xadd("s", {"f": "v"}, id="1-1")
    no_group = "NOGROUP No such consumer group 'g' for key name 's'"
    for args in (("SETID", "s", "g", "0"), ("CREATECONSUMER", "s", "g", "c"), ("DELCONSUMER", "s", "g", "c")):
        assert _error(r, "XGROUP", *args) == no_group
    assert _error(r, "XINFO", "CONSUMERS", "s", "g") == no_group
    assert r.xgroup_destroy("s", "g") == 0
    assert _error(r, "XAUTOCLAIM", "s", "g", "c", 0, "0") == "NOGROUP No such key 's' or consumer group 'g'"
    if real_server_details.server_type == "dragonfly":
        assert testtools.raw_command(r, "XCLAIM", "s", "g", "c", 0, "1-1") == []
    else:
        assert _error(r, "XCLAIM", "s", "g", "c", 0, "1-1") == "NOGROUP No such key 's' or consumer group 'g'"
