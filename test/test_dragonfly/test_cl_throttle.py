from __future__ import annotations

from time import sleep

import pytest
import redis

from fakeredis._typing import ClientType
from test import testtools

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("redis", "valkey", "kividb"),
    ]
)


def assert_throttle(actual: list[int], expected: list[int]) -> None:
    """Compare a CL.THROTTLE reply, allowing the two time fields to lag by up to a second.

    `retry_after`/`reset_after` are derived from the time actually elapsed since the key was
    written, so they drop by one as soon as the previous commands took more than a millisecond.
    """
    assert actual[:3] == expected[:3]
    for i in (3, 4):
        if expected[i] <= 0:
            assert actual[i] == expected[i]
        else:
            assert expected[i] - 1 <= actual[i] <= expected[i]


def test_cl_throttle(r: ClientType):
    limit, max_burst, count, period = 5, 4, 1, 10

    # You can never make a request larger than the maximum.
    res = testtools.raw_command(r, "cl.throttle", "foo", max_burst, count, period, 6)
    assert_throttle(res, [1, limit, 5, -1, 0])

    # Rate limit normal requests appropriately.
    for remaining in range(4, -1, -1):
        res = testtools.raw_command(r, "cl.throttle", "foo", max_burst, count, period)
        assert_throttle(res, [0, limit, remaining, -1, 10 * (limit - remaining) + 1])

    res = testtools.raw_command(r, "cl.throttle", "foo", max_burst, count, period)
    assert_throttle(res, [1, limit, 0, 11, 51])

    # A zero-volume request just peeks at the state.
    res = testtools.raw_command(r, "cl.throttle", "foo", max_burst, count, period, 0)
    assert_throttle(res, [0, limit, 0, -1, 51])


def test_cl_throttle_quantity(r: ClientType):
    limit, max_burst, count, period = 5, 4, 1, 10

    # A high-volume request uses up more of the limit.
    res = testtools.raw_command(r, "cl.throttle", "foo", max_burst, count, period, 2)
    assert_throttle(res, [0, limit, 3, -1, 21])

    # Large requests cannot exceed limits.
    res = testtools.raw_command(r, "cl.throttle", "foo", max_burst, count, period, 5)
    assert_throttle(res, [1, limit, 3, 21, 21])


def test_cl_throttle_sub_millisecond_emission_interval(r: ClientType):
    # emission interval = 2000 nanoseconds, cost = 2 units
    res = testtools.raw_command(r, "cl.throttle", "foo", 4, 500000, 1, 2)
    assert_throttle(res, [0, 5, 3, -1, 1])


@pytest.mark.slow
def test_cl_throttle_recovers_over_time(r: ClientType):
    limit, max_burst, count, period = 2, 1, 2, 1  # 2 tokens per second, emission interval 500ms

    assert_throttle(testtools.raw_command(r, "cl.throttle", "foo", max_burst, count, period), [0, limit, 1, -1, 1])
    assert_throttle(testtools.raw_command(r, "cl.throttle", "foo", max_burst, count, period), [0, limit, 0, -1, 2])
    assert_throttle(testtools.raw_command(r, "cl.throttle", "foo", max_burst, count, period), [1, limit, 0, 1, 2])

    sleep(1.1)
    # The whole bucket has drained, so the request is allowed again.
    assert_throttle(testtools.raw_command(r, "cl.throttle", "foo", max_burst, count, period), [0, limit, 1, -1, 1])


@pytest.mark.slow
def test_cl_throttle_stores_expiring_key(r: ClientType):
    testtools.raw_command(r, "cl.throttle", "foo", 0, 1, 1)
    # The key holds the theoretical arrival time of the next conforming request, in nanoseconds.
    assert int(r.get("foo")) > 0
    assert r.pttl("foo") > 0

    sleep(1.1)
    assert r.get("foo") is None


def test_cl_throttle_wrong_type(r: ClientType):
    r.rpush("foo", "bar")
    with pytest.raises(redis.ResponseError, match="WRONGTYPE"):
        testtools.raw_command(r, "cl.throttle", "foo", 1, 1, 1)

    r.set("bar", "not-an-integer")
    with pytest.raises(redis.ResponseError, match="value is not an integer or out of range"):
        testtools.raw_command(r, "cl.throttle", "bar", 1, 1, 1)


def test_cl_throttle_zero_rates(r: ClientType):
    with pytest.raises(redis.ResponseError, match="zero rates are not supported"):
        testtools.raw_command(r, "cl.throttle", "foo", 10, 1, 0)


@pytest.mark.parametrize(
    "args",
    [
        (10, 0, 1),  # count == 0
        (-1, 1, 1),  # negative max_burst
        (10, -1, 1),  # negative count
        (10, 1, -1),  # negative period
        (10, 1, 1, -1),  # negative quantity
        (10, 1, "one"),  # not a number
    ],
)
def test_cl_throttle_invalid_args(r: ClientType, args: tuple):
    with pytest.raises(redis.ResponseError, match="value is not an integer or out of range"):
        testtools.raw_command(r, "cl.throttle", "foo", *args)


def test_cl_throttle_wrong_number_of_args(r: ClientType):
    with pytest.raises(redis.ResponseError, match="wrong number of arguments"):
        testtools.raw_command(r, "cl.throttle", "foo", 1, 1)
