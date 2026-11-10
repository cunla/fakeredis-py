"""XREAD / XREADGROUP `MAXCOUNT` and `MAXSIZE`, the cumulative caps redis 8.10 added across all the streams read."""

import threading
import time

import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test import testtools
from test.testtools import get_protocol_version

pytestmark = [
    pytest.mark.supported_server_versions(min_redis_ver="8.10"),
    pytest.mark.unsupported_server_types("valkey", "dragonfly", "kividb"),
]


def _ids(res) -> list[tuple[bytes, list[bytes]]]:
    """(stream, [entry ids]) for each stream in a raw XREAD/XREADGROUP reply, in reply order."""
    if res is None:
        return []
    pairs = res.items() if isinstance(res, dict) else res
    return [(name, [entry[0] for entry in entries]) for name, entries in pairs]


def _add(r: ClientType, key: str, n: int, start: int = 1, **fields) -> None:
    for i in range(start, start + n):
        r.xadd(key, fields or {"f": "v"}, id=f"{i}-0")


def _xread(r: ClientType, *args):
    return _ids(testtools.raw_command(r, "XREAD", *args))


def _xreadgroup(r: ClientType, consumer: str, *args):
    return _ids(testtools.raw_command(r, "XREADGROUP", "GROUP", "g", consumer, *args))


def _pending(r: ClientType, key: str) -> list[tuple[bytes, bytes]]:
    return [(p["message_id"], p["consumer"]) for p in r.xpending_range(key, "g", "-", "+", 100)]


def _assert_error(r: ClientType, args, msg: str) -> None:
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, *args)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert msg in str(ctx.value)


def test_xread_maxcount(r: ClientType):
    _add(r, "s1", 5)
    _add(r, "s2", 5)
    # MAXCOUNT is one budget for the whole reply, filled from the first stream onward
    assert _xread(r, "MAXCOUNT", 3, "STREAMS", "s1", "s2", 0, 0) == [(b"s1", [b"1-0", b"2-0", b"3-0"])]
    assert _xread(r, "MAXCOUNT", 7, "STREAMS", "s1", "s2", 0, 0) == [
        (b"s1", [b"1-0", b"2-0", b"3-0", b"4-0", b"5-0"]),
        (b"s2", [b"1-0", b"2-0"]),
    ]
    # A budget used up by the first stream leaves the next one out of the reply
    assert _xread(r, "MAXCOUNT", 5, "STREAMS", "s1", "s2", 0, 0) == [(b"s1", [b"1-0", b"2-0", b"3-0", b"4-0", b"5-0"])]
    # COUNT still caps each stream
    assert _xread(r, "COUNT", 2, "MAXCOUNT", 3, "STREAMS", "s1", "s2", 0, 0) == [
        (b"s1", [b"1-0", b"2-0"]),
        (b"s2", [b"1-0"]),
    ]
    # A COUNT of 0 or less reads everything and is not compared with MAXCOUNT
    assert _xread(r, "COUNT", 0, "MAXCOUNT", 2, "STREAMS", "s1", 0) == [(b"s1", [b"1-0", b"2-0"])]
    # Streams with nothing to read take nothing from the budget
    assert _xread(r, "MAXCOUNT", 1, "STREAMS", "missing", "s1", "s2", 0, "5-0", 0) == [(b"s2", [b"1-0"])]
    assert _xread(r, "MAXCOUNT", 1, "STREAMS", "s1", "s2", "$", 0) == [(b"s2", [b"1-0"])]
    # The option is case-insensitive, and a repeated one overrides the earlier one
    assert _xread(r, "maxcount", 2, "MAXCOUNT", 1, "STREAMS", "s1", 0) == [(b"s1", [b"1-0"])]
    assert _xread(r, "MAXCOUNT", 9223372036854775807, "STREAMS", "s1", 3) == [(b"s1", [b"4-0", b"5-0"])]


