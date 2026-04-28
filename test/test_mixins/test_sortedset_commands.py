from __future__ import annotations

from collections import OrderedDict
from typing import Tuple, List, Optional

import math
import pytest
import redis
import redis.client
import valkey
from packaging.version import Version

from fakeredis._typing import ClientType
from test import testtools
from test.testtools import resp_conversion, resp_conversion_from_resp2

REDIS_VERSION = Version(redis.__version__)


def round_str(x):
    # assert isinstance(x, bytes)
    return round(float(x))


def zincrby(r, key, amount, value):
    return r.zincrby(key, amount, value)


def test_zpopmin(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zpopmin("foo", count=2) == resp_conversion(
        r, [[b"one", 1.0], [b"two", 2.0]], [(b"one", 1.0), (b"two", 2.0)]
    )
    assert r.zpopmin("foo", count=2) == resp_conversion(r, [[b"three", 3.0]], [(b"three", 3.0)])


def test_zpopmin_too_many(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zpopmin("foo", count=5) == resp_conversion(
        r, [[b"one", 1.0], [b"two", 2.0], [b"three", 3.0]], [(b"one", 1.0), (b"two", 2.0), (b"three", 3.0)]
    )


def test_zpopmax(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zpopmax("foo", count=2) == resp_conversion(
        r, [[b"three", 3.0], [b"two", 2.0]], [(b"three", 3.0), (b"two", 2.0)]
    )
    assert r.zpopmax("foo", count=2) == resp_conversion(r, [[b"one", 1.0]], [(b"one", 1.0)])


def test_zrange_same_score(r: ClientType):
    r.zadd("foo", {"two_a": 2})
    r.zadd("foo", {"two_b": 2})
    r.zadd("foo", {"two_c": 2})
    r.zadd("foo", {"two_d": 2})
    r.zadd("foo", {"two_e": 2})
    assert r.zrange("foo", 2, 3) == [b"two_c", b"two_d"]


def test_zrange_with_bylex_and_byscore(r: ClientType):
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"three_a": 0})
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "zrange", "foo", "(t", "+", "bylex", "byscore")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zrange_with_rev_and_bylex(r: ClientType):
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"three_a": 0})
    assert r.zrange("foo", b"+", b"(t", desc=True, bylex=True) == [b"two_b", b"two_a", b"three_a"]
    assert r.zrange("foo", b"[two_b", b"(t", desc=True, bylex=True) == [b"two_b", b"two_a", b"three_a"]
    assert r.zrange("foo", b"(two_b", b"(t", desc=True, bylex=True) == [b"two_a", b"three_a"]
    assert r.zrange("foo", b"[two_b", b"[three_a", desc=True, bylex=True) == [b"two_b", b"two_a", b"three_a"]
    assert r.zrange("foo", b"[two_b", b"(three_a", desc=True, bylex=True) == [b"two_b", b"two_a"]
    assert r.zrange("foo", b"(two_b", b"-", desc=True, bylex=True) == [b"two_a", b"three_a", b"one_a"]
    assert r.zrange("foo", b"(two_b", b"[two_b", bylex=True) == []
    # reversed max + and min - boundaries
    # these will be always empty, but allowed by redis
    assert r.zrange("foo", b"-", b"+", desc=True, bylex=True) == []
    assert r.zrange("foo", b"[three_a", b"+", desc=True, bylex=True) == []
    assert r.zrange("foo", b"-", b"[o", desc=True, bylex=True) == []


def test_zrange_with_bylex(r: ClientType):
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"three_a": 0})
    assert r.zrange("foo", b"(t", b"+", bylex=True) == [b"three_a", b"two_a", b"two_b"]
    assert r.zrange("foo", b"(t", b"[two_b", bylex=True) == [b"three_a", b"two_a", b"two_b"]
    assert r.zrange("foo", b"(t", b"(two_b", bylex=True) == [b"three_a", b"two_a"]
    assert r.zrange("foo", b"[three_a", b"[two_b", bylex=True) == [b"three_a", b"two_a", b"two_b"]
    assert r.zrange("foo", b"(three_a", b"[two_b", bylex=True) == [b"two_a", b"two_b"]
    assert r.zrange("foo", b"-", b"(two_b", bylex=True) == [b"one_a", b"three_a", b"two_a"]
    assert r.zrange("foo", b"[two_b", b"(two_b", bylex=True) == []
    # reversed max + and min - boundaries
    # these will be always empty, but allowed by redis
    assert r.zrange("foo", b"+", b"-", bylex=True) == []
    assert r.zrange("foo", b"+", b"[three_a", bylex=True) == []
    assert r.zrange("foo", b"[o", b"-", bylex=True) == []


def test_zrange_with_byscore(r: ClientType):
    r.zadd("foo", {"zero": 0})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"two_a_also": 2})
    r.zadd("foo", {"two_b_also": 2})
    r.zadd("foo", {"four": 4})
    assert r.zrange("foo", 1, 3, byscore=True) == [b"two", b"two_a_also", b"two_b_also"]
    assert r.zrange("foo", 2, 3, byscore=True) == [b"two", b"two_a_also", b"two_b_also"]
    assert r.zrange("foo", 0, 4, byscore=True) == [b"zero", b"two", b"two_a_also", b"two_b_also", b"four"]
    assert r.zrange("foo", "-inf", 1, byscore=True) == [b"zero"]
    assert r.zrange("foo", 2, "+inf", byscore=True) == [b"two", b"two_a_also", b"two_b_also", b"four"]
    assert r.zrange("foo", "-inf", "+inf", byscore=True) == [b"zero", b"two", b"two_a_also", b"two_b_also", b"four"]


