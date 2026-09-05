"""Lua scripting behaviour where Dragonfly deliberately differs from Redis.

The Redis-flavoured versions of these tests live in
`test/test_mixins/test_scripting_commands.py` and are marked
`@pytest.mark.unsupported_server_types("dragonfly")`; these are the Dragonfly
counterparts, so both sides of each divergence stay covered.
"""

from __future__ import annotations

import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test.testtools import raw_command, resp_conversion

_ = pytest.importorskip("lupa")

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("redis", "valkey", "kividb"),
    ]
)


@pytest.mark.parametrize("args", [("a",), tuple("abcdefghijklmn")])
def test_script_flush_ignores_extra_args(r: ClientType, args: tuple[str, ...]):
    # Redis rejects anything that is not ASYNC/SYNC; Dragonfly has no mode argument at all
    # and simply ignores whatever follows.
    sha1 = r.script_load("return 'a'")
    assert raw_command(r, "SCRIPT FLUSH {}".format(" ".join(args))) == b"OK"
    assert r.script_exists(sha1) == [0]


def test_script_help(r: ClientType):
    assert raw_command(r, "SCRIPT HELP") == [
        b"SCRIPT <subcommand> [<arg> [value] [opt] ...]",
        b"Subcommands are:",
        b"EXISTS <sha1> [<sha1> ...]",
        b"   Return information about the existence of the scripts in the script cache.",
        b"FLUSH",
        b"   Flush the Lua scripts cache. Very dangerous on replicas.",
        b"LOAD <script>",
        b"   Load a script into the scripts cache without executing it.",
        b"FLAGS <sha> [flags ...]",
        b"   Set specific flags for script. Can be called before the sript is loaded.",
        b"   The following flags are possible: ",
        b"      - Use 'allow-undeclared-keys' to allow accessing undeclared keys",
        b"      - Use 'disable-atomicity' to allow running scripts non-atomically",
        b"      - Use 'legacy-float' to return floats as integers",
        b"LIST",
        b"   Lists loaded scripts.",
        b"LATENCY",
        b"   Prints latency histograms in usec for every called function.",
        b"GC",
        b"   Invokes garbage collection on all unused interpreter instances.",
        b"HELP",
        b"   Prints this help.",
    ]


@pytest.mark.parametrize("value", [3.2, 3.8, -3.8])
def test_eval_keeps_fractional_numbers(r: ClientType, value: float):
    # Redis truncates every Lua number to an integer, Dragonfly replies with a double --
    # rendered under RESP2 as the shortest bulk string that round-trips.
    assert r.eval(f"return {value}", 0) == resp_conversion(r, value, str(value).encode())


def test_eval_still_truncates_whole_numbers(r: ClientType):
    # `return 3.0` is not asserted here: Dragonfly runs Lua 5.4, whose integer subtype tells
    # it apart from `return 3` and makes it a double, and the 5.1 runtime fakeredis uses
    # cannot draw that distinction.
    assert r.eval("return 3", 0) == 3


def test_eval_call_bool(r: ClientType):
    # Dragonfly kept the pre-7 wording, which names `redis()` rather than "redis lib".
    with pytest.raises(Exception) as exc_info:
        r.eval('return redis.call("SET", KEYS[1], true)', 1, "testkey")
    assert isinstance(exc_info.value, (redis.ResponseError, valkey.ResponseError))
    assert "Lua redis() command arguments must be strings or integers" in str(exc_info.value)


@pytest.mark.parametrize("command", ["FLUSHDB", "FLUSHALL"])
def test_eval_cannot_flush(r: ClientType, command: str):
    # Redis lets a script flush the keyspace; Dragonfly refuses.
    r.set("foo", "bar")
    with pytest.raises(Exception, match="not allowed from script") as exc_info:
        r.eval(f'return redis.call("{command}")', 0)
    assert isinstance(exc_info.value, (redis.ResponseError, valkey.ResponseError))
    assert r.get("foo") == b"bar"


def test_eval_incrbyfloat_returns_a_number(r: ClientType):
    # Redis hands INCRBYFLOAT's bulk string to Lua as a string, Dragonfly as a number.
    r.set("foo", 0.5)
    val = r.eval(
        """
        local value = redis.call("INCRBYFLOAT", KEYS[1], 2.0);
        return type(value) == "number" and tostring(value) or type(value);
        """,
        1,
        "foo",
    )
    assert val == b"2.5"


def test_incrbyfloat_replies_with_a_double(r: ClientType):
    r.set("foo", 0.5)
    assert raw_command(r, "INCRBYFLOAT", "foo", "2.0") == resp_conversion(r, 2.5, b"2.5")


def test_hincrbyfloat_replies_with_a_double(r: ClientType):
    assert raw_command(r, "HINCRBYFLOAT", "foo", "field", "1.5") == resp_conversion(r, 1.5, b"1.5")


def test_lua_log_ignores_wrong_level(r: ClientType):
    # Redis rejects a level outside LOG_DEBUG..LOG_WARNING; Dragonfly drops the message.
    assert r.register_script("redis.log(10, 'string')")() is None


def test_lua_log_still_needs_two_arguments(r: ClientType):
    with pytest.raises(Exception, match="requires two arguments or more") as ctx:
        r.register_script("redis.log(redis.LOG_WARNING)")()
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
