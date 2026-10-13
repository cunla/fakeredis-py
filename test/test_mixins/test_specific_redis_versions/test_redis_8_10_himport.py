"""Tests for the `HIMPORT` commands introduced in Redis 8.10: session-local fieldsets and the hashes built from them.

Most tests send the commands raw. redis-py 8.1 added `himport_*` methods, but they keep a registry of fieldsets on the
client and prepare, discard and re-prepare them on each connection as needed, which hides what the server does with a
fieldset. The tests at the end of the file go through those methods.

See https://github.com/cunla/fakeredis-py/issues/599
"""

import pytest
import redis

from fakeredis._typing import ClientType
from test import testtools
from test.test_keyspace_notifications import wait_for_message
from test.testtools import raw_command

pytestmark = []
pytestmark.extend(
    [
        testtools.run_test_if_redispy_ver("gte", "8.1"),
        pytest.mark.unsupported_server_types("dragonfly", "valkey", "kividb"),
        pytest.mark.supported_server_versions(min_redis_ver="8.10"),
    ]
)


def test_himport_set(r: ClientType):
    assert raw_command(r, "HIMPORT", "PREPARE", "fs", "b", "a", "c") == b"OK"
    assert raw_command(r, "HIMPORT", "SET", "foo", "fs", "1", "2", "3") == b"OK"
    # Values follow the order the fields were prepared in.
    assert r.hgetall("foo") == {b"a": b"2", b"b": b"1", b"c": b"3"}
    assert r.type("foo") == b"hash"


def test_himport_set_field_order(r: ClientType):
    # The fieldset is sorted by length, then bytewise.
    raw_command(r, "HIMPORT", "PREPARE", "fs", "10", "9", "a", "B", "aa", "")
    raw_command(r, "HIMPORT", "SET", "foo", "fs", "v1", "v2", "v3", "v4", "v5", "v6")
    assert r.hkeys("foo") == [b"", b"9", b"B", b"a", b"10", b"aa"]
    assert r.hvals("foo") == [b"v6", b"v2", b"v4", b"v3", b"v1", b"v5"]


def test_himport_set_replaces_hash(r: ClientType):
    raw_command(r, "HIMPORT", "PREPARE", "fs", "a", "b")
    r.hset("foo", mapping={"a": "old", "z": "9"})
    raw_command(r, "HEXPIRE", "foo", 100, "FIELDS", 2, "a", "z")
    r.expire("foo", 100)
    raw_command(r, "HIMPORT", "SET", "foo", "fs", "1", "2")
    assert r.hgetall("foo") == {b"a": b"1", b"b": b"2"}
    assert r.ttl("foo") == -1
    assert raw_command(r, "HTTL", "foo", "FIELDS", 3, "a", "b", "z") == [-1, -1, -2]

    raw_command(r, "HIMPORT", "SET", "foo", "fs", "", "4")
    assert r.hgetall("foo") == {b"a": b"", b"b": b"4"}


def test_himport_set_then_hash_commands(r: ClientType):
    raw_command(r, "HIMPORT", "PREPARE", "fs", "a", "b")
    raw_command(r, "HIMPORT", "SET", "foo", "fs", "1", "2")
    assert r.hincrby("foo", "a", 5) == 6
    assert r.hset("foo", "c", "3") == 1
    assert r.hdel("foo", "b") == 1
    assert r.hgetall("foo") == {b"a": b"6", b"c": b"3"}
    assert r.hdel("foo", "a", "c") == 2
    assert r.exists("foo") == 0


def test_himport_set_errors(r: ClientType):
    raw_command(r, "HIMPORT", "PREPARE", "fs", "a", "b")
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(r, "HIMPORT", "SET", "foo", "nofs", "1")
    # Fieldset names are case-sensitive.
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(r, "HIMPORT", "SET", "foo", "FS", "1", "2")
    for values in (("1",), ("1", "2", "3")):
        with pytest.raises(redis.ResponseError, match="value count does not match fieldset field count"):
            raw_command(r, "HIMPORT", "SET", "foo", "fs", *values)
    assert r.exists("foo") == 0
    with pytest.raises(redis.ResponseError):
        raw_command(r, "HIMPORT", "SET", "foo", "fs")

    # The key's type is checked before the fieldset is looked up.
    r.set("str", "v")
    for args in (("nofs", "1"), ("fs", "1"), ("fs", "1", "2")):
        with pytest.raises(redis.ResponseError, match="WRONGTYPE"):
            raw_command(r, "HIMPORT", "SET", "str", *args)
    assert r.get("str") == b"v"