def test_zcard(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    assert r.zcard("foo") == 2


def test_zcard_non_existent_key(r: ClientType):
    assert r.zcard("foo") == 0


def test_zcard_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zcard("foo")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zcount(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"three": 2})
    r.zadd("foo", {"five": 5})
    assert r.zcount("foo", 2, 4) == 1
    assert r.zcount("foo", 1, 4) == 2
    assert r.zcount("foo", 0, 5) == 3
    assert r.zcount("foo", 4, "+inf") == 1
    assert r.zcount("foo", "-inf", 4) == 2
    assert r.zcount("foo", "-inf", "+inf") == 3


def test_zcount_exclusive(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"three": 2})
    r.zadd("foo", {"five": 5})
    assert r.zcount("foo", "-inf", "(2") == 1
    assert r.zcount("foo", "-inf", 2) == 2
    assert r.zcount("foo", "(5", "+inf") == 0
    assert r.zcount("foo", "(1", 5) == 2
    assert r.zcount("foo", "(2", "(5") == 0
    assert r.zcount("foo", "(1", "(5") == 1
    assert r.zcount("foo", 2, "(5") == 1


def test_zcount_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zcount("foo", "-inf", "+inf")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zincrby(r: ClientType):
    r.zadd("foo", {"one": 1})
    assert zincrby(r, "foo", 10, "one") == 11
    assert r.zrange("foo", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"one", 11)])


