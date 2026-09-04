import pytest

from fakeredis._typing import ClientType
from test import testtools

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.supported_server_versions(min_redis_ver="8.7.2"),
        pytest.mark.unsupported_server_types("dragonfly", "valkey"),
    ]
)


@pytest.fixture
def zsets(r: ClientType) -> ClientType:
    r.zadd("z1", {"a": 1, "b": 2})
    r.zadd("z2", {"b": 10, "c": 20})
    r.zadd("z3", {"b": 100})
    return r


def _withscores(res) -> list:
    """Normalize a raw WITHSCORES reply to (member, score) pairs.

    `raw_command` skips redis-py's response callbacks, so RESP2 gives a flat list with the scores
    as bulk strings, while RESP3 gives [member, score] pairs with the scores already as floats.
    """
    if res and isinstance(res[0], list):
        return [(member, float(score)) for member, score in res]
    return [(res[i], float(res[i + 1])) for i in range(0, len(res), 2)]


def _pairs(res) -> list:
    """zrange WITHSCORES gives (member, score) tuples in RESP2 and [member, score] lists in RESP3."""
    return [tuple(item) for item in res]


# The commands below are issued with `raw_command` rather than the redis-py helpers, since redis-py
# only accepts AGGREGATE COUNT from 8.0.0 onwards and rejects it client-side before it reaches the
# server. Going through raw_command keeps these tests meaningful on every supported redis-py version.


def test_zunion_aggregate_count(zsets: ClientType):
    # With COUNT, the score is the number of input sets containing the member
    res = testtools.raw_command(zsets, "ZUNION", 3, "z1", "z2", "z3", "AGGREGATE", "COUNT", "WITHSCORES")
    assert _withscores(res) == [(b"a", 1.0), (b"c", 1.0), (b"b", 3.0)]


def test_zunion_aggregate_count_with_weights(zsets: ClientType):
    # With COUNT, each set contributes its weight for members it contains
    res = testtools.raw_command(
        zsets, "ZUNION", 3, "z1", "z2", "z3", "WEIGHTS", 2, 3, 4, "AGGREGATE", "COUNT", "WITHSCORES"
    )
    assert _withscores(res) == [(b"a", 2.0), (b"c", 3.0), (b"b", 9.0)]


def test_zinter_aggregate_count(zsets: ClientType):
    res = testtools.raw_command(zsets, "ZINTER", 2, "z1", "z2", "AGGREGATE", "COUNT", "WITHSCORES")
    assert _withscores(res) == [(b"b", 2.0)]


def test_zunionstore_aggregate_count(zsets: ClientType):
    assert testtools.raw_command(zsets, "ZUNIONSTORE", "dest", 3, "z1", "z2", "z3", "AGGREGATE", "COUNT") == 3
    assert _pairs(zsets.zrange("dest", 0, -1, withscores=True)) == [(b"a", 1.0), (b"c", 1.0), (b"b", 3.0)]


def test_zinterstore_aggregate_count_with_weights(zsets: ClientType):
    res = testtools.raw_command(zsets, "ZINTERSTORE", "dest", 2, "z1", "z2", "WEIGHTS", 5, 7, "AGGREGATE", "COUNT")
    assert res == 1
    assert _pairs(zsets.zrange("dest", 0, -1, withscores=True)) == [(b"b", 12.0)]


def test_zunion_aggregate_count_lowercase(zsets: ClientType):
    res = testtools.raw_command(zsets, "ZUNION", 2, "z1", "z2", "AGGREGATE", "count", "WITHSCORES")
    assert _withscores(res) == [(b"a", 1.0), (b"c", 1.0), (b"b", 2.0)]


@testtools.run_test_if_redispy_ver("gte", "8.0.0")
def test_zunion_aggregate_count_redispy_client(zsets: ClientType):
    """redis-py only allows AGGREGATE COUNT through its zunion/zinter helpers from 8.0.0."""
    assert _pairs(zsets.zunion(["z1", "z2", "z3"], aggregate="COUNT", withscores=True)) == [
        (b"a", 1.0),
        (b"c", 1.0),
        (b"b", 3.0),
    ]
    assert _pairs(zsets.zinter(["z1", "z2"], aggregate="COUNT", withscores=True)) == [(b"b", 2.0)]
    assert zsets.zunionstore("dest", ["z1", "z2", "z3"], aggregate="COUNT") == 3
