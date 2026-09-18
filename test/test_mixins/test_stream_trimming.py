"""XADD/XTRIM trimming, argument validation and entry IDs, compared with real servers.

A stream keeps its entries in nodes of up to `stream-node-max-entries` entries (100 by default) or
`stream-node-max-bytes` bytes (4096), and approximate trimming (`~`) only drops whole nodes.
"""

from __future__ import annotations

import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test import testtools


def _add(r: ClientType, count: int, start: int = 1, value: bytes = b"v", key: str = "s") -> None:
    pipe = r.pipeline(transaction=False)
    for i in range(start, start + count):
        pipe.xadd(key, {"f": value}, id=f"{i}-1")
    pipe.execute()


def _ids(r: ClientType, key: str = "s") -> list[bytes]:
    return [entry[0] for entry in r.xrange(key)]


def _raises(r: ClientType, message: str, *args) -> None:
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, *args)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert str(ctx.value) == message


# KiviDB trims exactly, `~` or not.
approximate_trimming = pytest.mark.unsupported_server_types("kividb")


@approximate_trimming
def test_xtrim_approximate_drops_whole_nodes(r: ClientType):
    _add(r, 250)  # nodes of 100, 100 and 50 entries
    assert r.xtrim("s", maxlen=10, approximate=True) == 200
    assert r.xlen("s") == 50
    assert r.xtrim("s", maxlen=10, approximate=True) == 0
    assert r.xtrim("s", maxlen=10, approximate=False) == 40
    assert _ids(r)[0] == b"241-1"


@approximate_trimming
def test_xtrim_approximate_stops_at_a_node_it_cannot_drop(r: ClientType):
    _add(r, 250)
    assert r.xtrim("s", maxlen=151, approximate=True) == 0  # dropping the first node would leave 150
    assert r.xtrim("s", maxlen=150, approximate=True) == 100
    assert r.xtrim("s", minid="200-1", approximate=True) == 0  # the second node ends at 200-1
    assert r.xtrim("s", minid="201-1", approximate=True) == 100
    assert _ids(r)[0] == b"201-1"


@approximate_trimming
def test_xadd_approximate_maxlen(r: ClientType):
    for i in range(1, 251):
        r.xadd("s", {"f": "v"}, id=f"{i}-1", maxlen=10, approximate=True)
        if i == 109:
            assert r.xlen("s") == 109
        if i == 110:
            assert r.xlen("s") == 10  # the first node went as soon as that left at least 10 entries
    assert r.xlen("s") == 50
    assert r.xinfo_stream("s")["radix-tree-keys"] == 1


@approximate_trimming
@pytest.mark.parametrize(
    "size,nodes,trimmed",
    [
        (50, 1, 0),  # 60 small entries fit one node
        (62, 2, 56),  # a node fills up at 4096 bytes
        (100, 2, 36),
        (126, 3, 58),  # from 64 bytes on, a value takes a longer header
        (1000, 15, 56),
    ],
)
def test_xtrim_approximate_node_size_follows_the_bytes_of_the_entries(r: ClientType, size, nodes, trimmed):
    _add(r, 60, value=b"y" * size)
    assert r.xinfo_stream("s")["radix-tree-keys"] == nodes
    assert r.xtrim("s", maxlen=1, approximate=True) == trimmed


@approximate_trimming
def test_xtrim_approximate_nodes_count_deleted_entries(r: ClientType):
    _add(r, 100)
    r.xdel("s", *[f"{i}-1" for i in range(2, 101, 2)])
    _add(r, 60, start=101)  # the first node is full: 50 entries left, 50 deleted
    assert r.xinfo_stream("s")["radix-tree-keys"] == 2
    assert r.xtrim("s", maxlen=60, approximate=True) == 50
    assert _ids(r)[0] == b"101-1"


@approximate_trimming
def test_xtrim_approximate_after_exact_trimming(r: ClientType):
    _add(r, 150)
    assert r.xtrim("s", maxlen=120, approximate=False) == 30  # deleted in place: the first node still holds 100
    _add(r, 60, start=151)
    assert r.xinfo_stream("s")["radix-tree-keys"] == 3
    assert r.xtrim("s", maxlen=100, approximate=True) == 70
    assert _ids(r)[0] == b"101-1"


@approximate_trimming
def test_xtrim_approximate_limit(r: ClientType):
    _add(r, 350)
    assert r.xtrim("s", maxlen=0, approximate=True, limit=150) == 100  # a second node would take it past 150
    assert r.xtrim("s", maxlen=0, approximate=True, limit=200) == 200
    assert testtools.raw_command(r, "XTRIM", "s", "MAXLEN", "~", 0, "LIMIT", 0) == 50  # LIMIT 0: no limit


@approximate_trimming
def test_xtrim_approximate_default_limit(r: ClientType):
    _add(r, 10250)
    # Without LIMIT, approximate trimming stops after 100 nodes.
    assert r.xtrim("s", maxlen=0, approximate=True) == 10000


@pytest.mark.unsupported_server_types("dragonfly", "kividb")
def test_xtrim_approximate_follows_the_node_settings(r: ClientType):
    try:
        r.config_set("stream-node-max-entries", 10)
        _add(r, 25)
        assert r.xinfo_stream("s")["radix-tree-keys"] == 3
        assert r.xtrim("s", maxlen=5, approximate=True) == 20
    finally:
        r.config_set("stream-node-max-entries", 100)


