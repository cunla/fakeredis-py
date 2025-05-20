import time
from datetime import timedelta

import pytest
from packaging.version import Version
from redis import exceptions

from test import testtools
from test.testtools import redis_server_time, REDIS_PY_VERSION

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.min_server("7.9"),
        testtools.run_test_if_redispy_ver("gte", "5.9"),
    ]
)

if REDIS_PY_VERSION >= Version("5.9"):
    from redis.commands.core import HashDataPersistOptions


def test_hgetdel(r):
    r.delete("test:hash")
    r.hset("test:hash", "foo", "bar", mapping={"1": 1, "2": 2})
    assert r.hgetdel("test:hash", "foo", "1") == [b"bar", b"1"]
    assert r.hget("test:hash", "foo") is None
    assert r.hget("test:hash", "1") is None
    assert r.hget("test:hash", "2") == b"2"
    assert r.hgetdel("test:hash", "foo", "1") == [None, None]
    assert r.hget("test:hash", "2") == b"2"

    with pytest.raises(exceptions.DataError):
        r.hgetdel("test:hash")


def test_hgetex_no_expiration(r):
    r.delete("test:hash")
    r.hset("b", "foo", "bar", mapping={"1": 1, "2": 2, "3": "three", "4": b"four"})

    assert r.hgetex("b", "foo", "1", "4") == [b"bar", b"1", b"four"]
    assert r.httl("b", "foo", "1", "4") == [-1, -1, -1]


def test_hgetex_expiration_configs(r):
    r.delete("test:hash")
    r.hset("test:hash", "foo", "bar", mapping={"1": 1, "3": "three", "4": b"four"})
    test_keys = ["foo", "1", "4"]

    # test get with multiple fields with expiration set through 'ex'
    assert r.hgetex("test:hash", *test_keys, ex=10) == [b"bar", b"1", b"four"]
    ttls = r.httl("test:hash", *test_keys)
    for ttl in ttls:
        assert pytest.approx(ttl, 1) == 10

    # test get with multiple fields removing expiration settings with 'persist'
    assert r.hgetex("test:hash", *test_keys, persist=True) == [
        b"bar",
        b"1",
        b"four",
    ]
    assert r.httl("test:hash", *test_keys) == [-1, -1, -1]

    # test get with multiple fields with expiration set through 'px'
    assert r.hgetex("test:hash", *test_keys, px=6000) == [b"bar", b"1", b"four"]
    ttls = r.httl("test:hash", *test_keys)
    for ttl in ttls:
        assert pytest.approx(ttl, 1) == 6

    # test get single field with expiration set through 'pxat'
    expire_at = redis_server_time(r) + timedelta(minutes=1)
    assert r.hgetex("test:hash", "foo", pxat=expire_at) == [b"bar"]
    assert r.httl("test:hash", "foo")[0] <= 61

    # test get single field with expiration set through 'exat'
    expire_at = redis_server_time(r) + timedelta(seconds=10)
    assert r.hgetex("test:hash", "foo", exat=expire_at) == [b"bar"]
    assert r.httl("test:hash", "foo")[0] <= 10


def test_hgetex_validate_expired_fields_removed(r):
    r.delete("test:hash")
    r.hset("test:hash", "foo", "bar", mapping={"1": 1, "3": "three", "4": b"four"})

    test_keys = ["foo", "1", "3"]
    # test get multiple fields with expiration set
    # validate that expired fields are removed
    assert r.hgetex("test:hash", *test_keys, ex=1) == [b"bar", b"1", b"three"]
    time.sleep(1.1)
    assert r.hgetex("test:hash", *test_keys) == [None, None, None]
    assert r.httl("test:hash", *test_keys) == [-2, -2, -2]
    assert r.hgetex("test:hash", "4") == [b"four"]


def test_hgetex_invalid_inputs(r):
    with pytest.raises(exceptions.DataError):
        r.hgetex("b", "foo", "1", "3", ex=10, persist=True)

    with pytest.raises(exceptions.DataError):
        r.hgetex("b", "foo", ex=10.0, persist=True)

    with pytest.raises(exceptions.DataError):
        r.hgetex("b", "foo", ex=10, px=6000)

    with pytest.raises(exceptions.DataError):
        r.hgetex("b", ex=10)


def test_hsetex_no_expiration(r):
    r.delete("test:hash")

    # # set items from mapping without expiration
    assert r.hsetex("test:hash", None, None, mapping={"1": 1, "4": b"four"}) == 1
    assert r.httl("test:hash", "foo", "1", "4") == [-2, -1, -1]
    assert r.hgetex("test:hash", "foo", "1") == [None, b"1"]


