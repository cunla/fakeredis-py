import time
from typing import Optional, Dict

import pytest
import redis.client

from test import testtools

pytestmark = []
pytestmark.extend([pytest.mark.min_server("7.4"), testtools.run_test_if_redispy_ver("gte", "5")])


@pytest.mark.parametrize(
    "expiration_seconds,preset_expiration,flags,expected_result",
    [
        # No flags
        (100, None, dict(), 1),
        (100, 50, dict(), 1),
        # NX
        (100, None, dict(nx=True), 1),
        (100, 50, dict(nx=True), 0),
        # XX
        (100, None, dict(xx=True), 0),
        (100, 50, dict(xx=True), 1),
        # GT
        (100, None, dict(gt=True), 0),
        (100, 50, dict(gt=True), 1),
        (100, 101, dict(gt=True), 0),
        (100, 200, dict(gt=True), 0),
        # LT
        (100, None, dict(lt=True), 1),
        (100, 50, dict(lt=True), 0),
        (100, 100, dict(lt=True), 0),
        (100, 200, dict(lt=True), 1),
    ],
)
def test_hexpire(
    r: redis.Redis,
    expiration_seconds: int,
    preset_expiration: Optional[int],
    flags: Dict[str, bool],
    expected_result: int,
) -> None:
    key, field = "redis-key", "hash-key"
    r.hset(key, field, "value")
    if preset_expiration is not None:
        assert r.hexpire(key, preset_expiration, field) == [1]
    result = r.hexpire(key, expiration_seconds, field, **flags)
    assert result == [expected_result]