def test_xread_maxsize(r: ClientType):
    _add(r, "s", 3)
    # MAXSIZE counts the reply's bytes: the stream's header, then each `[id, [field, value]]` entry (31 bytes here). The
    # header is the key, preceded under RESP2 by the 2-array pairing it with its entries.
    second_entry_at = 43 if get_protocol_version(r) == 2 else 39
    assert _xread(r, "MAXSIZE", second_entry_at - 1, "STREAMS", "s", 0) == [(b"s", [b"1-0"])]
    assert _xread(r, "MAXSIZE", second_entry_at, "STREAMS", "s", 0) == [(b"s", [b"1-0", b"2-0"])]
    assert _xread(r, "MAXSIZE", second_entry_at + 30, "STREAMS", "s", 0) == [(b"s", [b"1-0", b"2-0"])]
    assert _xread(r, "MAXSIZE", second_entry_at + 31, "STREAMS", "s", 0) == [(b"s", [b"1-0", b"2-0", b"3-0"])]
    # At least one entry is always returned, however big
    r.xadd("big", {"f": "v" * 5000}, id="1-1")
    res = testtools.raw_command(r, "XREAD", "MAXSIZE", 50, "STREAMS", "big", 0)
    entries = res[b"big"] if isinstance(res, dict) else res[0][1]
    assert entries == [[b"1-1", [b"f", b"v" * 5000]]]


def test_xread_maxsize_can_leave_a_stream_without_entries(r: ClientType):
    _add(r, "a", 2)
    _add(r, "b", 2)
    # Once `a` is done (its header, 2 entries and the length of its entries array), `b` is started if the bytes so far
    # are still under MAXSIZE. Its header can then use up the rest, leaving `b` in the reply with no entries.
    b_started_at = 78 if get_protocol_version(r) == 2 else 74
    b_header = 11 if get_protocol_version(r) == 2 else 7
    a_ids = [b"1-0", b"2-0"]
    assert _xread(r, "MAXSIZE", b_started_at - 1, "STREAMS", "a", "b", 0, 0) == [(b"a", a_ids)]
    assert _xread(r, "MAXSIZE", b_started_at, "STREAMS", "a", "b", 0, 0) == [(b"a", a_ids), (b"b", [])]
    assert _xread(r, "MAXSIZE", b_started_at + b_header - 1, "STREAMS", "a", "b", 0, 0) == [(b"a", a_ids), (b"b", [])]
    assert _xread(r, "MAXSIZE", b_started_at + b_header, "STREAMS", "a", "b", 0, 0) == [
        (b"a", a_ids),
        (b"b", [b"1-0"]),
    ]


def test_xread_maxcount_and_maxsize(r: ClientType):
    _add(r, "s1", 5)
    _add(r, "s2", 5)
    # Whichever cap is reached first wins
    assert _xread(r, "MAXCOUNT", 2, "MAXSIZE", 100000, "STREAMS", "s1", "s2", 0, 0) == [(b"s1", [b"1-0", b"2-0"])]
    assert _xread(r, "MAXSIZE", 1, "MAXCOUNT", 100, "STREAMS", "s1", "s2", 0, 0) == [(b"s1", [b"1-0"])]


@pytest.mark.parametrize("command", [("XREAD",), ("XREADGROUP", "GROUP", "g", "c")])
@pytest.mark.parametrize(
    "options,msg",
    [
        (("MAXCOUNT", 0), "MAXCOUNT must be a positive integer"),
        (("MAXCOUNT", -1), "MAXCOUNT must be a positive integer"),
        (("MAXSIZE", 0), "MAXSIZE must be a positive integer"),
        (("MAXSIZE", -1), "MAXSIZE must be a positive integer"),
        (("MAXCOUNT", "abc"), "value is not an integer or out of range"),
        (("MAXCOUNT", "1.5"), "value is not an integer or out of range"),
        (("MAXSIZE", "abc"), "value is not an integer or out of range"),
        (("MAXCOUNT", 9223372036854775808), "value is not an integer or out of range"),
        (("MAXCOUNT",), "value is not an integer or out of range"),  # STREAMS is read as its value
        (("COUNT", 3, "MAXCOUNT", 2), "MAXCOUNT must be greater than or equal to COUNT"),
        (("MAXCOUNT", 2, "COUNT", 3), "MAXCOUNT must be greater than or equal to COUNT"),
    ],
)
def test_stream_read_caps_errors(r: ClientType, command, options, msg):
    _add(r, "s", 1)
    r.xgroup_create("s", "g", id="0")
    _assert_error(r, (*command, *options, "STREAMS", "s", 0), msg)