@pytest.mark.supported_server_versions(min_redis_ver="7")
@pytest.mark.unsupported_server_types("dragonfly", "kividb")
def test_xadd_xtrim_argument_errors(r: ClientType):
    _add(r, 5)
    _raises(r, "syntax error, LIMIT cannot be used without the special ~ option", "XTRIM", "s", "MAXLEN", 3, "LIMIT", 1)
    _raises(
        r, "syntax error, LIMIT cannot be used without the special ~ option", "XTRIM", "s", "MINID", "3-1", "LIMIT", 1
    )
    _raises(
        r, "syntax error, LIMIT cannot be used without the special ~ option", "XADD", "s", "LIMIT", 0, "*", "f", "v"
    )
    _raises(
        r,
        "syntax error, LIMIT cannot be used without specifying a trimming strategy",
        *("XADD", "s", "LIMIT", 5, "*", "f", "v"),
    )
    _raises(r, "syntax error, XTRIM must be called with a trimming strategy", "XTRIM", "s", "LIMIT", 0)
    _raises(r, "The MAXLEN argument must be >= 0.", "XTRIM", "s", "MAXLEN", -1)
    _raises(r, "The LIMIT argument must be >= 0.", "XTRIM", "s", "MAXLEN", "~", 5, "LIMIT", -1)
    _raises(r, "value is not an integer or out of range", "XTRIM", "s", "MAXLEN", "~")
    for args in (("MAXLEN", 5, "MINID", "3-1"), ("MINID", "3-1", "MAXLEN", 5), ("MAXLEN", 5, "MAXLEN", 4)):
        _raises(r, "syntax error, MAXLEN and MINID options at the same time are not compatible", "XTRIM", "s", *args)
    for minid in ("abc", "3-*", "-", "+", "$", "1-2-3", "18446744073709551616"):
        _raises(r, "Invalid stream ID specified as stream command argument", "XTRIM", "s", "MINID", minid)
    _raises(r, "Invalid stream ID specified as stream command argument", "XADD", "s", "MAXLEN", 5, "FOO", "*", "f", "v")
    _raises(r, "syntax error", "XTRIM", "s", "MAXLEN", 5, "FOO")
    _raises(r, "wrong number of arguments for 'xtrim' command", "XTRIM", "s", "MAXLEN")
    _raises(r, "wrong number of arguments for 'xadd' command", "XADD", "s", "MAXLEN", 5, "*", "f")
    assert _ids(r) == [b"1-1", b"2-1", b"3-1", b"4-1", b"5-1"]
    # The options can come in any order, and LIMIT goes with `~`.
    assert testtools.raw_command(r, "XTRIM", "s", "LIMIT", 100, "MAXLEN", "~", 3) == 0
    assert testtools.raw_command(r, "XTRIM", "s", "MINID", "=", "3") == 2


@pytest.mark.unsupported_server_types("kividb")
def test_xtrim_missing_key(r: ClientType):
    assert r.xtrim("missing", maxlen=5) == 0
    assert r.exists("missing") == 0


@pytest.mark.supported_server_versions(min_redis_ver="7")
@pytest.mark.unsupported_server_types("dragonfly", "kividb")
def test_xadd_entry_ids(r: ClientType):
    assert r.xadd("s", {"f": "v"}, id="5-1") == b"5-1"
    assert r.xdel("s", "5-1") == 1
    # The last ID handed out still counts once its entry is gone.
    _raises(
        r, "The ID specified in XADD is equal or smaller than the target stream top item", "XADD", "s", "5-1", "f", "v"
    )
    assert r.xadd("s", {"f": "v"}, id="5-*") == b"5-2"
    assert r.xinfo_stream("s")["last-generated-id"] == b"5-2"

    assert r.xadd("new", {"f": "v"}, id="0-*") == b"0-1"
    for entry_id in ("0-0", "0"):
        _raises(r, "The ID specified in XADD must be greater than 0-0", "XADD", "other", entry_id, "f", "v")
    for entry_id in ("1-2-3", "18446744073709551616-1", "-1", "1-"):
        _raises(r, "Invalid stream ID specified as stream command argument", "XADD", "other", entry_id, "f", "v")
    assert r.exists("other") == 0

    max_id = "18446744073709551615-18446744073709551615"
    assert r.xadd("full", {"f": "v"}, id=max_id) == max_id.encode()
    _raises(r, "The stream has exhausted the last possible ID, unable to add more items", "XADD", "full", "*", "f", "v")


def test_xadd_wrong_type(r: ClientType):
    r.set("string", "x")
    with pytest.raises(Exception) as ctx:
        r.xadd("string", {"f": "v"})
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert str(ctx.value).startswith("WRONGTYPE")


@pytest.mark.supported_server_versions(min_redis_ver="7")
def test_xinfo_stream_of_a_stream_nothing_was_added_to(r: ClientType):
    r.xgroup_create("s", "g", id="$", mkstream=True)
    # Read raw: under RESP3 dragonfly sends the empty stream's first/last entry in a shape redis-py cannot parse.
    info = testtools.raw_command(r, "XINFO", "STREAM", "s")
    if isinstance(info, list):  # RESP2
        info = dict(zip(info[::2], info[1::2]))
    assert info[b"last-generated-id"] == b"0-0"