def test_zincrby_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        zincrby(r, "foo", 10, "one")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zrange_descending(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrange("foo", 0, -1, desc=True) == [b"three", b"two", b"one"]


def test_zrange_descending_with_scores(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrange("foo", 0, -1, desc=True, withscores=True) == resp_conversion(
        r, [[b"three", 3.0], [b"two", 2.0], [b"one", 1.0]], [(b"three", 3), (b"two", 2), (b"one", 1)]
    )
    # comment


def test_zrange_with_positive_indices(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrange("foo", 0, 1) == [b"one", b"two"]


def test_zrange_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zrange("foo", 0, -1)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.resp2_only
def test_zrange_score_cast(r: ClientType):
    r.zadd("foo", {"one": 1.2})
    r.zadd("foo", {"two": 2.2})

    assert r.zrange("foo", 0, 2, withscores=True) == resp_conversion_from_resp2(r, [(b"one", 1.2), (b"two", 2.2)])
    assert r.zrange("foo", 0, 2, withscores=True, score_cast_func=round_str) == resp_conversion_from_resp2(
        r, [(b"one", 1.0), (b"two", 2.0)]
    )


def test_zrank(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrank("foo", "one") == 0
    assert r.zrank("foo", "two") == 1
    assert r.zrank("foo", "three") == 2


@pytest.mark.supported_redis_versions(min_ver="7.2")
@pytest.mark.unsupported_server_types("dragonfly", "valkey")
@testtools.run_test_if_redispy_ver("gt", "4.6")
def test_zrank_redis7_2(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrank("foo", "one") == 0
    assert r.zrank("foo", "two") == 1
    assert r.zrank("foo", "three") == 2
    assert r.zrank("foo", "one", withscore=True) == [0, 1.0]
    assert r.zrank("foo", "two", withscore=True) == [1, 2.0]


def test_zrank_non_existent_member(r: ClientType):
    assert r.zrank("foo", "one") is None


def test_zrank_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zrank("foo", "one")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zrem(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    r.zadd("foo", {"four": 4})
    assert r.zrem("foo", "one") == 1
    assert r.zrange("foo", 0, -1) == [b"two", b"three", b"four"]
    # Since redis>=2.7.6 returns number of deleted items.
    assert r.zrem("foo", "two", "three") == 2
    assert r.zrange("foo", 0, -1) == [b"four"]
    assert r.zrem("foo", "three", "four") == 1
    assert r.zrange("foo", 0, -1) == []
    assert r.zrem("foo", "three", "four") == 0


def test_zrem_non_existent_member(r: ClientType):
    assert not r.zrem("foo", "one")


def test_zrem_numeric_member(r: ClientType):
    r.zadd("foo", {"128": 13.0, "129": 12.0})
    assert r.zrem("foo", 128) == 1
    assert r.zrange("foo", 0, -1) == [b"129"]


def test_zrem_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zrem("foo", "bar")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zscore(r: ClientType):
    r.zadd("foo", {"one": 54})
    assert r.zscore("foo", "one") == 54


def test_zscore_non_existent_member(r: ClientType):
    assert r.zscore("foo", "one") is None


def test_zscore_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zscore("foo", "one")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zmscore(r: ClientType):
    """When all the requested sorted-set members are in the cache, a valid float value should be returned for each
    requested member.

    The order of the returned scores should always match the order in which the set members were supplied.
    """
    cache_key: str = "scored-set-members"
    members: Tuple[str, ...] = ("one", "two", "three", "four", "five", "six")
    scores: Tuple[float, ...] = (1.1, 2.2, 3.3, 4.4, 5.5, 6.6)

    r.zadd(cache_key, dict(zip(members, scores)))
    cached_scores: List[Optional[float]] = r.zmscore(
        cache_key,
        list(members),
    )

    assert all(cached_scores[idx] == score for idx, score in enumerate(scores))


def test_zmscore_missing_members(r: ClientType):
    """When none of the requested sorted-set members are in the cache, a value
    of `None` should be returned once for each requested member."""
    cache_key: str = "scored-set-members"
    members: Tuple[str, ...] = ("one", "two", "three", "four", "five", "six")

    r.zadd(cache_key, {"eight": 8.8})
    cached_scores: List[Optional[float]] = r.zmscore(
        cache_key,
        list(members),
    )

    assert all(score is None for score in cached_scores)


def test_zmscore_mixed_membership(r: ClientType):
    """When only some requested sorted-set members are in the cache, a
    valid float value should be returned for each present member and `None` for
    each missing member.

    The order of the returned scores should always match the order in
    which the set members were supplied.
    """
    cache_key: str = "scored-set-members"
    members: Tuple[str, ...] = ("one", "two", "three", "four", "five", "six")
    scores: Tuple[float, ...] = (1.1, 2.2, 3.3, 4.4, 5.5, 6.6)

    r.zadd(
        cache_key,
        {member: scores[idx] for (idx, member) in enumerate(members) if idx % 2 != 0},
    )

    cached_scores: List[Optional[float]] = r.zmscore(cache_key, list(members))

    assert all(cached_scores[idx] is None for (idx, score) in enumerate(scores) if idx % 2 == 0)
    assert all(cached_scores[idx] == score for (idx, score) in enumerate(scores) if idx % 2 != 0)


def test_zrevrank(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrevrank("foo", "one") == 2
    assert r.zrevrank("foo", "two") == 1
    assert r.zrevrank("foo", "three") == 0


@pytest.mark.supported_redis_versions(min_ver="7.2")
@pytest.mark.unsupported_server_types("dragonfly", "valkey")
@testtools.run_test_if_redispy_ver("gt", "4.6")
def test_zrevrank_redis7_2(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrevrank("foo", "one") == 2
    assert r.zrevrank("foo", "two") == 1
    assert r.zrevrank("foo", "three") == 0
    assert r.zrevrank("foo", "one", withscore=True) == [2, 1.0]
    assert r.zrevrank("foo", "two", withscore=True) == [1, 2.0]


def test_zrevrank_non_existent_member(r: ClientType):
    assert r.zrevrank("foo", "one") is None


def test_zrevrank_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zrevrank("foo", "one")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zrevrange(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrevrange("foo", 0, 1) == [b"three", b"two"]
    assert r.zrevrange("foo", 0, -1) == [b"three", b"two", b"one"]


def test_zrevrange_sorted_keys(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"two_b": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrevrange("foo", 0, 2) == [b"three", b"two_b", b"two"]
    assert r.zrevrange("foo", 0, -1) == [b"three", b"two_b", b"two", b"one"]


def test_zrevrange_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zrevrange("foo", 0, 2)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.resp2_only
def test_zrevrange_score_cast(r: ClientType):
    r.zadd("foo", {"one": 1.2})
    r.zadd("foo", {"two": 2.2})

    assert r.zrevrange("foo", 0, 2, withscores=True) == resp_conversion_from_resp2(r, [(b"two", 2.2), (b"one", 1.2)])
    assert r.zrevrange("foo", 0, 2, withscores=True, score_cast_func=round_str) == resp_conversion_from_resp2(
        r, [(b"two", 2.0), (b"one", 1.0)]
    )


def test_zrange_with_large_int(r: ClientType):
    with pytest.raises(Exception, match="value is not an integer or out of range") as ctx:
        r.zrange("", 0, 9223372036854775808)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception, match="value is not an integer or out of range") as ctx:
        r.zrange("", 0, -9223372036854775809)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zrangebyscore(r: ClientType):
    r.zadd("foo", {"zero": 0})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"two_a_also": 2})
    r.zadd("foo", {"two_b_also": 2})
    r.zadd("foo", {"four": 4})
    assert r.zrangebyscore("foo", 1, 3) == [b"two", b"two_a_also", b"two_b_also"]
    assert r.zrangebyscore("foo", 2, 3) == [b"two", b"two_a_also", b"two_b_also"]
    assert r.zrangebyscore("foo", 0, 4) == [b"zero", b"two", b"two_a_also", b"two_b_also", b"four"]
    assert r.zrangebyscore("foo", "-inf", 1) == [b"zero"]
    assert r.zrangebyscore("foo", 2, "+inf") == [b"two", b"two_a_also", b"two_b_also", b"four"]
    assert r.zrangebyscore("foo", "-inf", "+inf") == [b"zero", b"two", b"two_a_also", b"two_b_also", b"four"]
    assert r.zrangebyscore("foo", "-inf", "+inf", start=-1, num=3) == []
    assert r.zrangebyscore("foo", "-inf", "+inf", start=0, num=2) == [b"zero", b"two"]


def test_zrangebysore_exclusive(r: ClientType):
    r.zadd("foo", {"zero": 0})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"four": 4})
    r.zadd("foo", {"five": 5})
    assert r.zrangebyscore("foo", "(0", 6) == [b"two", b"four", b"five"]
    assert r.zrangebyscore("foo", "(2", "(5") == [b"four"]
    assert r.zrangebyscore("foo", 0, "(4") == [b"zero", b"two"]
    assert r.zrangebyscore("foo", 0.0, 4, start=-1, num=2) == []


def test_zrangebyscore_raises_error(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    with pytest.raises(Exception) as ctx:
        r.zrangebyscore("foo", "one", 2)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrangebyscore("foo", 2, "three")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrangebyscore("foo", 2, "3)")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrangebyscore("foo", 2, "3)", 0, None)

    assert isinstance(ctx.value, (redis.RedisError, valkey.ValkeyError))


def test_zrangebyscore_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zrangebyscore("foo", "(1", "(2")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zrangebyscore_slice(r: ClientType):
    r.zadd("foo", {"two_a": 2})
    r.zadd("foo", {"two_b": 2})
    r.zadd("foo", {"two_c": 2})
    r.zadd("foo", {"two_d": 2})
    assert r.zrangebyscore("foo", 0, 4, 0, 2) == [b"two_a", b"two_b"]
    assert r.zrangebyscore("foo", 0, 4, 1, 3) == [b"two_b", b"two_c", b"two_d"]


def test_zrangebyscore_withscores(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrangebyscore("foo", 1, 3, 0, 2, True) == resp_conversion(
        r, [[b"one", 1], [b"two", 2]], [(b"one", 1), (b"two", 2)]
    )


@pytest.mark.resp2_only
def test_zrangebyscore_cast_scores(r: ClientType):
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"two_a_also": 2.2})

    expected_without_cast_round = sorted([(b"two", 2.0), (b"two_a_also", 2.2)])
    expected_with_cast_round = sorted([(b"two", 2.0), (b"two_a_also", 2.0)])
    assert sorted(r.zrangebyscore("foo", 2, 3, withscores=True)) == resp_conversion_from_resp2(
        r, expected_without_cast_round
    )
    assert sorted(
        r.zrangebyscore("foo", 2, 3, withscores=True, score_cast_func=round_str)
    ) == resp_conversion_from_resp2(r, expected_with_cast_round)


def test_zrevrangebyscore(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrevrangebyscore("foo", 3, 1) == [b"three", b"two", b"one"]
    assert r.zrevrangebyscore("foo", 3, 2) == [b"three", b"two"]
    assert r.zrevrangebyscore("foo", 3, 1, 0, 1) == [b"three"]
    assert r.zrevrangebyscore("foo", 3, 1, 1, 2) == [b"two", b"one"]


def test_zrevrangebyscore_exclusive(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zrevrangebyscore("foo", "(3", 1) == [b"two", b"one"]
    assert r.zrevrangebyscore("foo", 3, "(2") == [b"three"]
    assert r.zrevrangebyscore("foo", "(3", "(1") == [b"two"]
    assert r.zrevrangebyscore("foo", "(2", 1, 0, 1) == [b"one"]
    assert r.zrevrangebyscore("foo", "(2", "(1", 0, 1) == []
    assert r.zrevrangebyscore("foo", "(3", "(0", 1, 2) == [b"one"]


def test_zrevrangebyscore_raises_error(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    with pytest.raises(Exception) as ctx:
        r.zrevrangebyscore("foo", "three", 1)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrevrangebyscore("foo", 3, "one")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrevrangebyscore("foo", 3, "1)")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrevrangebyscore("foo", "((3", "1)")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zrevrangebyscore_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zrevrangebyscore("foo", "(3", "(1")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.resp2_only
def test_zrevrangebyscore_cast_scores(r: ClientType):
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"two_a_also": 2.2})
    assert r.zrevrangebyscore("foo", 3, 2, withscores=True) == resp_conversion_from_resp2(
        r, [(b"two_a_also", 2.2), (b"two", 2.0)]
    )
    assert r.zrevrangebyscore("foo", 3, 2, withscores=True, score_cast_func=round_str) == resp_conversion_from_resp2(
        r, [(b"two_a_also", 2.0), (b"two", 2.0)]
    )


def test_zrangebylex(r: ClientType):
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"three_a": 0})
    assert r.zrangebylex("foo", b"(t", b"+") == [b"three_a", b"two_a", b"two_b"]
    assert r.zrangebylex("foo", b"(t", b"[two_b") == [b"three_a", b"two_a", b"two_b"]
    assert r.zrangebylex("foo", b"(t", b"(two_b") == [b"three_a", b"two_a"]
    assert r.zrangebylex("foo", b"[three_a", b"[two_b") == [b"three_a", b"two_a", b"two_b"]
    assert r.zrangebylex("foo", b"(three_a", b"[two_b") == [b"two_a", b"two_b"]
    assert r.zrangebylex("foo", b"-", b"(two_b") == [b"one_a", b"three_a", b"two_a"]
    assert r.zrangebylex("foo", b"[two_b", b"(two_b") == []
    # reversed max + and min - boundaries
    # these will be always empty, but allowed by redis
    assert r.zrangebylex("foo", b"+", b"-") == []
    assert r.zrangebylex("foo", b"+", b"[three_a") == []
    assert r.zrangebylex("foo", b"[o", b"-") == []


def test_zrangebylex_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zrangebylex("foo", b"-", b"+")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zlexcount(r: ClientType):
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"three_a": 0})
    assert r.zlexcount("foo", b"(t", b"+") == 3
    assert r.zlexcount("foo", b"(t", b"[two_b") == 3
    assert r.zlexcount("foo", b"(t", b"(two_b") == 2
    assert r.zlexcount("foo", b"[three_a", b"[two_b") == 3
    assert r.zlexcount("foo", b"(three_a", b"[two_b") == 2
    assert r.zlexcount("foo", b"-", b"(two_b") == 3
    assert r.zlexcount("foo", b"[two_b", b"(two_b") == 0
    # reversed max + and min - boundaries
    # these will be always empty, but allowed by redis
    assert r.zlexcount("foo", b"+", b"-") == 0
    assert r.zlexcount("foo", b"+", b"[three_a") == 0
    assert r.zlexcount("foo", b"[o", b"-") == 0


def test_zlexcount_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zlexcount("foo", b"-", b"+")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zrangebylex_with_limit(r: ClientType):
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"three_a": 0})
    assert r.zrangebylex("foo", b"-", b"+", 1, 2) == [b"three_a", b"two_a"]

    # negative offset no results
    assert r.zrangebylex("foo", b"-", b"+", -1, 3) == []

    # negative limit ignored
    assert r.zrangebylex("foo", b"-", b"+", 0, -2) == [b"one_a", b"three_a", b"two_a", b"two_b"]
    assert r.zrangebylex("foo", b"-", b"+", 1, -2) == [b"three_a", b"two_a", b"two_b"]
    assert r.zrangebylex("foo", b"+", b"-", 1, 1) == []


