from typing import Tuple, List, Dict

import pytest
import redis
import redis.client
from packaging.version import Version

from test import testtools
from test.testtools import raw_command, resp_conversion, tuple_to_list

REDIS_VERSION = Version(redis.__version__)


def test_zadd_roman(r: redis.Redis):
    testtools.raw_command(r, "ZADD", "b", "0", "c")
    with pytest.raises(redis.ResponseError) as ctx:
        testtools.raw_command(r, "SORT", "b")

    assert str(ctx.value) == "One or more scores can't be converted into double"


def test_zadd(r: redis.Redis):
    r.zadd("foo", {"four": 4})
    r.zadd("foo", {"three": 3})
    assert r.zadd("foo", {"two": 2, "one": 1, "zero": 0}) == 3
    assert r.zrange("foo", 0, -1) == [b"zero", b"one", b"two", b"three", b"four"]
    assert r.zadd("foo", {"zero": 7, "one": 1, "five": 5}) == 1
    assert r.zrange("foo", 0, -1) == [b"one", b"two", b"three", b"four", b"five", b"zero"]


def test_zadd_empty(r: redis.Redis):
    # Have to add at least one key/value pair
    with pytest.raises(redis.RedisError):
        r.zadd("foo", {})


@pytest.mark.min_server("7")
def test_zadd_minus_zero_redis7(r: redis.Redis):
    r.zadd("foo", {"a": -0.0})
    r.zadd("foo", {"a": 0.0})
    assert raw_command(r, "zscore", "foo", "a") == resp_conversion(r, 0.0, b"0")


def test_zadd_wrong_type(r: redis.Redis):
    r.sadd("foo", "bar")
    with pytest.raises(redis.ResponseError):
        r.zadd("foo", {"two": 2})


def test_zadd_multiple(r: redis.Redis):
    r.zadd("foo", {"one": 1, "two": 2})
    assert r.zrange("foo", 0, 0) == [b"one"]
    assert r.zrange("foo", 1, 1) == [b"two"]


@pytest.mark.parametrize(
    ["map_to_add", "expected_ret", "expected_zrange_state"],
    [
        ({"four": 2.0, "three": 1.0}, 0, [(b"three", 3.0), (b"four", 4.0)]),
        ({"four": 2.0, "three": 1.0, "zero": 0.0}, 1, [(b"zero", 0.0), (b"three", 3.0), (b"four", 4.0)]),
        ({"two": 2.0, "one": 1.0}, 2, [(b"one", 1.0), (b"two", 2.0), (b"three", 3.0), (b"four", 4.0)]),
    ],
    ids=["no_additions", "partial_additions", "new_additions"],
)
@pytest.mark.parametrize("ch", [False, True])
def test_zadd_with_nx(
    r: redis.Redis,
    map_to_add: Dict[str, float],
    expected_ret: int,
    expected_zrange_state: List[Tuple[bytes, float]],
    ch: bool,
):
    r.zadd("foo", {"four": 4.0, "three": 3.0})
    assert r.zadd("foo", map_to_add, nx=True, ch=ch) == expected_ret
    assert r.zrange("foo", 0, -1, withscores=True) == resp_conversion(
        r, tuple_to_list(expected_zrange_state), expected_zrange_state
    )


@pytest.mark.parametrize(
    ["map_to_add", "expected_ret", "expected_zrange_state"],
    [
        ({"four": 2.0, "three": 1.0}, 0, [(b"three", 3.0), (b"four", 4.0)]),
        (
            {"four": 5.0, "three": 1.0, "zero": 0.0},
            2,
            [
                (b"zero", 0.0),
                (b"three", 3.0),
                (b"four", 5.0),
            ],
        ),
        ({"two": 2.0, "one": 1.0}, 2, [(b"one", 1.0), (b"two", 2.0), (b"three", 3.0), (b"four", 4.0)]),
    ],
    ids=["no_additions", "partial_additions", "new_additions"],
)
def test_zadd_with_gt_and_ch(
    r: redis.Redis, map_to_add: Dict[str, float], expected_ret: int, expected_zrange_state: List[Tuple[bytes, float]]
):
    r.zadd("foo", {"four": 4.0, "three": 3.0})
    assert r.zadd("foo", map_to_add, gt=True, ch=True) == expected_ret
    assert r.zrange("foo", 0, -1, withscores=True) == resp_conversion(
        r, tuple_to_list(expected_zrange_state), expected_zrange_state
    )