@pytest.mark.slow
def test_hexpire_basic(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1", "field2": "value2"})
    assert r.hexpire("redis-key", 1, "field1") == [1]
    time.sleep(1.1)
    assert r.hexists("redis-key", "field1") is False
    assert r.hexists("redis-key", "field2") is True


@pytest.mark.slow
def test_hexpire_conditions(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1"})
    assert r.hexpire("redis-key", 2, "field1", xx=True) == [0]
    assert r.hexpire("redis-key", 2, "field1", nx=True) == [1]
    assert r.hexpire("redis-key", 1, "field1", xx=True) == [1]
    assert r.hexpire("redis-key", 2, "field1", nx=True) == [0]
    time.sleep(1.1)
    assert r.hexists("redis-key", "field1") is False
    r.hset("redis-key", "field1", "value1")
    r.hexpire("redis-key", 2, "field1")
    assert r.hexpire("redis-key", 1, "field1", gt=True) == [0]
    assert r.hexpire("redis-key", 1, "field1", lt=True) == [1]
    time.sleep(1.1)
    assert r.hexists("redis-key", "field1") is False


def test_hexpire_nonexistent_key_or_field(r: redis.Redis):
    r.delete("redis-key")
    assert r.hexpire("redis-key", 1, "field1") == [-2]
    r.hset("redis-key", "field1", "value1")
    assert r.hexpire("redis-key", 1, "nonexistent_field") == [-2]


def test_hexpire_after_hset(r: redis.Redis):
    r.delete("redis-key")
    assert r.hexpire("redis-key", 5, "field1") == [-2]
    r.hset("redis-key", "field1", "value1")
    assert r.hexpire("redis-key", 1, "field1") == [1]
    assert r.hset("redis-key", "field1", "value1") == 0
    assert r.hexpire("redis-key", 3, "field1", lt=True) == [1]


@pytest.mark.slow
def test_hexpire_multiple_fields(r: redis.Redis):
    r.delete("redis-key")
    r.hset(
        "redis-key",
        mapping={"field1": "value1", "field2": "value2", "field3": "value3"},
    )
    assert r.hexpire("redis-key", 1, "field1", "field2") == [1, 1]
    time.sleep(1.1)
    assert r.hexists("redis-key", "field1") is False
    assert r.hexists("redis-key", "field2") is False
    assert r.hexists("redis-key", "field3") is True


def test_hpexpire_basic(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1", "field2": "value2"})
    assert r.hpexpire("redis-key", 100, "field1") == [1]
    time.sleep(0.11)
    assert r.hexists("redis-key", "field1") is False
    assert r.hexists("redis-key", "field2") is True


@pytest.mark.slow
def test_hpexpire_conditions(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1"})
    assert r.hpexpire("redis-key", 1500, "field1", xx=True) == [0]
    assert r.hpexpire("redis-key", 1500, "field1", nx=True) == [1]
    assert r.hpexpire("redis-key", 500, "field1", xx=True) == [1]
    assert r.hpexpire("redis-key", 1500, "field1", nx=True) == [0]
    time.sleep(0.6)
    assert r.hexists("redis-key", "field1") is False
    r.hset("redis-key", "field1", "value1")
    r.hpexpire("redis-key", 1000, "field1")
    assert r.hpexpire("redis-key", 500, "field1", gt=True) == [0]
    assert r.hpexpire("redis-key", 500, "field1", lt=True) == [1]
    time.sleep(0.6)
    assert r.hexists("redis-key", "field1") is False


def test_hpexpire_nonexistent_key_or_field(r: redis.Redis):
    r.delete("redis-key")
    assert r.hpexpire("redis-key", 500, "field1") == [-2]
    r.hset("redis-key", "field1", "value1")
    assert r.hpexpire("redis-key", 500, "nonexistent_field") == [-2]


def test_hpexpire_multiple_fields(r: redis.Redis):
    r.delete("redis-key")
    r.hset(
        "redis-key",
        mapping={"field1": "value1", "field2": "value2", "field3": "value3"},
    )
    assert r.hpexpire("redis-key", 100, "field1", "field2") == [1, 1]
    time.sleep(0.11)
    assert r.hexists("redis-key", "field1") is False
    assert r.hexists("redis-key", "field2") is False
    assert r.hexists("redis-key", "field3") is True


def test_hpexpire_multiple_condition_flags_error(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1"})
    with pytest.raises(ValueError) as e:
        r.hpexpire("redis-key", 500, "field1", nx=True, xx=True)
    assert "Only one of" in str(e)


@pytest.mark.slow
def test_hexpireat_basic(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1", "field2": "value2"})
    exp_time = (testtools.current_time() + 1000) // 1000
    assert r.hexpireat("redis-key", exp_time, "field1") == [1]
    time.sleep(1.1)
    assert r.hexists("redis-key", "field1") is False
    assert r.hexists("redis-key", "field2") is True


def test_hexpireat_conditions(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1"})
    future_exp_time = testtools.current_time() // 1000 + 20
    past_exp_time = testtools.current_time() // 1000 - 10
    assert r.hexpireat("redis-key", future_exp_time, "field1", xx=True) == [0]
    assert r.hexpireat("redis-key", future_exp_time, "field1", nx=True) == [1]
    assert r.hexpireat("redis-key", past_exp_time, "field1", gt=True) == [0]
    assert r.hexpireat("redis-key", past_exp_time, "field1", lt=True) == [2]
    assert r.hexists("redis-key", "field1") is False


def test_hexpireat_nonexistent_key_or_field(r: redis.Redis):
    r.delete("redis-key")
    future_exp_time = (testtools.current_time() + 1000) // 1000
    assert r.hexpireat("redis-key", future_exp_time, "field1") == [-2]
    r.hset("redis-key", "field1", "value1")
    assert r.hexpireat("redis-key", future_exp_time, "nonexistent_field") == [-2]


def test_hexpireat_multiple_fields(r: redis.Redis):
    r.delete("redis-key")
    r.hset(
        "redis-key",
        mapping={"field1": "value1", "field2": "value2", "field3": "value3"},
    )
    exp_time = (testtools.current_time() + 1000) // 1000
    assert r.hexpireat("redis-key", exp_time, "field1", "field2") == [1, 1]
    time.sleep(1.1)
    assert r.hexists("redis-key", "field1") is False
    assert r.hexists("redis-key", "field2") is False
    assert r.hexists("redis-key", "field3") is True


def test_hexpireat_multiple_condition_flags_error(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1"})
    exp_time = (testtools.current_time() + 1000) // 1000
    with pytest.raises(ValueError) as e:
        r.hexpireat("redis-key", exp_time, "field1", nx=True, xx=True)
    assert "Only one of" in str(e)


def test_hpexpireat_basic(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1", "field2": "value2"})
    exp_time = testtools.current_time() + 100
    assert r.hpexpireat("redis-key", exp_time, "field1") == [1]
    time.sleep(0.11)
    assert r.hexists("redis-key", "field1") is False
    assert r.hexists("redis-key", "field2") is True


def test_hpexpireat_conditions(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1"})
    future_exp_time = testtools.current_time() + 500
    past_exp_time = testtools.current_time() - 500
    assert r.hpexpireat("redis-key", future_exp_time, "field1", xx=True) == [0]
    assert r.hpexpireat("redis-key", future_exp_time, "field1", nx=True) == [1]
    assert r.hpexpireat("redis-key", past_exp_time, "field1", gt=True) == [0]
    assert r.hpexpireat("redis-key", past_exp_time, "field1", lt=True) == [2]
    assert r.hexists("redis-key", "field1") is False


def test_hpexpireat_nonexistent_key_or_field(r: redis.Redis):
    r.delete("redis-key")
    future_exp_time = testtools.current_time() + 500
    assert r.hpexpireat("redis-key", future_exp_time, "field1") == [-2]
    r.hset("redis-key", "field1", "value1")
    assert r.hpexpireat("redis-key", future_exp_time, "nonexistent_field") == [-2]


def test_hpexpireat_multiple_fields(r: redis.Redis):
    r.delete("redis-key")
    r.hset(
        "redis-key",
        mapping={"field1": "value1", "field2": "value2", "field3": "value3"},
    )
    exp_time = testtools.current_time() + 100
    assert r.hpexpireat("redis-key", exp_time, "field1", "field2") == [1, 1]
    time.sleep(0.11)
    assert r.hexists("redis-key", "field1") is False
    assert r.hexists("redis-key", "field2") is False
    assert r.hexists("redis-key", "field3") is True


def test_hpexpireat_multiple_condition_flags_error(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1"})
    exp_time = testtools.current_time() + 500
    with pytest.raises(ValueError) as e:
        r.hpexpireat("redis-key", exp_time, "field1", nx=True, xx=True)
    assert "Only one of" in str(e)


def test_hpersist_multiple_fields(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1", "field2": "value2"})
    r.hexpire("redis-key", 5000, "field1")
    assert r.hpersist("redis-key", "field1", "field2", "field3") == [1, -1, -2]


def test_hpersist_nonexistent_key(r: redis.Redis):
    r.delete("redis-key")
    assert r.hpersist("redis-key", "field1", "field2", "field3") == [-2, -2, -2]


def test_hexpiretime_multiple_fields_mixed_conditions(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1", "field2": "value2"})
    future_time = testtools.current_time() // 1000 + 30 * 60
    r.hexpireat("redis-key", future_time, "field1")
    result = r.hexpiretime("redis-key", "field1", "field2", "field3")
    assert future_time - 10 < result[0] <= future_time
    assert result[1:] == [-1, -2]


def test_hexpiretime_nonexistent_key(r: redis.Redis):
    r.delete("redis-key")
    assert r.hexpiretime("redis-key", "field1", "field2", "field3") == [-2, -2, -2]


def test_hpexpiretime_multiple_fields_mixed_conditions(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1", "field2": "value2"})
    future_time = testtools.current_time() // 1000 + 30 * 60
    r.hexpireat("redis-key", future_time, "field1")
    result = r.hpexpiretime("redis-key", "field1", "field2", "field3")
    assert future_time * 1000 - 10000 < result[0] <= future_time * 1000
    assert result[1:] == [-1, -2]


def test_hpexpiretime_nonexistent_key(r: redis.Redis):
    r.delete("redis-key")
    assert r.hpexpiretime("redis-key", "field1", "field2", "field3") == [-2, -2, -2]


def test_httl_multiple_fields_mixed_conditions(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1", "field2": "value2"})
    future_time = testtools.current_time() // 1000 + 30 * 60
    r.hexpireat("redis-key", future_time, "field1")
    result = r.httl("redis-key", "field1", "field2", "field3")
    assert 30 * 60 - 10 < result[0] <= 30 * 60
    assert result[1:] == [-1, -2]


def test_httl_nonexistent_key(r: redis.Redis):
    r.delete("redis-key")
    assert r.httl("redis-key", "field1", "field2", "field3") == [-2, -2, -2]


def test_hpttl_multiple_fields_mixed_conditions(r: redis.Redis):
    r.delete("redis-key")
    r.hset("redis-key", mapping={"field1": "value1", "field2": "value2"})
    future_time = testtools.current_time() // 1000 + 30 * 60
    r.hexpireat("redis-key", future_time, "field1")
    result = r.hpttl("redis-key", "field1", "field2", "field3")
    assert 30 * 60000 - 10000 < result[0] <= 30 * 60000
    assert result[1:] == [-1, -2]


def test_hpttl_nonexistent_key(r: redis.Redis):
    r.delete("redis-key")
    assert r.hpttl("redis-key", "field1", "field2", "field3") == [-2, -2, -2]


def test_hincrby_with_hash_key_expiration(r: redis.Redis):
    r.hincrby("foo", "counter")
    r.hexpire("foo", 10, "counter")
    assert r.hincrby("foo", "counter") == 2
    res = r.httl("foo", "counter")
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0] >= 0


@pytest.mark.min_server("7.4")
def test_hexpire_empty_key(r: redis.Redis):
    testtools.raw_command(r, "hexpire", b"", 2055010579, "fields", 2, b"\x89U\x04", b"6\x86\xf4\xdd")


def test_hincrbyfloat_with_hash_key_expiration(r: redis.Redis):
    r.hincrbyfloat("foo", "counter", 1.0)
    r.hexpire("foo", 10, "counter")
    assert r.hincrbyfloat("foo", "counter", 2.0) == 3.0
    res = r.httl("foo", "counter")
    assert isinstance(res, list)
    assert len(res) == 1
    assert res[0] >= 0