def test_zrangebylex_raises_error(r: ClientType):
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"three_a": 0})

    with pytest.raises(Exception) as ctx:
        r.zrangebylex("foo", b"", b"[two_b")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrangebylex("foo", b"-", b"two_b")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrangebylex("foo", b"(t", b"two_b")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrangebylex("foo", b"t", b"+")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrangebylex("foo", b"[two_a", b"")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrangebylex("foo", b"(two_a", b"[two_b", 1)

    assert isinstance(ctx.value, (redis.RedisError, valkey.ValkeyError))


def test_zrevrangebylex(r: ClientType):
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"three_a": 0})
    assert r.zrevrangebylex("foo", b"+", b"(t") == [b"two_b", b"two_a", b"three_a"]
    assert r.zrevrangebylex("foo", b"[two_b", b"(t") == [b"two_b", b"two_a", b"three_a"]
    assert r.zrevrangebylex("foo", b"(two_b", b"(t") == [b"two_a", b"three_a"]
    assert r.zrevrangebylex("foo", b"[two_b", b"[three_a") == [b"two_b", b"two_a", b"three_a"]
    assert r.zrevrangebylex("foo", b"[two_b", b"(three_a") == [b"two_b", b"two_a"]
    assert r.zrevrangebylex("foo", b"(two_b", b"-") == [b"two_a", b"three_a", b"one_a"]
    assert r.zrangebylex("foo", b"(two_b", b"[two_b") == []
    # reversed max + and min - boundaries
    # these will be always empty, but allowed by redis
    assert r.zrevrangebylex("foo", b"-", b"+") == []
    assert r.zrevrangebylex("foo", b"[three_a", b"+") == []
    assert r.zrevrangebylex("foo", b"-", b"[o") == []