def test_xreadgroup_maxcount(r: ClientType):
    for key in ("a", "b"):
        _add(r, key, 3)
        r.xgroup_create(key, "g", id="0")
    assert _xreadgroup(r, "c", "MAXCOUNT", 4, "STREAMS", "a", "b", ">", ">") == [
        (b"a", [b"1-0", b"2-0", b"3-0"]),
        (b"b", [b"1-0"]),
    ]
    # Only what was delivered is pending; the rest is delivered by the next read
    assert _pending(r, "a") == [(b"1-0", b"c"), (b"2-0", b"c"), (b"3-0", b"c")]
    assert _pending(r, "b") == [(b"1-0", b"c")]
    assert _xreadgroup(r, "c", "STREAMS", "a", "b", ">", ">") == [(b"b", [b"2-0", b"3-0"])]
    # A COUNT of 0 or less reads everything and is not compared with MAXCOUNT
    r.xgroup_create("a", "g2", id="0")
    assert _ids(
        testtools.raw_command(r, "XREADGROUP", "GROUP", "g2", "c", "COUNT", 0, "MAXCOUNT", 2, "STREAMS", "a", ">")
    ) == [(b"a", [b"1-0", b"2-0"])]


def test_xreadgroup_maxsize_does_not_deliver_skipped_entries(r: ClientType):
    for key in ("a", "b"):
        _add(r, key, 3)
        r.xgroup_create(key, "g", id="0")
    assert _xreadgroup(r, "c", "MAXSIZE", 1, "STREAMS", "a", "b", ">", ">") == [(b"a", [b"1-0"])]
    assert _pending(r, "a") == [(b"1-0", b"c")]
    assert _pending(r, "b") == []
    # `b` is started but its header uses up the budget: it is in the reply, yet nothing of it is delivered
    b_started_at = 78 if get_protocol_version(r) == 2 else 74
    assert _xreadgroup(r, "c", "MAXSIZE", b_started_at, "STREAMS", "a", "b", ">", ">") == [
        (b"a", [b"2-0", b"3-0"]),
        (b"b", []),
    ]
    assert _pending(r, "b") == []
    assert _xreadgroup(r, "c", "STREAMS", "b", ">") == [(b"b", [b"1-0", b"2-0", b"3-0"])]


def test_xreadgroup_history_read_caps(r: ClientType):
    for key in ("a", "b"):
        _add(r, key, 3)
        r.xgroup_create(key, "g", id="0")
    _xreadgroup(r, "c", "STREAMS", "a", "b", ">", ">")
    all_ids = [b"1-0", b"2-0", b"3-0"]
    assert _xreadgroup(r, "c", "MAXCOUNT", 4, "STREAMS", "a", "b", 0, 0) == [(b"a", all_ids), (b"b", [b"1-0"])]
    # A history read is in the reply even when it finds nothing, but not once the budget is used up
    assert _xreadgroup(r, "c", "MAXCOUNT", 3, "STREAMS", "a", "b", 0, 0) == [(b"a", all_ids)]
    assert _xreadgroup(r, "c", "MAXCOUNT", 1, "STREAMS", "a", "b", "3-0", 0) == [(b"a", []), (b"b", [b"1-0"])]
    assert _xreadgroup(r, "other", "MAXCOUNT", 1, "STREAMS", "a", "b", 0, 0) == [(b"a", []), (b"b", [])]
    assert _xreadgroup(r, "c", "MAXSIZE", 1, "STREAMS", "a", "b", 0, 0) == [(b"a", [b"1-0"])]
    # An entry deleted from the stream is read as `[id, nil]`, which is all it takes from MAXSIZE
    r.xdel("a", "2-0")
    third_entry_at = 61 if get_protocol_version(r) == 2 else 55
    assert _xreadgroup(r, "c", "MAXSIZE", third_entry_at - 1, "STREAMS", "a", 0) == [(b"a", [b"1-0", b"2-0"])]
    assert _xreadgroup(r, "c", "MAXSIZE", third_entry_at, "STREAMS", "a", 0) == [(b"a", all_ids)]


