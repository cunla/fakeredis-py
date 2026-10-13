import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test import testtools
from test.testtools import raw_command, resp_conversion


@pytest.mark.supported_server_versions(min_redis_ver="7.4")
@pytest.mark.unsupported_server_types("valkey")
def test_hexpire_empty_key(r: ClientType, real_server_details):
    args = ("hexpire", b"", 2055010579, "fields", 2, b"\x89U\x04", b"6\x86\xf4\xdd")
    if real_server_details.server_type == "dragonfly":
        # Dragonfly caps a field TTL at 2**26 seconds, well below the one used here.
        with pytest.raises(Exception, match="value is not an integer or out of range"):
            raw_command(r, *args)
        return
    raw_command(r, *args)


def test_hstrlen_missing(r: ClientType):
    assert r.hstrlen("foo", "doesnotexist") == 0

    r.hset("foo", "key", "value")
    assert r.hstrlen("foo", "doesnotexist") == 0


def test_hstrlen(r: ClientType):
    r.hset("foo", "key", "value")
    assert r.hstrlen("foo", "key") == 5


def test_hset_then_hget(r: ClientType):
    assert r.hset("foo", "key", "value") == 1
    assert r.hget("foo", "key") == b"value"


def test_hset_update(r: ClientType):
    assert r.hset("foo", "key", "value") == 1
    assert r.hset("foo", "key", "value") == 0


def test_hset_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hset("foo", "key", "value")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hgetall(r: ClientType):
    assert r.hset("foo", "k1", "v1") == 1
    assert r.hset("foo", "k2", "v2") == 1
    assert r.hset("foo", "k3", "v3") == 1
    assert r.hgetall("foo") == {b"k1": b"v1", b"k2": b"v2", b"k3": b"v3"}


def test_hgetall_empty_key(r: ClientType):
    assert r.hgetall("foo") == {}


def test_hgetall_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hgetall("foo")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hexists(r: ClientType):
    r.hset("foo", "bar", "v1")
    assert r.hexists("foo", "bar") == 1
    assert r.hexists("foo", "baz") == 0
    assert r.hexists("bar", "bar") == 0


def test_hexists_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hexists("foo", "key")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hkeys(r: ClientType):
    r.hset("foo", "k1", "v1")
    r.hset("foo", "k2", "v2")
    assert set(r.hkeys("foo")) == {b"k1", b"k2"}
    assert set(r.hkeys("bar")) == set()


def test_hkeys_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hkeys("foo")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hlen(r: ClientType):
    r.hset("foo", "k1", "v1")
    r.hset("foo", "k2", "v2")
    assert r.hlen("foo") == 2


def test_hlen_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hlen("foo")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hvals(r: ClientType):
    r.hset("foo", "k1", "v1")
    r.hset("foo", "k2", "v2")
    assert set(r.hvals("foo")) == {b"v1", b"v2"}
    assert set(r.hvals("bar")) == set()


def test_hvals_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hvals("foo")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hmget(r: ClientType):
    r.hset("foo", "k1", "v1")
    r.hset("foo", "k2", "v2")
    r.hset("foo", "k3", "v3")
    # Normal case.
    assert r.hmget("foo", ["k1", "k3"]) == [b"v1", b"v3"]
    assert r.hmget("foo", "k1", "k3") == [b"v1", b"v3"]
    # Key does not exist.
    assert r.hmget("bar", ["k1", "k3"]) == [None, None]
    assert r.hmget("bar", "k1", "k3") == [None, None]
    # Some keys in the hash do not exist.
    assert r.hmget("foo", ["k1", "k500"]) == [b"v1", None]
    assert r.hmget("foo", "k1", "k500") == [b"v1", None]


def test_hmget_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hmget("foo", "key1", "key2")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hdel(r: ClientType):
    r.hset("foo", "k1", "v1")
    r.hset("foo", "k2", "v2")
    r.hset("foo", "k3", "v3")
    assert r.hget("foo", "k1") == b"v1"
    assert r.hdel("foo", "k1") == 1
    assert r.hget("foo", "k1") is None
    assert r.hdel("foo", "k1") == 0
    # Since redis>=2.7.6 returns number of deleted items.
    assert r.hdel("foo", "k2", "k3") == 2
    assert r.hget("foo", "k2") is None
    assert r.hget("foo", "k3") is None
    assert r.hdel("foo", "k2", "k3") == 0


def test_hdel_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hdel("foo", "key")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hincrby(r: ClientType):
    r.hset("foo", "counter", 0)
    assert r.hincrby("foo", "counter") == 1
    assert r.hincrby("foo", "counter") == 2
    assert r.hincrby("foo", "counter") == 3


