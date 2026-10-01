"""How KiviDB reads the arguments of its sorted set commands.

Its sorted set parser is permissive where redis is strict: an endpoint it cannot use becomes an
unbounded or an empty range, an option it does not recognise is dropped, and COUNT/LIMIT/numkeys go
unchecked. The redis-flavoured versions of these tests are marked
`@pytest.mark.unsupported_server_types("kividb")` in `test/test_mixins`, so both sides stay covered.

Nothing here is shared with the other server types: redis, valkey and dragonfly all reject these.
"""

from __future__ import annotations

import pytest

from fakeredis._typing import ClientType
from test.testtools import raw_command

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("redis", "valkey", "dragonfly"),
    ]
)


@pytest.fixture
def zset(r: ClientType) -> ClientType:
    r.zadd("z", {"a": 0, "b": 0, "c": 0})
    return r


@pytest.fixture
def scored(r: ClientType) -> ClientType:
    r.zadd("s", {"one": 1, "two": 2, "three": 3})
    return r


@pytest.mark.parametrize("endpoint", [b"-", b"+", b"", b"b", b"junk"])
def test_lex_endpoint_without_a_bracket_is_unbounded(zset: ClientType, endpoint: bytes):
    """Only `[item` and `(item` name an item; everything else is unbounded on the side it is used."""
    assert raw_command(zset, "zrangebylex", "z", endpoint, "+") == [b"a", b"b", b"c"]
    assert raw_command(zset, "zrangebylex", "z", "-", endpoint) == [b"a", b"b", b"c"]


def test_lex_range_reversed_bounds(zset: ClientType):
    # `+` as the minimum and `-` as the maximum are both unbounded, so the whole set comes back
    # where redis answers with nothing.
    assert raw_command(zset, "zrangebylex", "z", "+", "-") == [b"a", b"b", b"c"]
    assert raw_command(zset, "zlexcount", "z", "+", "-") == 3
    assert raw_command(zset, "zrange", "z", "+", "-", "bylex") == [b"a", b"b", b"c"]
    # Two named items in the wrong order are still an empty range, as on redis.
    assert raw_command(zset, "zrangebylex", "z", "[c", "[a") == []


def test_lex_range_named_bounds_still_apply(zset: ClientType):
    assert raw_command(zset, "zrangebylex", "z", "[b", "+") == [b"b", b"c"]
    assert raw_command(zset, "zrangebylex", "z", "(b", "+") == [b"c"]
    assert raw_command(zset, "zremrangebylex", "z", "junk", "+") == 3


def test_score_endpoint_that_is_not_a_float(scored: ClientType):
    """The ranged reads answer with nothing; the counting and removing ones still reject it."""
    assert raw_command(scored, "zrangebyscore", "s", "one", "+inf") == []
    assert raw_command(scored, "zrevrangebyscore", "s", "one", "+inf") == []
    assert raw_command(scored, "zrange", "s", "one", "+inf", "byscore") == []
    for command in ("zcount", "zremrangebyscore"):
        with pytest.raises(Exception, match="min or max is not a float"):
            raw_command(scored, command, "s", "one", "+inf")


def test_index_that_is_not_usable_reads_as_zero(scored: ClientType):
    assert raw_command(scored, "zrange", "s", "x", "y") == [b"one"]
    assert raw_command(scored, "zrevrange", "s", "x", "y") == [b"three"]
    assert raw_command(scored, "zrange", "s", 0, 2**63) == [b"one"]


def test_options_that_are_dropped(scored: ClientType):
    # An option missing its values, and a word that is not an option at all.
    assert raw_command(scored, "zrangebyscore", "s", 0, 5, "limit", 0) == [b"one", b"two", b"three"]
    assert raw_command(scored, "zrangebyscore", "s", 0, 5, "bogus") == [b"one", b"two", b"three"]
    # LIMIT without BYSCORE/BYLEX, which redis rejects outright.
    assert raw_command(scored, "zrange", "s", 0, -1, "limit", 0, 1) == [b"one", b"two", b"three"]
    # A negative offset skips the whole range on redis; here it is no offset at all.
    assert raw_command(scored, "zrangebyscore", "s", "-inf", "+inf", "limit", -1, 3) == [b"one", b"two", b"three"]


def test_bylex_and_byscore_together(scored: ClientType):
    """Redis rejects the combination; KiviDB lets BYSCORE win -- and `(t` is not a score."""
    assert raw_command(scored, "zrange", "s", "(t", "+", "bylex", "byscore") == []


def test_numkeys_zero_is_an_empty_input(r: ClientType):
    r.zadd("dest", {"old": 5})
    assert raw_command(r, "zinterstore", "dest", 0, "aggregate", "max") == 0
    # The destination is emptied. Whether the key itself survives is a separate divergence: KiviDB
    # keeps emptied collections where redis drops them.
    assert r.zrange("dest", 0, -1) == []
    assert raw_command(r, "zinter", 0, "aggregate", "max") == []
    with pytest.raises(Exception, match="numkeys must be a positive integer"):
        raw_command(r, "zinterstore", "dest", -1, "aggregate", "max")


def test_numkeys_over_the_keys_given(r: ClientType):
    r.zadd("x", {"m": 1})
    r.zadd("y", {"m": 2})
    with pytest.raises(Exception, match="numkeys is greater than number of keys"):
        raw_command(r, "zinterstore", "dest", 3, "x", "y")
    # A word that is not an option is walked past, but WEIGHTS still has to carry one value per key.
    assert raw_command(r, "zinterstore", "dest", 1, "x", "bogus") == 1
    with pytest.raises(Exception, match="weight value is not a float"):
        raw_command(r, "zinterstore", "dest", 2, "x", "y", "weights", 1)


def test_zintercard_limit_is_unchecked(r: ClientType):
    r.zadd("x", {"m": 1, "n": 2})
    r.zadd("y", {"m": 1, "n": 2})
    assert raw_command(r, "zintercard", 2, "x", "y", "limit", -1) == 2
    assert raw_command(r, "zintercard", 2, "x", "y", "limit", 1) == 1


@pytest.mark.parametrize("command,key,direction", [("zmpop", "s", "min"), ("lmpop", "l", "left")])
def test_mpop_count_is_unchecked(r: ClientType, command: str, key: str, direction: str):
    r.zadd("s", {"one": 1, "two": 2})
    r.rpush("l", "a", "b")
    assert raw_command(r, command, 1, key, direction, "count", 0) is None
    popped = raw_command(r, command, 1, key, direction, "count", -1)
    assert len(popped[1]) == 1  # a negative count pops a single element
    with pytest.raises(Exception, match="numkeys can't be non-positive"):
        raw_command(r, command, 0, key, direction)


def test_zadd_nx_with_gt_or_lt(r: ClientType):
    """Redis rejects NX alongside GT/LT; KiviDB accepts it, and NX wins."""
    r.zadd("z", {"m": 5})
    assert raw_command(r, "zadd", "z", "gt", "nx", 9, "m") == 0
    assert raw_command(r, "zadd", "z", "lt", "nx", 1, "m") == 0
    assert r.zscore("z", "m") == 5
    assert raw_command(r, "zadd", "z", "gt", "nx", 3, "new") == 1
    with pytest.raises(Exception, match="GT and LT options at the same time are not compatible"):
        raw_command(r, "zadd", "z", "gt", "lt", 1, "m")