def test_zrevrangebylex_with_limit(r: ClientType):
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"three_a": 0})
    assert r.zrevrangebylex("foo", b"+", b"-", 1, 2) == [b"two_a", b"three_a"]


def test_zrevrangebylex_raises_error(r: ClientType):
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"three_a": 0})

    with pytest.raises(Exception) as ctx:
        r.zrevrangebylex("foo", b"[two_b", b"")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrevrangebylex("foo", b"two_b", b"-")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrevrangebylex("foo", b"two_b", b"(t")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrevrangebylex("foo", b"+", b"t")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrevrangebylex("foo", b"", b"[two_a")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zrevrangebylex("foo", b"[two_a", b"(two_b", 1)

    assert isinstance(ctx.value, (redis.RedisError, valkey.ValkeyError))


def test_zrevrangebylex_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zrevrangebylex("foo", b"+", b"-")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zremrangebyrank(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zremrangebyrank("foo", 0, 1) == 2
    assert r.zrange("foo", 0, -1) == [b"three"]


def test_zremrangebyrank_negative_indices(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zremrangebyrank("foo", -2, -1) == 2
    assert r.zrange("foo", 0, -1) == [b"one"]


def test_zremrangebyrank_out_of_bounds(r: ClientType):
    r.zadd("foo", {"one": 1})
    assert r.zremrangebyrank("foo", 1, 3) == 0


def test_zremrangebyrank_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zremrangebyrank("foo", 1, 3)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zremrangebyscore(r: ClientType):
    r.zadd("foo", {"zero": 0})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"four": 4})
    # Outside of range.
    assert r.zremrangebyscore("foo", 5, 10) == 0
    assert r.zrange("foo", 0, -1) == [b"zero", b"two", b"four"]
    # Middle of range.
    assert r.zremrangebyscore("foo", 1, 3) == 1
    assert r.zrange("foo", 0, -1) == [b"zero", b"four"]
    assert r.zremrangebyscore("foo", 1, 3) == 0
    # Entire range.
    assert r.zremrangebyscore("foo", 0, 4) == 2
    assert r.zrange("foo", 0, -1) == []


def test_zremrangebyscore_exclusive(r: ClientType):
    r.zadd("foo", {"zero": 0})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"four": 4})
    assert r.zremrangebyscore("foo", "(0", 1) == 0
    assert r.zrange("foo", 0, -1) == [b"zero", b"two", b"four"]
    assert r.zremrangebyscore("foo", "-inf", "(0") == 0
    assert r.zrange("foo", 0, -1) == [b"zero", b"two", b"four"]
    assert r.zremrangebyscore("foo", "(2", 5) == 1
    assert r.zrange("foo", 0, -1) == [b"zero", b"two"]
    assert r.zremrangebyscore("foo", 0, "(2") == 1
    assert r.zrange("foo", 0, -1) == [b"two"]
    assert r.zremrangebyscore("foo", "(1", "(3") == 1
    assert r.zrange("foo", 0, -1) == []


def test_zremrangebyscore_raises_error(r: ClientType):
    r.zadd("foo", {"zero": 0})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"four": 4})
    with pytest.raises(Exception) as ctx:
        r.zremrangebyscore("foo", "three", 1)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zremrangebyscore("foo", 3, "one")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zremrangebyscore("foo", 3, "1)")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zremrangebyscore("foo", "((3", "1)")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zremrangebyscore_badkey(r: ClientType):
    assert r.zremrangebyscore("foo", 0, 2) == 0


def test_zremrangebyscore_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zremrangebyscore("foo", 0, 2)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zremrangebylex(r: ClientType):
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"three_a": 0})
    assert r.zremrangebylex("foo", b"(three_a", b"[two_b") == 2
    assert r.zremrangebylex("foo", b"(three_a", b"[two_b") == 0
    assert r.zremrangebylex("foo", b"-", b"(o") == 0
    assert r.zremrangebylex("foo", b"-", b"[one_a") == 1
    assert r.zremrangebylex("foo", b"[tw", b"+") == 0
    assert r.zremrangebylex("foo", b"[t", b"+") == 1
    assert r.zremrangebylex("foo", b"[t", b"+") == 0


def test_zremrangebylex_error(r: ClientType):
    r.zadd("foo", {"two_a": 0})
    r.zadd("foo", {"two_b": 0})
    r.zadd("foo", {"one_a": 0})
    r.zadd("foo", {"three_a": 0})
    with pytest.raises(Exception) as ctx:
        r.zremrangebylex("foo", b"(t", b"two_b")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zremrangebylex("foo", b"t", b"+")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.zremrangebylex("foo", b"[two_a", b"")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zremrangebylex_badkey(r: ClientType):
    assert r.zremrangebylex("foo", b"(three_a", b"[two_b") == 0