def test_hincrby_with_no_starting_value(r: ClientType):
    assert r.hincrby("foo", "counter") == 1
    assert r.hincrby("foo", "counter") == 2
    assert r.hincrby("foo", "counter") == 3


def test_hincrby_with_range_param(r: ClientType):
    assert r.hincrby("foo", "counter", 2) == 2
    assert r.hincrby("foo", "counter", 2) == 4
    assert r.hincrby("foo", "counter", 2) == 6


def test_hincrby_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hincrby("foo", "key", 2)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hincrbyfloat(r: ClientType):
    r.hset("foo", "counter", 0.0)
    assert r.hincrbyfloat("foo", "counter") == 1.0
    assert r.hincrbyfloat("foo", "counter") == 2.0
    assert r.hincrbyfloat("foo", "counter") == 3.0


def test_hincrbyfloat_with_no_starting_value(r: ClientType):
    assert r.hincrbyfloat("foo", "counter") == 1.0
    assert r.hincrbyfloat("foo", "counter") == 2.0
    assert r.hincrbyfloat("foo", "counter") == 3.0


def test_hincrbyfloat_with_range_param(r: ClientType):
    assert r.hincrbyfloat("foo", "counter", 0.1) == pytest.approx(0.1)
    assert r.hincrbyfloat("foo", "counter", 0.1) == pytest.approx(0.2)
    assert r.hincrbyfloat("foo", "counter", 0.1) == pytest.approx(0.3)