@pytest.mark.parametrize(
    ["map_to_add", "expected_ret", "expected_zrange_state"],
    [
        ({"four": 2.0, "three": 1.0}, 0, [(b"three", 3.0), (b"four", 4.0)]),
        ({"four": 5.0, "three": 1.0, "zero": 0.0}, 1, [(b"zero", 0.0), (b"three", 3.0), (b"four", 5.0)]),
        ({"two": 2.0, "one": 1.0}, 2, [(b"one", 1.0), (b"two", 2.0), (b"three", 3.0), (b"four", 4.0)]),
    ],
    ids=["no_additions", "partial_additions", "new_additions"],
)
def test_zadd_with_gt(
    r: redis.Redis, map_to_add: Dict[str, float], expected_ret: int, expected_zrange_state: List[Tuple[bytes, float]]
):
    r.zadd("foo", {"four": 4.0, "three": 3.0})
    assert r.zadd("foo", map_to_add, gt=True) == expected_ret
    assert r.zrange("foo", 0, -1, withscores=True) == resp_conversion(
        r, tuple_to_list(expected_zrange_state), expected_zrange_state
    )


@pytest.mark.parametrize(
    ["map_to_add", "expected_ret", "expected_zrange_state"],
    [
        ({"four": 4.0, "three": 1.0}, 1, [(b"three", 1.0), (b"four", 4.0)]),
        ({"four": 4.0, "three": 1.0, "zero": 0.0}, 2, [(b"zero", 0.0), (b"three", 1.0), (b"four", 4.0)]),
        ({"two": 2.0, "one": 1.0}, 2, [(b"one", 1.0), (b"two", 2.0), (b"three", 3.0), (b"four", 4.0)]),
    ],
    ids=["no_additions", "partial_additions", "new_additions"],
)
def test_zadd_with_ch(
    r: redis.Redis, map_to_add: Dict[str, float], expected_ret: int, expected_zrange_state: List[Tuple[bytes, float]]
):
    r.zadd("foo", {"four": 4.0, "three": 3.0})
    assert r.zadd("foo", map_to_add, ch=True) == expected_ret
    assert r.zrange("foo", 0, -1, withscores=True) == resp_conversion(
        r, tuple_to_list(expected_zrange_state), expected_zrange_state
    )


@pytest.mark.parametrize(
    ["map_to_add", "expected_ret", "expected_zrange_state"],
    [
        ({"four": 2.0, "three": 1.0}, 2, [(b"three", 1.0), (b"four", 2.0)]),
        ({"four": 4.0, "three": 3.0, "zero": 0.0}, 0, [(b"three", 3.0), (b"four", 4.0)]),
        ({"two": 2.0, "one": 1.0}, 0, [(b"three", 3.0), (b"four", 4.0)]),
    ],
    ids=["new_additions", "no_additions", "no_additions_2"],
)
@pytest.mark.parametrize("ch", [False, True])
def test_zadd_with_xx(
    r: redis.Redis,
    map_to_add: Dict[str, float],
    expected_ret: int,
    expected_zrange_state: List[Tuple[bytes, float]],
    ch: bool,
):
    r.zadd("foo", {"four": 4.0, "three": 3.0})
    assert r.zadd("foo", map_to_add, xx=True, ch=ch) == (expected_ret if ch else 0)
    assert r.zrange("foo", 0, -1, withscores=True) == resp_conversion(
        r, tuple_to_list(expected_zrange_state), expected_zrange_state
    )


@pytest.mark.parametrize("ch", [False, True])
def test_zadd_with_nx_and_xx(r: redis.Redis, ch: bool):
    r.zadd("foo", {"four": 4.0, "three": 3.0})
    with pytest.raises(redis.DataError):
        r.zadd("foo", {"four": -4.0, "three": -3.0}, nx=True, xx=True, ch=ch)


@pytest.mark.parametrize("ch", [False, True])
def test_zadd_incr(r: redis.Redis, ch: bool):
    r.zadd("foo", {"four": 4.0, "three": 3.0})
    assert r.zadd("foo", {"four": 1.0}, incr=True, ch=ch) == 5.0
    assert r.zadd("foo", {"three": 1.0}, incr=True, nx=True, ch=ch) is None
    assert r.zscore("foo", "three") == 3.0
    assert r.zadd("foo", {"bar": 1.0}, incr=True, xx=True, ch=ch) is None
    assert r.zadd("foo", {"three": 1.0}, incr=True, xx=True, ch=ch) == 4.0


def test_zadd_with_xx_and_gt_and_ch(r: redis.Redis):
    r.zadd("test", {"one": 1})
    assert r.zscore("test", "one") == 1.0
    assert r.zadd("test", {"one": 4}, xx=True, gt=True, ch=True) == 1
    assert r.zscore("test", "one") == 4.0
    assert r.zadd("test", {"one": 0}, xx=True, gt=True, ch=True) == 0
    assert r.zscore("test", "one") == 4.0


def test_zadd_and_zrangebyscore(r: redis.Redis):
    raw_command(r, "zadd", "", 0.0, "")
    assert raw_command(r, "zrangebyscore", "", 0.0, 0.0, "limit", 0, 0) == []
    with pytest.raises(redis.RedisError):
        raw_command(r, "zrangebyscore", "", 0.0, 0.0, "limit", 0)
    with pytest.raises(redis.RedisError):
        raw_command(r, "zadd", "t", 0.0, "xx", "")