def test_himport_prepare(r: ClientType):
    assert raw_command(r, "HIMPORT", "PREPARE", "fs", "a", "b", "c") == b"OK"
    # Preparing a name again replaces its fieldset.
    assert raw_command(r, "himport", "prepare", "fs", "x", "y") == b"OK"
    raw_command(r, "HIMPORT", "SET", "foo", "fs", "1", "2")
    assert r.hgetall("foo") == {b"x": b"1", b"y": b"2"}

    # A rejected fieldset leaves the one it would have replaced.
    with pytest.raises(redis.ResponseError, match="duplicate field name in fieldset"):
        raw_command(r, "HIMPORT", "PREPARE", "fs", "a", "a", "b")
    raw_command(r, "HIMPORT", "SET", "foo", "fs", "3", "4")
    assert r.hgetall("foo") == {b"x": b"3", b"y": b"4"}
    with pytest.raises(redis.ResponseError, match="duplicate field name in fieldset"):
        raw_command(r, "HIMPORT", "PREPARE", "dup", "a", "a")
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(r, "HIMPORT", "SET", "foo", "dup", "1", "2")

    with pytest.raises(redis.ResponseError):
        raw_command(r, "HIMPORT", "PREPARE", "fs")
    # Empty names are as good as any.
    assert raw_command(r, "HIMPORT", "PREPARE", "", "") == b"OK"
    raw_command(r, "HIMPORT", "SET", "bar", "", "v")
    assert r.hgetall("bar") == {b"": b"v"}


def test_himport_discard(r: ClientType):
    raw_command(r, "HIMPORT", "PREPARE", "fs", "a")
    raw_command(r, "HIMPORT", "PREPARE", "other", "a")
    assert raw_command(r, "HIMPORT", "DISCARD", "nofs") == 0
    assert raw_command(r, "HIMPORT", "DISCARD", "fs") == 1
    assert raw_command(r, "HIMPORT", "DISCARD", "fs") == 0
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(r, "HIMPORT", "SET", "foo", "fs", "1")
    assert raw_command(r, "HIMPORT", "SET", "foo", "other", "1") == b"OK"
    with pytest.raises(redis.ResponseError):
        raw_command(r, "HIMPORT", "DISCARD")
    with pytest.raises(redis.ResponseError):
        raw_command(r, "HIMPORT", "DISCARD", "fs", "other")


def test_himport_discardall(r: ClientType):
    assert raw_command(r, "HIMPORT", "DISCARDALL") == 0
    raw_command(r, "HIMPORT", "PREPARE", "fs", "a")
    raw_command(r, "HIMPORT", "PREPARE", "other", "a")
    assert raw_command(r, "HIMPORT", "DISCARDALL") == 2
    assert raw_command(r, "HIMPORT", "DISCARDALL") == 0
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(r, "HIMPORT", "SET", "foo", "fs", "1")
    with pytest.raises(redis.ResponseError):
        raw_command(r, "HIMPORT", "DISCARDALL", "fs")


def test_himport_fieldsets_belong_to_the_connection(r: ClientType, create_connection):
    other = create_connection()
    raw_command(r, "HIMPORT", "PREPARE", "fs", "a")
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(other, "HIMPORT", "SET", "foo", "fs", "1")
    assert raw_command(other, "HIMPORT", "DISCARD", "fs") == 0
    assert raw_command(other, "HIMPORT", "DISCARDALL") == 0
    assert raw_command(r, "HIMPORT", "SET", "foo", "fs", "1") == b"OK"