def test_xreadgroup_noack_maxcount(r: ClientType):
    _add(r, "a", 3)
    r.xgroup_create("a", "g", id="0")
    assert _xreadgroup(r, "c", "NOACK", "MAXCOUNT", 2, "STREAMS", "a", ">") == [(b"a", [b"1-0", b"2-0"])]
    assert _pending(r, "a") == []
    assert _xreadgroup(r, "c", "STREAMS", "a", ">") == [(b"a", [b"3-0"])]


def test_xreadgroup_claim_maxcount(r: ClientType):
    _add(r, "a", 3)
    r.xgroup_create("a", "g", id="0")
    _xreadgroup(r, "c1", "STREAMS", "a", ">")
    time.sleep(0.05)
    _add(r, "a", 2, start=4)
    # MAXCOUNT caps the claimed entries as well as the new ones
    assert _xreadgroup(r, "c2", "CLAIM", 10, "MAXCOUNT", 2, "STREAMS", "a", ">") == [(b"a", [b"1-0", b"2-0"])]
    assert _pending(r, "a") == [(b"1-0", b"c2"), (b"2-0", b"c2"), (b"3-0", b"c1")]
    # Claimed entries come first, longest idle first, then new ones
    assert _xreadgroup(r, "c3", "CLAIM", 0, "MAXCOUNT", 4, "STREAMS", "a", ">") == [
        (b"a", [b"3-0", b"1-0", b"2-0", b"4-0"])
    ]
    assert _pending(r, "a") == [(b"1-0", b"c3"), (b"2-0", b"c3"), (b"3-0", b"c3"), (b"4-0", b"c3")]


def test_stream_read_caps_after_blocking(create_connection):
    r = create_connection(db=1)  # not flushed between tests: each read below starts from a fresh stream

    def add_entries():
        time.sleep(0.2)
        with create_connection(db=1).pipeline(transaction=True) as pipe:
            for i in range(2, 5):
                pipe.xadd("a", {"f": "v"}, id=f"{i}-0")
            pipe.execute()

    for read in (
        lambda: _xread(r, "MAXCOUNT", 2, "BLOCK", 5000, "STREAMS", "a", "$"),
        lambda: _xreadgroup(r, "c", "MAXCOUNT", 2, "BLOCK", 5000, "STREAMS", "a", ">"),
    ):
        r.delete("a")
        r.xadd("a", {"f": "v"}, id="1-0")
        r.xgroup_create("a", "g", id="$")
        thread = threading.Thread(target=add_entries)
        thread.start()
        assert read() == [(b"a", [b"2-0", b"3-0"])]
        thread.join()
    assert _pending(r, "a") == [(b"2-0", b"c"), (b"3-0", b"c")]


# These markers replace the module's: conftest reads the closest one
@pytest.mark.supported_server_versions(max_redis_ver="8.9")
@pytest.mark.unsupported_server_types("kividb")
def test_stream_read_caps_unsupported(r: ClientType):
    _add(r, "s", 1)
    r.xgroup_create("s", "g", id="0")
    for option in ("MAXCOUNT", "MAXSIZE"):
        _assert_error(r, ("XREAD", option, 1, "STREAMS", "s", 0), "syntax error")
        _assert_error(r, ("XREADGROUP", "GROUP", "g", "c", option, 1, "STREAMS", "s", ">"), "syntax error")
