from __future__ import annotations

import time
from datetime import timedelta

import pytest
import redis
import redis.client
import valkey

from fakeredis._helpers import current_time
from fakeredis._typing import ClientType
from .. import testtools
from ..testtools import raw_command, resp_conversion


def test_append(r: ClientType):
    assert r.set("foo", "bar")
    assert r.append("foo", "baz") == 6
    assert r.get("foo") == b"barbaz"


def test_append_with_no_preexisting_key(r: ClientType):
    assert r.append("foo", "bar") == 3
    assert r.get("foo") == b"bar"


def test_append_wrong_type(r: ClientType):
    r.rpush("foo", b"x")
    with pytest.raises(Exception) as ctx:
        r.append("foo", b"x")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_decr(r: ClientType):
    r.set("foo", 10)
    assert r.decr("foo") == 9
    assert r.get("foo") == b"9"


def test_decr_newkey(r: ClientType):
    r.decr("foo")
    assert r.get("foo") == b"-1"


def test_decr_expiry(r: ClientType):
    r.set("foo", 10, ex=10)
    r.decr("foo", 5)
    assert r.ttl("foo") > 0


def test_decr_badtype(r: ClientType):
    r.set("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.decr("foo", 15)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    r.rpush("foo2", 1)
    with pytest.raises(Exception) as ctx:
        r.decr("foo2", 15)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_get_does_not_exist(r: ClientType):
    assert r.get("foo") is None


def test_get_with_non_str_keys(r: ClientType):
    assert r.set("2", "bar") is True
    assert r.get(2) == b"bar"


def test_get_invalid_type(r: ClientType):
    assert r.hset("foo", "key", "value") == 1
    with pytest.raises(Exception) as ctx:
        r.get("foo")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_getset_exists(r: ClientType):
    r.set("foo", "bar")
    val = r.getset("foo", b"baz")
    assert val == b"bar"
    val = r.getset("foo", b"baz2")
    assert val == b"baz"


def test_getset_wrong_type(r: ClientType):
    r.rpush("foo", b"x")
    with pytest.raises(Exception) as ctx:
        r.getset("foo", "bar")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_getdel(r: ClientType):
    r["foo"] = "bar"
    assert r.getdel("foo") == b"bar"
    assert r.get("foo") is None


def test_getdel_doesnt_exist(r: ClientType):
    assert r.getdel("foo") is None


def test_incr_with_no_preexisting_key(r: ClientType):
    assert r.incr("foo") == 1
    assert r.incr("bar", 2) == 2


def test_incr_by(r: ClientType):
    assert r.incrby("foo") == 1
    assert r.incrby("bar", 2) == 2


def test_incr_preexisting_key(r: ClientType):
    r.set("foo", 15)
    assert r.incr("foo", 5) == 20
    assert r.get("foo") == b"20"


def test_incr_expiry(r: ClientType):
    r.set("foo", 15, ex=10)
    r.incr("foo", 5)
    assert r.ttl("foo") > 0


def test_incr_bad_type(r: ClientType):
    r.set("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.incr("foo", 15)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    r.rpush("foo2", 1)
    with pytest.raises(Exception) as ctx:
        r.incr("foo2", 15)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_incr_with_float(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.incr("foo", 2.0)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_incr_followed_by_mget(r: ClientType):
    r.set("foo", 15)
    assert r.incr("foo", 5) == 20
    assert r.get("foo") == b"20"


def test_incr_followed_by_mget_returns_strings(r: ClientType):
    r.incr("foo", 1)
    assert r.mget(["foo"]) == [b"1"]


def test_incrbyfloat(r: ClientType):
    r.set("foo", 0)
    assert r.incrbyfloat("foo", 1.0) == 1.0
    assert r.incrbyfloat("foo", 1.0) == 2.0


def test_incrbyfloat_with_noexist(r: ClientType):
    assert r.incrbyfloat("foo", 1.0) == 1.0
    assert r.incrbyfloat("foo", 1.0) == 2.0


def test_incrbyfloat_expiry(r: ClientType):
    r.set("foo", 1.5, ex=10)
    r.incrbyfloat("foo", 2.5)
    assert r.ttl("foo") > 0


def test_incrbyfloat_bad_type(r: ClientType):
    r.set("foo", "bar")
    with pytest.raises(Exception, match="not a valid float") as ctx:
        r.incrbyfloat("foo", 1.0)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    r.rpush("foo2", 1)
    with pytest.raises(Exception) as ctx:
        r.incrbyfloat("foo2", 1.0)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_incrbyfloat_precision(r: ClientType):
    x = 1.23456789123456789
    assert r.incrbyfloat("foo", x) == x
    assert float(r.get("foo")) == x


def test_mget(r: ClientType):
    r.set("foo", "one")
    r.set("bar", "two")
    assert r.mget(["foo", "bar"]) == [b"one", b"two"]
    assert r.mget(["foo", "bar", "baz"]) == [b"one", b"two", None]
    assert r.mget("foo", "bar") == [b"one", b"two"]


def test_mget_with_no_keys(r: ClientType):
    assert r.mget([]) == []


def test_mget_mixed_types(r: ClientType):
    r.hset("hash", "bar", "baz")
    r.zadd("zset", {"bar": 1})
    r.sadd("set", "member")
    r.rpush("list", "item1")
    r.set("string", "value")
    assert r.mget(["hash", "zset", "set", "string", "absent"]) == [None, None, None, b"value", None]


def test_mset_with_no_keys(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.mset({})
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_mset(r: ClientType):
    assert r.mset({"foo": "one", "bar": "two"}) is True
    assert r.mset({"foo": "one", "bar": "two"}) is True
    assert r.mget("foo", "bar") == [b"one", b"two"]


def test_msetnx(r: ClientType):
    assert r.msetnx({"foo": "one", "bar": "two"})
    assert not r.msetnx({"bar": "two", "baz": "three"})
    assert r.mget("foo", "bar", "baz") == [b"one", b"two", None]


def test_setex(r: ClientType):
    assert r.setex("foo", 100, "bar") is True
    assert r.get("foo") == b"bar"


def test_setex_using_timedelta(r: ClientType):
    assert r.setex("foo", timedelta(seconds=100), "bar") is True
    assert r.get("foo") == b"bar"


def test_setex_using_float(r: ClientType):
    with pytest.raises(Exception, match="integer") as ctx:
        r.setex("foo", 1.2, "bar")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.supported_redis_versions(min_ver="6.2")
def test_setex_overflow(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.setex("foo", 18446744073709561, "bar")  # Overflows longlong in ms
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_set_ex(r: ClientType):
    assert r.set("foo", "bar", ex=100) is True
    assert r.get("foo") == b"bar"


@pytest.mark.supported_redis_versions(min_ver="6.2")
def test_set_exat(r: ClientType):
    curr_time = int(time.time())
    assert r.set("foo", "bar", exat=curr_time + 100) is True
    assert r.get("foo") == b"bar"


@pytest.mark.supported_redis_versions(min_ver="6.2")
def test_set_pxat(r: ClientType):
    curr_time = current_time()
    assert r.set("foo", "bar", pxat=curr_time + 100) is True
    assert r.get("foo") == b"bar"
    time.sleep(0.15)
    assert r.get("foo") is None


def test_set_ex_using_timedelta(r: ClientType):
    assert r.set("foo", "bar", ex=timedelta(seconds=100)) is True
    assert r.get("foo") == b"bar"


def test_set_ex_overflow(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", ex=18446744073709561)  # Overflows longlong in ms
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_set_px_overflow(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", px=2**63 - 2)  # Overflows after adding current time
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_set_px(r: ClientType):
    assert r.set("foo", "bar", px=100) is True
    assert r.get("foo") == b"bar"


def test_set_px_using_timedelta(r: ClientType):
    assert r.set("foo", "bar", px=timedelta(milliseconds=100)) is True
    assert r.get("foo") == b"bar"


@testtools.run_test_if_redispy_ver("lt", "5.9")  # This will run for redis-py 4.2.0 or above.
def test_set_conflicting_expire_options(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", ex=1, px=1)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_set_raises_wrong_ex(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", ex=-100)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", ex=0)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert not r.exists("foo")


def test_set_using_timedelta_raises_wrong_ex(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", ex=timedelta(seconds=-100))
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", ex=timedelta(seconds=0))
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert not r.exists("foo")


def test_set_raises_wrong_px(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", px=-100)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", px=0)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert not r.exists("foo")


def test_set_using_timedelta_raises_wrong_px(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", px=timedelta(milliseconds=-100))
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.set("foo", "bar", px=timedelta(milliseconds=0))
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert not r.exists("foo")


def test_setex_raises_wrong_ex(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.setex("foo", -100, "bar")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.setex("foo", 0, "bar")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert not r.exists("foo")


def test_setex_using_timedelta_raises_wrong_ex(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.setex("foo", timedelta(seconds=-100), "bar")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.setex("foo", timedelta(seconds=-100), "bar")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert not r.exists("foo")


def test_setnx(r: ClientType):
    assert r.setnx("foo", "bar")
    assert r.get("foo") == b"bar"
    assert not r.setnx("foo", "baz")
    assert r.get("foo") == b"bar"


def test_set_nx(r: ClientType):
    assert r.set("foo", "bar", nx=True) is True
    assert r.get("foo") == b"bar"
    assert r.set("foo", "bar", nx=True) is None
    assert r.get("foo") == b"bar"


def test_set_xx(r: ClientType):
    assert r.set("foo", "bar", xx=True) is None
    r.set("foo", "bar")
    assert r.set("foo", "bar", xx=True) is True


@pytest.mark.supported_redis_versions(min_ver="6.2")
def test_set_get(r: ClientType):
    assert raw_command(r, "set", "foo", "bar", "GET") is None
    assert r.get("foo") == b"bar"
    assert raw_command(r, "set", "foo", "baz", "GET") == b"bar"
    assert r.get("foo") == b"baz"


@pytest.mark.supported_redis_versions(min_ver="6.2")
def test_set_get_xx(r: ClientType):
    assert raw_command(r, "set", "foo", "bar", "XX", "GET") is None
    assert r.get("foo") is None
    r.set("foo", "bar")
    assert raw_command(r, "set", "foo", "baz", "XX", "GET") == b"bar"
    assert r.get("foo") == b"baz"
    assert raw_command(r, "set", "foo", "baz", "GET") == b"baz"


@pytest.mark.supported_redis_versions(min_ver="7")
def test_set_get_nx_redis7(r: ClientType):
    # Note: this will most likely fail on a 7.0 server, based on the docs for SET
    assert raw_command(r, "set", "foo", "bar", "NX", "GET") is None


@pytest.mark.supported_redis_versions(min_ver="6.2")
def set_get_wrongtype(r: ClientType):
    r.lpush("foo", "bar")
    with pytest.raises(Exception) as ctx:
        raw_command(r, "set", "foo", "bar", "GET")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_substr(r: ClientType):
    r["foo"] = "one_two_three"
    assert r.substr("foo", 0) == b"one_two_three"
    assert r.substr("foo", 0, 2) == b"one"
    assert r.substr("foo", 4, 6) == b"two"
    assert r.substr("foo", -5) == b"three"
    assert r.substr("foo", -4, -5) == b""
    assert r.substr("foo", -5, -3) == b"thr"


def test_substr_noexist_key(r: ClientType):
    assert r.substr("foo", 0) == b""
    assert r.substr("foo", 10) == b""
    assert r.substr("foo", -5, -1) == b""


def test_substr_wrong_type(r: ClientType):
    r.rpush("foo", b"x")
    with pytest.raises(Exception) as ctx:
        r.substr("foo", 0)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_strlen(r: ClientType):
    r["foo"] = "bar"

    assert r.strlen("foo") == 3
    assert r.strlen("noexists") == 0


def test_strlen_wrong_type(r: ClientType):
    r.rpush("foo", b"x")
    with pytest.raises(Exception) as ctx:
        r.strlen("foo")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_setrange(r: ClientType):
    r.set("foo", "test")
    assert r.setrange("foo", 1, "aste") == 5
    assert r.get("foo") == b"taste"

    r.set("foo", "test")
    assert r.setrange("foo", 1, "a") == 4
    assert r.get("foo") == b"tast"

    assert r.setrange("bar", 2, "test") == 6
    assert r.get("bar") == b"\x00\x00test"

    assert r.setrange("bar", 501970112, "test") == 501970116


def test_setrange_expiry(r: ClientType):
    r.set("foo", "test", ex=10)
    r.setrange("foo", 1, "aste")
    assert r.ttl("foo") > 0


def test_large_command(r: ClientType):
    r.set("foo", "bar" * 10000)
    assert r.get("foo") == b"bar" * 10000


def test_saving_non_ascii_chars_as_value(r: ClientType):
    assert r.set("foo", "Ñandu") is True
    assert r.get("foo") == "Ñandu".encode()


def test_saving_unicode_type_as_value(r: ClientType):
    assert r.set("foo", "Ñandu") is True
    assert r.get("foo") == "Ñandu".encode()


def test_saving_non_ascii_chars_as_key(r: ClientType):
    assert r.set("Ñandu", "foo") is True
    assert r.get("Ñandu") == b"foo"


def test_saving_unicode_type_as_key(r: ClientType):
    assert r.set("Ñandu", "foo") is True
    assert r.get("Ñandu") == b"foo"


def test_future_newbytes(r: ClientType):
    # bytes = pytest.importorskip('builtins', reason='future.types not available').bytes
    r.set(bytes(b"\xc3\x91andu"), "foo")
    assert r.get("Ñandu") == b"foo"


def test_future_newstr(r: ClientType):
    # str = pytest.importorskip('builtins', reason='future.types not available').str
    r.set(str("Ñandu"), "foo")
    assert r.get("Ñandu") == b"foo"


def test_setitem_getitem(r: ClientType):
    assert r.keys() == []
    r["foo"] = "bar"
    assert r["foo"] == b"bar"


def test_getitem_non_existent_key(r: ClientType):
    assert r.keys() == []
    assert "noexists" not in r.keys()


@pytest.mark.slow
def test_getex(r: ClientType):
    # Exceptions
    with pytest.raises(Exception) as ctx:
        raw_command(r, "getex", "foo", "px", 1000, "ex", 1)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        raw_command(r, "getex", "foo", "dsac", 1000, "ex", 1)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    r.set("foo", "val")
    assert r.getex("foo", ex=1) == b"val"
    time.sleep(1.5)
    assert r.get("foo") is None

    r.set("foo2", "val")
    assert r.getex("foo2", px=1000) == b"val"
    time.sleep(1.5)
    assert r.get("foo2") is None

    r.set("foo4", "val")
    r.getex("foo4", exat=int(time.time() + 1))
    time.sleep(1.5)
    assert r.get("foo4") is None

    r.set("foo2", "val")
    r.getex("foo2", pxat=int(time.time() + 1) * 1000)
    time.sleep(1.5)
    assert r.get("foo2") is None

    r.setex("foo5", 1, "val")
    r.getex("foo5", persist=True)
    assert r.ttl("foo5") == -1
    time.sleep(1.5)
    assert r.get("foo5") == b"val"


@pytest.mark.supported_redis_versions(min_ver="7")
def test_lcs(r: ClientType):
    r.mset({"key1": "ohmytext", "key2": "mynewtext"})
    assert r.lcs("key1", "key2") == b"mytext"
    assert r.lcs("key1", "key2", len=True) == 6

    assert r.lcs("key1", "key2", idx=True, minmatchlen=3, withmatchlen=True) == resp_conversion(
        r, {b"len": 6, b"matches": [[[4, 7], [5, 8], 4]]}, [b"matches", [[[4, 7], [5, 8], 4]], b"len", 6]
    )
    assert r.lcs("key1", "key2", idx=True, minmatchlen=3) == resp_conversion(
        r, {b"len": 6, b"matches": [[[4, 7], [5, 8]]]}, [b"matches", [[[4, 7], [5, 8]]], b"len", 6]
    )

    with pytest.raises(Exception) as ctx:
        assert r.lcs("key1", "key2", len=True, idx=True)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        raw_command(r, "lcs", "key1", "key2", "not_supported_arg")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
