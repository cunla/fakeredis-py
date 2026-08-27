"""Behaviour where Dragonfly deliberately differs from Redis.

The Redis-flavoured versions of these tests are marked
`@pytest.mark.unsupported_server_types("dragonfly")` in `test/test_mixins`; these are the
Dragonfly counterparts, so both sides of each divergence stay covered.
"""

from __future__ import annotations

import pytest

from fakeredis._typing import ClientType
from test.testtools import raw_command

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("redis", "valkey"),
    ]
)

RESPONSE_ERRORS = ("redis.exceptions.ResponseError", "valkey.exceptions.ResponseError")


def _raises(r: ClientType, match: str, *args):
    with pytest.raises(Exception, match=match) as ctx:
        raw_command(r, *args)
    assert type(ctx.value).__module__ + "." + type(ctx.value).__qualname__ in RESPONSE_ERRORS
    return ctx.value


def test_unknown_command_message_format(r: ClientType):
    # Dragonfly names the command in backticks and uppercase, and does not echo the args.
    err = _raises(r, "unknown command", "nosuchcmd", "a", "b")
    assert str(err) == "unknown command `NOSUCHCMD`"


def test_lcs_is_not_supported(r: ClientType):
    r.mset({"key1": "ohmytext", "key2": "mynewtext"})
    err = _raises(r, "unknown command", "lcs", "key1", "key2")
    assert str(err) == "unknown command `LCS`"


def test_at_least_one_key_is_needed_for_numkeys_commands(r: ClientType):
    r.sadd("s", "m")
    r.zadd("z", {"m": 1.0})
    for args in (
        ("sintercard", 0, "s"),
        ("zintercard", 0, "z"),
        ("zunion", 0, "z"),
        ("zunionstore", "dst", 0, "z"),
    ):
        _raises(r, "at least 1 input key is needed for this command", *args)
    # Dragonfly reads numkeys as unsigned, so a negative one never decodes.
    for args in (("sintercard", -1, "s"), ("zintercard", -1, "z")):
        _raises(r, "value is not an integer or out of range", *args)


def test_smove_checks_the_destination_type_even_when_the_source_is_missing(r: ClientType):
    r.set("str", "x")
    _raises(r, "WRONGTYPE", "smove", "nosuchkey", "str", "m")
    # With both keys missing there is nothing to check, and the answer is 0.
    assert r.smove("nosuchkey", "alsomissing", "m") is False