def test_hsetex_expiration_ex_and_keepttl(r):
    r.delete("test:hash")

    # set items from key/value provided
    # combined with mapping and items with expiration - testing ex field
    assert (
        r.hsetex(
            "test:hash",
            "foo",
            "bar",
            mapping={"1": 1, "2": "2"},
            items=["i1", 11, "i2", 22],
            ex=10,
        )
        == 1
    )
    ttls = r.httl("test:hash", "foo", "1", "2", "i1", "i2")
    for ttl in ttls:
        assert pytest.approx(ttl, 1) == 10

    assert r.hgetex("test:hash", "foo", "1", "2", "i1", "i2") == [b"bar", b"1", b"2", b"11", b"22"]
    time.sleep(1.1)
    # validate keepttl
    assert r.hsetex("test:hash", "foo", "bar1", keepttl=True) == 1
    assert r.httl("test:hash", "foo")[0] < 10


def test_hsetex_expiration_px(r):
    r.delete("test:hash")
    # set items from key/value provided and mapping
    # with expiration - testing px field
    assert r.hsetex("test:hash", "foo", "bar", mapping={"1": 1, "2": "2"}, px=60000) == 1
    test_keys = ["foo", "1", "2"]
    ttls = r.httl("test:hash", *test_keys)
    for ttl in ttls:
        assert pytest.approx(ttl, 1) == 60
    assert r.hgetex("test:hash", *test_keys) == [b"bar", b"1", b"2"]


def test_hsetex_expiration_pxat_and_fnx(r):
    r.delete("test:hash")
    assert r.hsetex("test:hash", "foo", "bar", mapping={"1": 1, "2": "2"}, ex=30) == 1

    expire_at = redis_server_time(r) + timedelta(minutes=1)
    assert (
        r.hsetex(
            "test:hash",
            "foo",
            "bar1",
            mapping={"new": "ok"},
            pxat=expire_at,
            data_persist_option=HashDataPersistOptions.FNX,
        )
        == 0
    )
    ttls = r.httl("test:hash", "foo", "new")
    assert ttls[0] <= 30
    assert ttls[1] == -2

    assert r.hgetex("test:hash", "foo", "1", "new") == [b"bar", b"1", None]
    assert (
        r.hsetex(
            "test:hash",
            "foo_new",
            "bar1",
            mapping={"new": "ok"},
            pxat=expire_at,
            data_persist_option=HashDataPersistOptions.FNX,
        )
        == 1
    )
    ttls = r.httl("test:hash", "foo", "new")
    for ttl in ttls:
        assert ttl <= 61
    assert r.hgetex("test:hash", "foo", "foo_new", "new") == [b"bar", b"bar1", b"ok"]


def test_hsetex_expiration_exat_and_fxx(r):
    r.delete("test:hash")
    assert r.hsetex("test:hash", "foo", "bar", mapping={"1": 1, "2": "2"}, ex=30) == 1

    expire_at = redis_server_time(r) + timedelta(seconds=10)
    assert (
        r.hsetex(
            "test:hash",
            "foo",
            "bar1",
            mapping={"new": "ok"},
            exat=expire_at,
            data_persist_option=HashDataPersistOptions.FXX,
        )
        == 0
    )
    ttls = r.httl("test:hash", "foo", "new")
    assert 10 < ttls[0] <= 30
    assert ttls[1] == -2

    assert r.hgetex("test:hash", "foo", "1", "new") == [b"bar", b"1", None]
    assert (
        r.hsetex(
            "test:hash",
            "foo",
            "bar1",
            mapping={"1": "new_value"},
            exat=expire_at,
            data_persist_option=HashDataPersistOptions.FXX,
        )
        == 1
    )
    assert r.hgetex("test:hash", "foo", "1") == [b"bar1", b"new_value"]


def test_hsetex_invalid_inputs(r):
    with pytest.raises(exceptions.DataError):
        r.hsetex("b", "foo", "bar", ex=10.0)

    with pytest.raises(exceptions.DataError):
        r.hsetex("b", None, None)

    with pytest.raises(exceptions.DataError):
        r.hsetex("b", "foo", "bar", items=["i1", 11, "i2"], px=6000)

    with pytest.raises(exceptions.DataError):
        r.hsetex("b", "foo", "bar", ex=10, keepttl=True)