def test_zremrangebylex_wrong_type(r: ClientType):
    r.sadd("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zremrangebylex("foo", b"bar", b"baz")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zunionstore(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("bar", {"one": 1})
    r.zadd("bar", {"two": 2})
    r.zadd("bar", {"three": 3})
    r.zunionstore("baz", ["foo", "bar"])

    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(
        r, [(b"one", 2), (b"three", 3), (b"two", 4)]
    )


def test_zunionstore_sum(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("bar", {"one": 1})
    r.zadd("bar", {"two": 2})
    r.zadd("bar", {"three": 3})
    r.zunionstore("baz", ["foo", "bar"], aggregate="SUM")
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(
        r, [(b"one", 2), (b"three", 3), (b"two", 4)]
    )


def test_zunionstore_max(r: ClientType):
    r.zadd("foo", {"one": 0})
    r.zadd("foo", {"two": 0})
    r.zadd("bar", {"one": 1})
    r.zadd("bar", {"two": 2})
    r.zadd("bar", {"three": 3})
    r.zunionstore("baz", ["foo", "bar"], aggregate="MAX")
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(
        r, [(b"one", 1), (b"two", 2), (b"three", 3)]
    )


def test_zunionstore_min(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("bar", {"one": 0})
    r.zadd("bar", {"two": 0})
    r.zadd("bar", {"three": 3})
    r.zunionstore("baz", ["foo", "bar"], aggregate="MIN")
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(
        r, [(b"one", 0), (b"two", 0), (b"three", 3)]
    )


def test_zunionstore_weights(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("bar", {"one": 1})
    r.zadd("bar", {"two": 2})
    r.zadd("bar", {"four": 4})
    r.zunionstore("baz", {"foo": 1, "bar": 2}, aggregate="SUM")
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(
        r, [(b"one", 3), (b"two", 6), (b"four", 8)]
    )


def test_zunionstore_nan_to_zero(r: ClientType):
    r.zadd("foo", {"x": math.inf})
    r.zadd("foo2", {"x": math.inf})
    r.zunionstore("bar", OrderedDict([("foo", 1.0), ("foo2", 0.0)]))
    # This is different to test_zinterstore_nan_to_zero because of a quirk
    # in redis. See https://github.com/antirez/redis/issues/3954.
    assert r.zscore("bar", "x") == math.inf


def test_zunionstore_nan_to_zero2(r: ClientType):
    r.zadd("foo", {"zero": 0})
    r.zadd("foo2", {"one": 1})
    r.zadd("foo3", {"one": 1})
    r.zunionstore("bar", {"foo": math.inf}, aggregate="SUM")
    assert r.zrange("bar", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"zero", 0)])
    r.zunionstore("bar", OrderedDict([("foo2", math.inf), ("foo3", -math.inf)]))
    assert r.zrange("bar", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"one", 0)])


def test_zunionstore_nan_to_zero_ordering(r: ClientType):
    r.zadd("foo", {"e1": math.inf})
    r.zadd("bar", {"e1": -math.inf, "e2": 0.0})
    r.zunionstore("baz", ["foo", "bar", "foo"])
    assert r.zscore("baz", "e1") == 0.0


def test_zunionstore_mixed_set_types(r: ClientType):
    # No score, redis will use 1.0.
    r.sadd("foo", "one")
    r.sadd("foo", "two")
    r.zadd("bar", {"one": 1})
    r.zadd("bar", {"two": 2})
    r.zadd("bar", {"three": 3})
    r.zunionstore("baz", ["foo", "bar"], aggregate="SUM")
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(
        r, [(b"one", 2), (b"three", 3), (b"two", 3)]
    )


def test_zunionstore_badkey(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zunionstore("baz", ["foo", "bar"], aggregate="SUM")
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"one", 1), (b"two", 2)])
    r.zunionstore("baz", {"foo": 1, "bar": 2}, aggregate="SUM")
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"one", 1), (b"two", 2)])


@pytest.mark.unsupported_server_types("dragonfly")  # TODO Should pass?
def test_zunionstore_wrong_type(r: ClientType):
    r.set("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zunionstore("baz", ["foo", "bar"])

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zinterstore(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("bar", {"one": 1})
    r.zadd("bar", {"two": 2})
    r.zadd("bar", {"three": 3})
    r.zinterstore("baz", ["foo", "bar"])
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"one", 2), (b"two", 4)])


@pytest.mark.unsupported_server_types("dragonfly")
def test_zinterstore_mixed_set_types(r: ClientType):
    r.sadd("foo", "one")
    r.sadd("foo", "two")
    r.zadd("bar", {"one": 1})
    r.zadd("bar", {"two": 2})
    r.zadd("bar", {"three": 3})
    r.zinterstore("baz", ["foo", "bar"], aggregate="SUM")
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"one", 2), (b"two", 3)])


def test_zinterstore_max(r: ClientType):
    r.zadd("foo", {"one": 0})
    r.zadd("foo", {"two": 0})
    r.zadd("bar", {"one": 1})
    r.zadd("bar", {"two": 2})
    r.zadd("bar", {"three": 3})
    r.zinterstore("baz", ["foo", "bar"], aggregate="MAX")
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"one", 1), (b"two", 2)])


def test_zinterstore_onekey(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zinterstore("baz", ["foo"], aggregate="MAX")
    assert r.zrange("baz", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"one", 1)])