def test_hincrbyfloat_on_non_float_value_raises_error(r: ClientType):
    r.hset("foo", "counter", "cat")
    with pytest.raises(Exception) as ctx:
        r.hincrbyfloat("foo", "counter")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hincrbyfloat_with_non_float_amount_raises_error(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.hincrbyfloat("foo", "counter", "cat")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hincrbyfloat_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hincrbyfloat("foo", "key", 0.1)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_hincrbyfloat_precision(r: ClientType):
    x = 1.23456789123456789
    assert r.hincrbyfloat("foo", "bar", x) == x
    assert float(r.hget("foo", "bar")) == x


def test_hsetnx(r: ClientType):
    assert r.hsetnx("foo", "newkey", "v1") == 1
    assert r.hsetnx("foo", "newkey", "v1") == 0
    assert r.hget("foo", "newkey") == b"v1"


def test_hmset_empty_raises_error(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.hmset("foo", {})

    assert isinstance(ctx.value, (redis.DataError, valkey.DataError))


@testtools.run_test_if_redispy_ver("lte", "4.6")
def test_hmset_redispy4(r: ClientType):
    r.hset("foo", "k1", "v1")
    assert r.hmset("foo", {"k2": "v2", "k3": "v3"}) is True


def test_hmset_wrong_type(r: ClientType):
    r.zadd("foo", {"bar": 1})
    with pytest.raises(Exception) as ctx:
        r.hmset("foo", {"key": "value"})

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_empty_hash(r: ClientType):
    r.hset("foo", "bar", "baz")
    r.hdel("foo", "bar")
    assert not r.exists("foo")


def test_hset_removing_last_field_delete_key(r: ClientType):
    r.hset(b"3L", b"f1", b"v1")
    r.hdel(b"3L", b"f1")
    assert r.keys("*") == []


@pytest.mark.supported_server_versions(min_redis_ver="7.4")
@testtools.run_test_if_redispy_ver("gte", "5")
def test_hscan_no_values(r: ClientType):
    name = "hscan-test"
    for ix in range(20):
        k = f"key:{ix}"
        v = f"result:{ix}"
        r.hset(name, k, v)
    expected = r.hgetall(name)
    assert len(expected) == 20  # Ensure we know what we're testing

    # Test that we page through the results and get everything out
    results = set()
    cursor = "0"
    while cursor != 0:
        cursor, data = r.hscan(name, cursor, count=6, no_values=True)
        results.update(data)
    assert results == set(expected.keys())


def test_hscan(r: ClientType):
    # Set up the data
    name = "hscan-test"
    for ix in range(20):
        k = f"key:{ix}"
        v = f"result:{ix}"
        r.hset(name, k, v)
    expected = r.hgetall(name)
    assert len(expected) == 20  # Ensure we know what we're testing

    # Test that we page through the results and get everything out
    results = {}
    cursor = "0"
    while cursor != 0:
        cursor, data = r.hscan(name, cursor, count=6)
        results.update(data)
    assert expected == results

    # Test the iterator version
    results = {}
    for key, val in r.hscan_iter(name, count=6):
        results[key] = val
    assert expected == results

    # Now test that the MATCH functionality works
    results = {}
    cursor = "0"
    while cursor != 0:
        cursor, data = r.hscan(name, cursor, match="*7", count=100)
        results.update(data)
    assert b"key:7" in results
    assert b"key:17" in results
    assert len(results) == 2

    # Test the match on iterator
    results = {}
    for key, val in r.hscan_iter(name, match="*7"):
        results[key] = val
    assert b"key:7" in results
    assert b"key:17" in results
    assert len(results) == 2


def test_hrandfield(r: ClientType):
    assert r.hrandfield("key") is None
    hash = {b"a": 1, b"b": 2, b"c": 3, b"d": 4, b"e": 5}
    r.hset("key", mapping=hash)
    assert r.hrandfield("key") is not None
    assert len(r.hrandfield("key", 0)) == 0
    res = r.hrandfield("key", 2)
    assert len(res) == 2
    assert res[0] in set(hash.keys())
    assert res[1] in set(hash.keys())
    # with values
    res = r.hrandfield("key", 2, True)
    assert len(res) == resp_conversion(r, 2, 4)
    if testtools.get_protocol_version(r) == 2:
        assert res[0] in set(hash.keys())
        assert res[1] in {str(x).encode() for x in hash.values()}
        assert res[2] in set(hash.keys())
        assert res[3] in {str(x).encode() for x in hash.values()}
    else:
        assert res[0][1] in {str(x).encode() for x in hash.values()}
        assert res[1][1] in {str(x).encode() for x in hash.values()}
        assert res[0][0] in set(hash.keys())
        assert res[1][0] in set(hash.keys())
    # without duplications
    assert len(r.hrandfield("key", 10)) == 5
    # with duplications
    assert len(r.hrandfield("key", -10)) == 10

    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "HRANDFIELD", "key", 3, "WITHVALUES", 3)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


himport_test = pytest.mark.supported_server_versions(min_redis_ver="8.10")
himport_servers = pytest.mark.unsupported_server_types("valkey", "dragonfly", "kividb")


@himport_test
@himport_servers
def test_himport_set(r: ClientType):
    assert raw_command(r, "HIMPORT", "PREPARE", "fs", "b", "a", "c") == b"OK"
    assert raw_command(r, "HIMPORT", "SET", "foo", "fs", "1", "2", "3") == b"OK"
    # Values follow the order the fields were prepared in.
    assert r.hgetall("foo") == {b"a": b"2", b"b": b"1", b"c": b"3"}
    assert r.type("foo") == b"hash"


@himport_test
@himport_servers
def test_himport_set_field_order(r: ClientType):
    # The fieldset is sorted by length, then bytewise.
    raw_command(r, "HIMPORT", "PREPARE", "fs", "10", "9", "a", "B", "aa", "")
    raw_command(r, "HIMPORT", "SET", "foo", "fs", "v1", "v2", "v3", "v4", "v5", "v6")
    assert r.hkeys("foo") == [b"", b"9", b"B", b"a", b"10", b"aa"]
    assert r.hvals("foo") == [b"v6", b"v2", b"v4", b"v3", b"v1", b"v5"]


@himport_test
@himport_servers
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


@himport_test
@himport_servers
def test_himport_set_then_hash_commands(r: ClientType):
    raw_command(r, "HIMPORT", "PREPARE", "fs", "a", "b")
    raw_command(r, "HIMPORT", "SET", "foo", "fs", "1", "2")
    assert r.hincrby("foo", "a", 5) == 6
    assert r.hset("foo", "c", "3") == 1
    assert r.hdel("foo", "b") == 1
    assert r.hgetall("foo") == {b"a": b"6", b"c": b"3"}
    assert r.hdel("foo", "a", "c") == 2
    assert r.exists("foo") == 0


@himport_test
@himport_servers
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


@himport_test
@himport_servers
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


@himport_test
@himport_servers
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


@himport_test
@himport_servers
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


@himport_test
@himport_servers
def test_himport_fieldsets_belong_to_the_connection(r: ClientType, create_connection):
    other = create_connection()
    raw_command(r, "HIMPORT", "PREPARE", "fs", "a")
    with pytest.raises(redis.ResponseError, match="no such fieldset"):
        raw_command(other, "HIMPORT", "SET", "foo", "fs", "1")
    assert raw_command(other, "HIMPORT", "DISCARD", "fs") == 0
    assert raw_command(other, "HIMPORT", "DISCARDALL") == 0
    assert raw_command(r, "HIMPORT", "SET", "foo", "fs", "1") == b"OK"


@himport_test
@himport_servers
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


@himport_test
@himport_servers
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


@himport_test
@himport_servers
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
