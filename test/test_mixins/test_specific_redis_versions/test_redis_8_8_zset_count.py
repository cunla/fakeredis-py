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


def _pairs(res) -> list:
    """WITHSCORES results are (member, score) tuples in RESP2 and [member, score] lists in RESP3."""
    return [tuple(item) for item in res]


def test_zunion_aggregate_count(zsets: ClientType):
    # With COUNT, the score is the number of input sets containing the member
    res = zsets.zunion(["z1", "z2", "z3"], aggregate="COUNT", withscores=True)
    assert _pairs(res) == [(b"a", 1.0), (b"c", 1.0), (b"b", 3.0)]


def test_zunion_aggregate_count_with_weights(zsets: ClientType):
    # With COUNT, each set contributes its weight for members it contains
    res = testtools.raw_command(
        zsets, "ZUNION", 3, "z1", "z2", "z3", "WEIGHTS", 2, 3, 4, "AGGREGATE", "COUNT", "WITHSCORES"
    )
    flat_resp2 = [b"a", b"2", b"c", b"3", b"b", b"9"]
    pairs_resp3 = [[b"a", 2.0], [b"c", 3.0], [b"b", 9.0]]
    assert res in (flat_resp2, pairs_resp3)


def test_zinter_aggregate_count(zsets: ClientType):
    res = zsets.zinter(["z1", "z2"], aggregate="COUNT", withscores=True)
    assert _pairs(res) == [(b"b", 2.0)]


def test_zunionstore_aggregate_count(zsets: ClientType):
    assert zsets.zunionstore("dest", ["z1", "z2", "z3"], aggregate="COUNT") == 3
    assert _pairs(zsets.zrange("dest", 0, -1, withscores=True)) == [(b"a", 1.0), (b"c", 1.0), (b"b", 3.0)]


def test_zinterstore_aggregate_count_with_weights(zsets: ClientType):
    res = testtools.raw_command(zsets, "ZINTERSTORE", "dest", 2, "z1", "z2", "WEIGHTS", 5, 7, "AGGREGATE", "COUNT")
    assert res == 1
    assert _pairs(zsets.zrange("dest", 0, -1, withscores=True)) == [(b"b", 12.0)]