def test_himport_fieldsets_survive_select_but_not_reset(r: ClientType):
    # One connection throughout: SELECT and RESET act on the connection, as fieldsets do.
    with r.client() as conn:
        raw_command(conn, "HIMPORT", "PREPARE", "fs", "a")
        raw_command(conn, "SELECT", 1)
        assert raw_command(conn, "HIMPORT", "SET", "foo", "fs", "1") == b"OK"
        assert raw_command(conn, "HGETALL", "foo") in ([b"a", b"1"], {b"a": b"1"})
        raw_command(conn, "DEL", "foo")
        raw_command(conn, "RESET")
        with pytest.raises(redis.ResponseError, match="no such fieldset"):
            raw_command(conn, "HIMPORT", "SET", "foo", "fs", "1")


def test_himport_in_transaction(r: ClientType):
    p = r.pipeline()
    p.execute_command("HIMPORT", "PREPARE", "fs", "a", "b")
    p.execute_command("HIMPORT", "SET", "foo", "fs", "1", "2")
    p.execute_command("HIMPORT", "DISCARD", "fs")
    p.execute_command("HIMPORT", "SET", "bar", "fs", "1", "2")
    res = p.execute(raise_on_error=False)
    assert res[:3] == [b"OK", b"OK", 1]
    assert isinstance(res[3], redis.ResponseError)
    assert r.hgetall("foo") == {b"a": b"1", b"b": b"2"}
    assert r.exists("bar") == 0


def test_himport_set_invalidates_watch(r: ClientType, create_connection):
    other = create_connection(db=2)  # the database `r` is on
    raw_command(other, "HIMPORT", "PREPARE", "fs", "a")
    with r.pipeline() as p:
        p.watch("foo")
        raw_command(other, "HIMPORT", "SET", "foo", "fs", "1")
        p.multi()
        p.ping()
        with pytest.raises(redis.WatchError):
            p.execute()


def test_himport_fieldsets_are_scoped_to_the_script(r: ClientType):
    pytest.importorskip("lupa")
    raw_command(r, "HIMPORT", "PREPARE", "fs", "a")
    # A script does not see the caller's fieldsets...
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        r.eval("return redis.pcall('HIMPORT', 'SET', KEYS[1], 'fs', '1')", 1, "foo")
    # ...it can prepare and use its own...
    script = "redis.call('HIMPORT', 'PREPARE', 'lfs', 'k', 'j'); return redis.call('HIMPORT', 'SET', KEYS[1], 'lfs', 'v', 'w')"
    assert r.eval(script, 1, "foo") == b"OK"
    assert r.hgetall("foo") == {b"k": b"v", b"j": b"w"}
    # ...which neither a later script nor the caller gets to use.
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        r.eval("return redis.call('HIMPORT', 'SET', KEYS[1], 'lfs', 'v', 'w')", 1, "bar")
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(r, "HIMPORT", "SET", "bar", "lfs", "v", "w")
    assert raw_command(r, "HIMPORT", "SET", "bar", "fs", "1") == b"OK"


def test_himport_fieldsets_are_scoped_to_the_function(r: ClientType):
    pytest.importorskip("lupa")
    library = """#!lua name=himport
redis.register_function('use', function(keys, args) return redis.call('HIMPORT', 'SET', keys[1], args[1], '1') end)
redis.register_function('prepare_and_use', function(keys, args)
  redis.call('HIMPORT', 'PREPARE', 'lfs', 'a')
  return redis.call('HIMPORT', 'SET', keys[1], 'lfs', '1')
end)
"""
    # A real server keeps its libraries from one test to the next.
    raw_command(r, "FUNCTION", "LOAD", "REPLACE", library)
    raw_command(r, "HIMPORT", "PREPARE", "fs", "a")
    # A function does not see the caller's fieldsets...
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(r, "FCALL", "use", 1, "foo", "fs")
    # ...it can prepare and use its own...
    assert raw_command(r, "FCALL", "prepare_and_use", 1, "foo") == b"OK"
    assert r.hgetall("foo") == {b"a": b"1"}
    # ...which neither a later call nor the caller gets to use.
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(r, "FCALL", "use", 1, "bar", "lfs")
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(r, "HIMPORT", "SET", "bar", "lfs", "1")
    assert raw_command(r, "HIMPORT", "SET", "bar", "fs", "1") == b"OK"
    raw_command(r, "FUNCTION", "DELETE", "himport")