def test_zinterstore_nokey(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.zinterstore("baz", [], aggregate="MAX")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.unsupported_server_types("dragonfly")  # TODO bad response
def test_zinterstore_nan_to_zero(r: ClientType):
    r.zadd("foo", {"x": math.inf})
    r.zadd("foo2", {"x": math.inf})
    r.zinterstore("bar", OrderedDict([("foo", 1.0), ("foo2", 0.0)]))
    assert r.zscore("bar", "x") == 0.0


def test_zunionstore_nokey(r: ClientType):
    with pytest.raises(Exception) as ctx:
        r.zunionstore("baz", [], aggregate="MAX")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_zinterstore_wrong_type(r: ClientType):
    r.set("foo", "bar")
    with pytest.raises(Exception) as ctx:
        r.zinterstore("baz", ["foo", "bar"])

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_empty_zset(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zrem("foo", "one")
    assert not r.exists("foo")


def test_zpopmax_too_many(r: ClientType):
    r.zadd("foo", {"one": 1})
    r.zadd("foo", {"two": 2})
    r.zadd("foo", {"three": 3})
    assert r.zpopmax("foo", count=5) == resp_conversion_from_resp2(r, [(b"three", 3.0), (b"two", 2.0), (b"one", 1.0)])


def test_bzpopmin(r: ClientType):
    r.zadd("foo", {"one": 1, "two": 2, "three": 3})
    r.zadd("bar", {"a": 1.5, "b": 2, "c": 3})
    assert r.bzpopmin(["foo", "bar"], 0) == resp_conversion_from_resp2(r, (b"foo", b"one", 1.0))
    assert r.bzpopmin(["foo", "bar"], 0) == resp_conversion_from_resp2(r, (b"foo", b"two", 2.0))
    assert r.bzpopmin(["foo", "bar"], 0) == resp_conversion_from_resp2(r, (b"foo", b"three", 3.0))
    assert r.bzpopmin(["foo", "bar"], 0) == resp_conversion_from_resp2(r, (b"bar", b"a", 1.5))


def test_bzpopmax(r: ClientType):
    r.zadd("foo", {"one": 1, "two": 2, "three": 3})
    r.zadd("bar", {"a": 1.5, "b": 2.5, "c": 3.5})
    assert r.bzpopmax(["foo", "bar"], 0) == resp_conversion(r, [b"foo", b"three", 3.0], (b"foo", b"three", 3.0))
    assert r.bzpopmax(["foo", "bar"], 0) == resp_conversion(r, [b"foo", b"two", 2.0], (b"foo", b"two", 2.0))
    assert r.bzpopmax(["foo", "bar"], 0) == resp_conversion(r, [b"foo", b"one", 1.0], (b"foo", b"one", 1.0))
    assert r.bzpopmax(["foo", "bar"], 0) == resp_conversion(r, [b"bar", b"c", 3.5], (b"bar", b"c", 3.5))


def test_zscan(r: ClientType):
    # Set up the data
    name = "zscan-test"
    for ix in range(20):
        r.zadd(name, {"key:%s" % ix: ix})
    expected = dict(r.zrange(name, 0, -1, withscores=True))

    # Test the basic version
    results = {}
    for key, val in r.zscan_iter(name, count=6):
        results[key] = val
    assert results == expected

    # Now test that the MATCH functionality works
    results = {}
    cursor = "0"
    while cursor != 0:
        cursor, data = r.zscan(name, cursor, match="*7", count=6)
        results.update(data)
    assert results == {b"key:7": 7.0, b"key:17": 17.0}


def test_zrandemember(r: ClientType):
    r.zadd("a", {"a1": 1, "a2": 2, "a3": 3, "a4": 4, "a5": 5})
    assert r.zrandmember("a") is not None
    assert len(r.zrandmember("a", 2)) == 2
    # with scores
    assert len(r.zrandmember("a", 2, withscores=True)) == resp_conversion(r, 2, 4)
    # without duplications
    assert len(r.zrandmember("a", 10)) == 5
    # with duplications
    assert len(r.zrandmember("a", -10)) == 10


def test_zdiffstore(r: ClientType):
    r.zadd("a", {"a1": 1, "a2": 2, "a3": 3})
    r.zadd("b", {"a1": 1, "a2": 2})
    assert r.zdiffstore("out", ["a", "b"])
    assert r.zrange("out", 0, -1) == [b"a3"]
    assert r.zrange("out", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"a3", 3.0)])


@pytest.mark.unsupported_server_types("dragonfly")  # TODO bad response
def test_zdiff(r: ClientType):
    r.zadd("a", {"a1": 1, "a2": 2, "a3": 3})
    r.zadd("b", {"a1": 1, "a2": 2})
    assert r.zdiff(["a", "b"]) == [b"a3"]
    assert r.zdiff(["a", "b"], withscores=True) == resp_conversion(r, [[b"a3", 3.0]], [b"a3", b"3"])


@pytest.mark.unsupported_server_types("dragonfly")  # TODO bad response
def test_zunion(r: ClientType):
    r.zadd("a", {"a1": 1, "a2": 1, "a3": 1})
    r.zadd("b", {"a1": 2, "a2": 2, "a3": 2})
    r.zadd("c", {"a1": 6, "a3": 5, "a4": 4})
    # sum
    assert r.zunion(["a", "b", "c"]) == [b"a2", b"a4", b"a3", b"a1"]

    assert r.zunion(["a", "b", "c"], withscores=True) == resp_conversion_from_resp2(
        r, [(b"a2", 3), (b"a4", 4), (b"a3", 8), (b"a1", 9)]
    )
    # max
    assert r.zunion(["a", "b", "c"], aggregate="MAX", withscores=True) == resp_conversion_from_resp2(
        r, [(b"a2", 2), (b"a4", 4), (b"a3", 5), (b"a1", 6)]
    )
    # min
    assert r.zunion(["a", "b", "c"], aggregate="MIN", withscores=True) == resp_conversion_from_resp2(
        r, [(b"a1", 1), (b"a2", 1), (b"a3", 1), (b"a4", 4)]
    )
    # with weight
    assert r.zunion({"a": 1, "b": 2, "c": 3}, withscores=True) == resp_conversion_from_resp2(
        r, [(b"a2", 5), (b"a4", 12), (b"a3", 20), (b"a1", 23)]
    )


