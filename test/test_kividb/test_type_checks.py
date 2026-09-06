"""The type checks KiviDB does not make, and the one it makes that redis does not.

Redis answers WRONGTYPE for any key whose type a command cannot use. KiviDB reads a wrongly typed
key as an empty one in its multi-key set operations, and passes over one in some -- not all -- of its
blocking pops. It is stricter in the other direction for the sorted set aggregates, which refuse a
plain set that redis would read as a sorted set scoring every member 1.

The redis-flavoured versions of these tests are marked
`@pytest.mark.unsupported_server_types("kividb")` in `test/test_mixins`.
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

WRONGTYPE = "WRONGTYPE Operation against a key holding the wrong kind of value"


@pytest.fixture
def mixed(r: ClientType) -> ClientType:
    """A string, a list, a set and a sorted set, so every command has a wrong type to be given."""
    r.set("str", "v")
    r.rpush("list", "a", "b")
    r.sadd("set", "m")
    r.zadd("zset", {"m": 1})
    return r


def test_multi_key_set_reads_take_a_wrong_type_as_empty(mixed: ClientType):
    assert raw_command(mixed, "sdiff", "str", "set") == []
    assert raw_command(mixed, "sdiff", "set", "str") == [b"m"]
    assert raw_command(mixed, "sinter", "str", "set") == []
    assert raw_command(mixed, "sunion", "str", "set") == [b"m"]
    assert raw_command(mixed, "sintercard", 2, "str", "set") == 0
    # A sorted set is just as wrong a type here as a string is.
    assert raw_command(mixed, "sunion", "zset", "set") == [b"m"]


def test_multi_key_set_stores_take_a_wrong_type_as_empty(mixed: ClientType):
    assert raw_command(mixed, "sdiffstore", "dest", "str", "set") == 0
    assert raw_command(mixed, "sinterstore", "dest", "str", "set") == 0
    assert raw_command(mixed, "sunionstore", "dest", "str", "set") == 1


@pytest.mark.parametrize(
    "args",
    [
        ("smembers", "str"),
        ("scard", "str"),
        ("sismember", "str", "m"),
        ("sadd", "str", "m"),
        ("srem", "str", "m"),
        ("spop", "str"),
        ("smove", "str", "set", "m"),
        ("smove", "set", "str", "m"),
    ],
)
def test_single_key_set_commands_still_check(mixed: ClientType, args: tuple):
    with pytest.raises(Exception, match=WRONGTYPE):
        raw_command(mixed, *args)


@pytest.mark.parametrize(
    "args",
    [
        ("brpop", "str", 0.1),
        ("brpoplpush", "str", "list", 0.1),
        ("bzpopmin", "str", 0.1),
        ("bzpopmax", "str", 0.1),
        ("bzmpop", 0.1, 1, "str", "min"),
        ("blmpop", 0.1, 1, "str", "left"),
        ("lmpop", 1, "str", "left"),
    ],
)
def test_pops_that_pass_over_a_wrong_type(mixed: ClientType, args: tuple):
    """These answer nil -- the blocking ones after waiting out their timeout -- rather than WRONGTYPE."""
    assert raw_command(mixed, *args) is None


@pytest.mark.parametrize(
    "args",
    [
        ("blpop", "str", 0.1),
        ("blmove", "str", "list", "left", "right", 0.1),
        ("lmove", "str", "list", "left", "right"),
        ("rpoplpush", "str", "list"),
        ("zmpop", 1, "str", "min"),
        ("lpop", "str"),
        ("lrange", "str", 0, -1),
    ],
)
def test_pops_that_still_check(mixed: ClientType, args: tuple):
    """BLPOP checks where BRPOP does not, and ZMPOP where BZMPOP does not."""
    with pytest.raises(Exception, match=WRONGTYPE):
        raw_command(mixed, *args)


def test_a_wrong_type_is_only_passed_over_not_given_up_on(mixed: ClientType):
    """The keys that can be popped from still are, whichever side of the bad key they are on."""
    assert raw_command(mixed, "brpop", "str", "list", 0.1) == [b"list", b"b"]
    assert raw_command(mixed, "brpop", "list", "str", 0.1) == [b"list", b"a"]


@pytest.mark.parametrize(
    "args",
    [
        ("zdiff", 2, "set", "zset"),
        ("zunion", 2, "set", "zset"),
        ("zintercard", 2, "set", "zset"),
        ("zinterstore", "dest", 2, "set", "zset"),
        ("zunionstore", "dest", 2, "set", "zset"),
        ("zdiffstore", "dest", 2, "set", "zset"),
    ],
)
def test_sorted_set_aggregates_refuse_a_plain_set(mixed: ClientType, args: tuple):
    """Redis reads a plain set as a sorted set scoring every member 1; KiviDB never does."""
    with pytest.raises(Exception, match=WRONGTYPE):
        raw_command(mixed, *args)