def test_himport_set_keyspace_notification(r: ClientType):
    r.config_set("notify-keyspace-events", "KEA")
    p = r.pubsub()
    p.psubscribe("__key*@*__:*")
    assert wait_for_message(p)["type"] == "psubscribe"

    r.execute_command("HIMPORT", "PREPARE", "fs", "a")
    r.execute_command("HIMPORT", "SET", "foo", "fs", "1")

    msgs = []
    msg = wait_for_message(p, timeout=1.0)
    while msg is not None:
        msgs.append((msg["channel"], msg["data"]))
        msg = wait_for_message(p, timeout=0.1)
    # It is reported as the `hset` it amounts to.
    assert msgs == [(b"__keyspace@2__:foo", b"hset"), (b"__keyevent@2__:hset", b"foo")]


def test_redis_py_himport_set(r: ClientType):
    assert r.himport_prepare("fs", ["b", "a", "c"]) is True
    assert r.himport_set("foo", "fs", ["1", "2", "3"]) is True
    assert r.hgetall("foo") == {b"a": b"2", b"b": b"1", b"c": b"3"}

    # Preparing the name again replaces the fieldset, on the server too.
    assert r.himport_prepare("fs", ["x"]) is True
    assert r.himport_set("foo", "fs", ["9"]) is True
    assert r.hgetall("foo") == {b"x": b"9"}


def test_redis_py_himport_set_errors(r: ClientType):
    r.himport_prepare("fs", ["a", "b"])
    with pytest.raises(redis.exceptions.NoSuchFieldsetError, match="no such fieldset"):
        r.himport_set("foo", "nofs", ["1"])
    with pytest.raises(redis.ResponseError, match="value count does not match fieldset field count"):
        r.himport_set("foo", "fs", ["1"])
    # A fieldset is only sent to the server with the first hash that uses it, which is when the server gets to reject it.
    assert r.himport_prepare("dup", ["a", "a"]) is True
    with pytest.raises(redis.ResponseError, match="duplicate field name in fieldset"):
        r.himport_set("foo", "dup", ["1", "2"])
    assert r.exists("foo") == 0


def test_redis_py_himport_prepares_each_connection(r: ClientType):
    r.himport_prepare("fs", ["a"])
    assert r.himport_set("foo", "fs", ["1"]) is True
    # The pool's connection is busy, so the next hash goes out on a new one, which has to be given the fieldset first.
    with r.pipeline() as p:
        p.watch("other")
        assert r.himport_set("bar", "fs", ["2"]) is True
    assert r.hgetall("bar") == {b"a": b"2"}


def test_redis_py_himport_recovers_after_reset(r: ClientType):
    r.himport_prepare("fs", ["a"])
    assert r.himport_set("foo", "fs", ["1"]) is True
    with r.client() as conn:
        assert conn.himport_set("foo", "fs", ["2"]) is True
        # RESET drops the connection's fieldsets, and takes it back to database 0 and RESP2; redis-py prepares the
        # fieldset again when the server says it is gone.
        raw_command(conn, "RESET")
        assert conn.himport_set("foo", "fs", ["3"]) is True
        assert conn.hget("foo", "a") == b"3"
        conn.delete("foo")


def test_redis_py_himport_in_pipeline(r: ClientType):
    r.himport_prepare("fs", ["a", "b"])
    for transaction in (True, False):
        with r.pipeline(transaction=transaction) as p:
            p.himport_set("foo", "fs", ["1", "2"])
            p.hgetall("foo")
            assert p.execute() == [True, {b"a": b"1", b"b": b"2"}]


def test_redis_py_himport_discard(r: ClientType):
    r.himport_prepare("fs", ["a"])
    r.himport_prepare("other", ["a"])
    assert r.himport_set("foo", "fs", ["1"]) is True
    assert r.himport_discard("fs") == 1
    assert r.himport_discard("fs") == 0
    # The server is told to discard it before the connection is used for another hash.
    with pytest.raises(redis.exceptions.NoSuchFieldsetError):
        r.himport_set("foo", "fs", ["1"])
    assert raw_command(r, "HIMPORT", "DISCARD", "fs") == 0
    assert r.himport_set("foo", "other", ["2"]) is True
    assert r.himport_discard_all() == 1
    with pytest.raises(redis.exceptions.NoSuchFieldsetError):
        r.himport_set("foo", "other", ["1"])