@pytest.mark.unsupported_server_types("dragonfly")  # TODO bad response
def test_zinter(r: ClientType):
    r.zadd("a", {"a1": 1, "a2": 2, "a3": 1})
    r.zadd("b", {"a1": 2, "a2": 2, "a3": 2})
    r.zadd("c", {"a1": 6, "a3": 5, "a4": 4})
    assert r.zinter(["a", "b", "c"]) == [b"a3", b"a1"]
    # invalid aggregation
    with pytest.raises(Exception) as ctx:
        r.zinter(["a", "b", "c"], aggregate="foo", withscores=True)
    assert isinstance(ctx.value, (redis.DataError, valkey.DataError))
    # aggregate with SUM
    assert r.zinter(["a", "b", "c"], withscores=True) == resp_conversion_from_resp2(r, [(b"a3", 8), (b"a1", 9)])
    # aggregate with MAX
    assert r.zinter(["a", "b", "c"], aggregate="MAX", withscores=True) == resp_conversion_from_resp2(
        r, [(b"a3", 5), (b"a1", 6)]
    )
    # aggregate with MIN
    assert r.zinter(["a", "b", "c"], aggregate="MIN", withscores=True) == resp_conversion_from_resp2(
        r, [(b"a1", 1), (b"a3", 1)]
    )
    # with weights
    assert r.zinter({"a": 1, "b": 2, "c": 3}, withscores=True) == resp_conversion_from_resp2(
        r, [(b"a3", 20), (b"a1", 23)]
    )


@pytest.mark.supported_redis_versions(min_ver="7")
def test_zintercard(r: ClientType):
    r.zadd("a", {"a1": 1, "a2": 2, "a3": 1})
    r.zadd("b", {"a1": 2, "a2": 2, "a3": 2})
    r.zadd("c", {"a1": 6, "a3": 5, "a4": 4})
    assert r.zintercard(3, ["a", "b", "c"]) == 2
    assert r.zintercard(3, ["a", "b", "c"], limit=1) == 1


def test_zrangestore(r: ClientType):
    r.zadd("a", {"a1": 1, "a2": 2, "a3": 3})
    assert r.zrangestore("b", "a", 0, 1)
    assert r.zrange("b", 0, -1) == [b"a1", b"a2"]
    assert r.zrangestore("b", "a", 1, 2)
    assert r.zrange("b", 0, -1) == [b"a2", b"a3"]
    assert r.zrange("b", 0, -1, withscores=True) == resp_conversion_from_resp2(r, [(b"a2", 2), (b"a3", 3)])
    # reversed order
    assert r.zrangestore("b", "a", 1, 2, desc=True)
    assert r.zrange("b", 0, -1) == [b"a1", b"a2"]
    # by score
    assert r.zrangestore("b", "a", 2, 1, byscore=True, offset=0, num=1, desc=True)
    assert r.zrange("b", 0, -1) == [b"a2"]
    # by lex
    assert r.zrange("a", "[a2", "(a3", bylex=True, offset=0, num=1) == [b"a2"]
    assert r.zrangestore("b", "a", "[a2", "(a3", bylex=True, offset=0, num=1)
    assert r.zrange("b", 0, -1) == [b"a2"]


@pytest.mark.supported_redis_versions(min_ver="7")
def test_zmpop(r: ClientType):
    r.zadd("a", {"a1": 1, "a2": 2, "a3": 3})
    assert r.zmpop("2", ["b", "a"], min=True, count=2) == resp_conversion(
        r, [b"a", [[b"a1", 1.0], [b"a2", 2.0]]], [b"a", [[b"a1", b"1"], [b"a2", b"2"]]]
    )
    with pytest.raises(Exception) as ctx:
        r.zmpop("2", ["b", "a"], count=2)
    assert isinstance(ctx.value, (redis.DataError, valkey.DataError))
    r.zadd("b", {"b1": 10, "ab": 9, "b3": 8})
    assert r.zmpop("2", ["b", "a"], max=True) == resp_conversion(r, [b"b", [[b"b1", 10.0]]], [b"b", [[b"b1", b"10"]]])


@pytest.mark.supported_redis_versions(min_ver="7")
def test_bzmpop(r: ClientType):
    r.zadd("a", {"a1": 1, "a2": 2, "a3": 3})
    assert r.bzmpop(1, "2", ["b", "a"], min=True, count=2) == resp_conversion(
        r, [b"a", [[b"a1", 1], [b"a2", 2]]], [b"a", [[b"a1", b"1"], [b"a2", b"2"]]]
    )
    with pytest.raises(Exception) as ctx:
        r.bzmpop(1, "2", ["b", "a"], count=2)
    assert isinstance(ctx.value, (redis.DataError, valkey.DataError))
    r.zadd("b", {"b1": 10, "ab": 9, "b3": 8})
    assert r.bzmpop(0, "2", ["b", "a"], max=True) == resp_conversion(
        r, [b"b", [[b"b1", 10.0]]], [b"b", [[b"b1", b"10"]]]
    )
    assert r.bzmpop(1, "2", ["foo", "bar"], max=True) is None


def test_zrangebyscore_negative_start_after_sort(r: ClientType):
    r.zadd("A", {"A": 0.0})
    r.zadd("B", {"A": 0.0})
    with pytest.raises(redis.ResponseError):
        r.sort("B")
    assert r.zrangebyscore("B", 0.0, 0.0, start=-1, num=1) == []
