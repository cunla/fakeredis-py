from __future__ import annotations

from typing import Any

import pytest
import redis
import valkey

import fakeredis
from fakeredis._typing import ClientType
from test.conftest import ServerDetails
from test.testtools import raw_command

_ = pytest.importorskip("lupa")

pytestmark = [
    pytest.mark.supported_server_versions(min_redis_ver="7"),
    pytest.mark.unsupported_server_types("dragonfly", "kividb"),
]

RESPONSE_ERRORS = (redis.ResponseError, valkey.ResponseError)

LIBRARY = (
    "#!lua name=mylib\n"
    "redis.register_function('set_key', function(keys, args) return redis.call('SET', keys[1], args[1]) end)\n"
    "redis.register_function{function_name='get_key', callback=function(keys, args)\n"
    "  return redis.call('GET', keys[1])\n"
    "end, flags={'no-writes'}, description='reads a key'}"
)
OTHER_LIBRARY = "#!lua name=other\nredis.register_function('other', function() return 'other' end)"


@pytest.fixture(autouse=True)
def _no_libraries(request: pytest.FixtureRequest):
    """Functions belong to the server rather than a database, so every test starts and ends without any."""
    if "r" not in request.fixturenames:
        yield
        return
    r = request.getfixturevalue("r")
    r.function_flush()
    yield
    r.function_flush()


def _error(r: ClientType, *args: Any) -> str:
    with pytest.raises(RESPONSE_ERRORS) as ctx:
        raw_command(r, *args)
    return str(ctx.value)


def _load(r: ClientType, *lines: str) -> None:
    raw_command(r, "FUNCTION", "LOAD", "\n".join(["#!lua name=lib", *lines]))


def _located(details: ServerDetails, function_name: str, line: int) -> str:
    """The suffix naming where a function raised an error it did not catch."""
    if details.server_type == "valkey" and details.server_version >= (9,):
        return f" script: on @user_function:{line}."
    return f" script: {function_name}, on @user_function:{line}."


def _as_dict(value: Any) -> dict[Any, Any]:
    """RESP3 sends a map; RESP2 flattens it into [key, value, ...]."""
    if isinstance(value, dict):
        return value
    return dict(zip(value[::2], value[1::2]))


def _libraries(r: ClientType, *args: str) -> list[dict[Any, Any]]:
    return [_as_dict(library) for library in raw_command(r, "FUNCTION", "LIST", *args)]


def test_function_load_and_fcall(r: ClientType):
    assert raw_command(r, "FUNCTION", "LOAD", LIBRARY) == b"mylib"
    assert raw_command(r, "FCALL", "set_key", 1, "key", "value") == b"OK"
    assert r.get("key") == b"value"
    assert raw_command(r, "FCALL", "get_key", 1, "key") == b"value"
    assert raw_command(r, "FCALL_RO", "get_key", 1, "key") == b"value"


def test_fcall_passes_keys_and_args(r: ClientType):
    _load(r, "redis.register_function('f', function(keys, args) return {#keys, #args, keys[1], args[2]} end)")
    assert raw_command(r, "FCALL", "f", 2, "k1", "k2", "a1", "a2") == [2, 2, b"k1", b"a2"]
    assert raw_command(r, "FCALL", "f", 0) == [0, 0]


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("return 1", "Missing library metadata"),
        ("#!lua name=lib", "Invalid library metadata"),
        ("#!lua\nredis.register_function('f', function() return 1 end)", "Library name was not given"),
        ("#!js name=lib\n1", "Engine 'js' not found"),
        ("#!lua name=lib foo=bar\n1", "Invalid metadata value given: foo=bar"),
        (
            "#!lua name=bad-name\n1",
            "Library names can only contain letters, numbers, or underscores(_) and must be at least one character long",
        ),
        ("#!lua name=lib\nreturn 1", "No functions registered"),
        ("#!lua name=lib\nsyntax error here", "Error compiling function: user_function:2: '=' expected near 'error'"),
    ],
)
def test_function_load_rejects_invalid_libraries(r: ClientType, code: str, expected: str):
    assert _error(r, "FUNCTION", "LOAD", code) == expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        (
            "redis.register_function('f')",
            (
                "calling {api}.register_function with a single argument is only applicable to Lua table (representing "
                "named arguments)."
            ),
        ),
        ("redis.register_function()", "wrong number of arguments to {api}.register_function"),
        ("redis.register_function('f', 'nope')", "second argument to {api}.register_function must be a function"),
        ("redis.register_function{function_name='f'}", "{api}.register_function must get a callback argument"),
        (
            "redis.register_function{callback=function() return 1 end}",
            "{api}.register_function must get a function name argument",
        ),
        (
            "redis.register_function{function_name='f', callback=function() return 1 end, foo=1}",
            "unknown argument given to {api}.register_function",
        ),
        (
            "redis.register_function{function_name='f', callback=function() return 1 end, flags='no-writes'}",
            "flags argument to {api}.register_function must be a table representing function flags",
        ),
        (
            "redis.register_function{function_name='f', callback=function() return 1 end, flags={'bogus'}}",
            "unknown flag given",
        ),
        (
            "redis.register_function{function_name='f', callback=function() return 1 end, description={}}",
            "description argument given to {api}.register_function must be a string",
        ),
        (
            "redis.call('SET', 'a', 'b')",
            "user_function:2: Script attempted to access nonexistent global variable 'call'",
        ),
        ("local t = ipairs", "user_function:2: Script attempted to access nonexistent global variable 'ipairs'"),
        ("x = 1", "user_function:2: Attempt to modify a readonly table"),
    ],
)
def test_function_load_reports_registration_errors(
    r: ClientType, real_server_details: ServerDetails, line: str, expected: str
):
    api = "server" if real_server_details.server_type == "valkey" else "redis"
    message = expected.format(api=api)
    assert _error(r, "FUNCTION", "LOAD", f"#!lua name=lib\n{line}") == f"Error registering functions: ERR {message}"


def test_function_names_are_checked(r: ClientType, real_server_details: ServerDetails):
    bad_name = "#!lua name=lib\nredis.register_function('bad-name', function() return 1 end)"
    registered_twice = (
        "#!lua name=lib\n"
        "redis.register_function('f', function() return 1 end)\n"
        "redis.register_function('f', function() return 2 end)"
    )
    rules = "can only contain letters, numbers, or underscores(_) and must be at least one character long"
    if real_server_details.server_type == "valkey":
        assert _error(r, "FUNCTION", "LOAD", bad_name) == f"Function names {rules}"
        assert _error(r, "FUNCTION", "LOAD", registered_twice) == "Function already exists in the library"
    else:
        # Redis checks a function's name against the rules for library names.
        assert _error(r, "FUNCTION", "LOAD", bad_name) == f"Error registering functions: ERR Library names {rules}"
        assert (
            _error(r, "FUNCTION", "LOAD", registered_twice)
            == "Error registering functions: ERR Function already exists in the library"
        )


def test_function_load_replace(r: ClientType):
    raw_command(r, "FUNCTION", "LOAD", LIBRARY)
    assert _error(r, "FUNCTION", "LOAD", LIBRARY) == "Library 'mylib' already exists"
    replacement = "#!lua name=mylib\nredis.register_function('new_function', function() return 'new' end)"
    assert raw_command(r, "FUNCTION", "LOAD", "REPLACE", replacement) == b"mylib"
    assert raw_command(r, "FCALL", "new_function", 0) == b"new"
    assert _error(r, "FCALL", "set_key", 1, "key", "value") == "Function not found"


def test_function_load_options(r: ClientType):
    assert _error(r, "FUNCTION", "LOAD", "BADOPT", LIBRARY) == "Unknown option given: BADOPT"
    assert _error(r, "FUNCTION", "LOAD", "REPLACE") == "Missing library metadata"
    assert raw_command(r, "FUNCTION", "LOAD", "replace", "REPLACE", LIBRARY) == b"mylib"


def test_function_names_are_unique_across_libraries(r: ClientType):
    raw_command(r, "FUNCTION", "LOAD", LIBRARY)
    clash = "#!lua name=other\nredis.register_function('set_key', function() return 1 end)"
    assert _error(r, "FUNCTION", "LOAD", clash) == "Function set_key already exists"
    assert _error(r, "FUNCTION", "LOAD", "REPLACE", clash) == "Function set_key already exists"
    assert [library[b"library_name"] for library in _libraries(r)] == [b"mylib"]


def test_function_runs_in_a_sandbox(r: ClientType, real_server_details: ServerDetails):
    _load(
        r,
        "redis.register_function('set_global', function() g = 1 return 1 end)",
        "redis.register_function('read_keys', function() return KEYS end)",
        "redis.register_function('register', function() redis.register_function('x', function() return 1 end) end)",
        "redis.register_function('globals', function() return {type(string), type(table), type(cjson), type(pcall)} end)",
    )
    assert _error(r, "FCALL", "set_global", 0) == "user_function:2: Attempt to modify a readonly table" + _located(
        real_server_details, "set_global", 2
    )
    assert _error(
        r, "FCALL", "read_keys", 0
    ) == "user_function:3: Script attempted to access nonexistent global variable 'KEYS'" + _located(
        real_server_details, "read_keys", 3
    )
    assert _error(
        r, "FCALL", "register", 0
    ) == "user_function:4: attempt to call field 'register_function' (a nil value)" + _located(
        real_server_details, "register", 4
    )
    assert raw_command(r, "FCALL", "globals", 0) == [b"table", b"table", b"table", b"function"]


def test_fcall_argument_errors(r: ClientType):
    raw_command(r, "FUNCTION", "LOAD", LIBRARY)
    assert _error(r, "FCALL", "missing", 0) == "Function not found"
    assert _error(r, "FCALL", "missing", -1) == "Function not found"
    assert _error(r, "FCALL_RO", "missing", 0) == "Function not found"
    assert _error(r, "FCALL", "set_key", "one") == "Bad number of keys provided"
    assert _error(r, "FCALL", "set_key", "+1", "key", "value") == "Bad number of keys provided"
    assert _error(r, "FCALL", "set_key", -1) == "Number of keys can't be negative"
    assert _error(r, "FCALL", "set_key", 3, "key", "value") == "Number of keys can't be greater than number of args"


def test_fcall_errors_name_the_function_and_line(r: ClientType, real_server_details: ServerDetails):
    _load(
        r,
        "redis.register_function('incr', function() return redis.call('INCR', 'string') end)",
        "redis.register_function('incr_pcall', function() return redis.pcall('INCR', 'string') end)",
        "redis.register_function('index_nil', function()",
        "  local t = nil",
        "  return t.x",
        "end)",
        "redis.register_function('error_reply', function() return redis.error_reply('My error') end)",
        "redis.register_function('status_reply', function() return redis.status_reply('FINE') end)",
    )
    r.set("string", "abc")
    assert _error(r, "FCALL", "incr", 0) == "value is not an integer or out of range" + _located(
        real_server_details, "incr", 2
    )
    assert _error(r, "FCALL", "incr_pcall", 0) == "value is not an integer or out of range"
    assert _error(r, "FCALL", "index_nil", 0) == "user_function:6: attempt to index local 't' (a nil value)" + _located(
        real_server_details, "index_nil", 6
    )
    assert _error(r, "FCALL", "error_reply", 0) == "My error"
    assert raw_command(r, "FCALL", "status_reply", 0) == b"FINE"


def test_fcall_bad_redis_calls(r: ClientType, real_server_details: ServerDetails):
    _load(
        r,
        "redis.register_function('unknown', function() return redis.call('NOPE') end)",
        "redis.register_function('arity', function() return redis.call('GET') end)",
        "redis.register_function('bad_arg', function() return redis.call('SET', 'key', {}) end)",
    )
    if real_server_details.server_type == "valkey":
        unknown, arity, bad_arg = (
            "Unknown command called from script",
            "Wrong number of args calling command from script",
            "Command arguments must be strings or integers",
        )
    else:
        unknown, arity, bad_arg = (
            "Unknown Redis command called from script",
            "Wrong number of args calling Redis command from script",
            "Lua redis lib command arguments must be strings or integers",
        )
    assert _error(r, "FCALL", "unknown", 0) == unknown + _located(real_server_details, "unknown", 2)
    assert _error(r, "FCALL", "arity", 0) == arity + _located(real_server_details, "arity", 3)
    assert _error(r, "FCALL", "bad_arg", 0) == bad_arg + _located(real_server_details, "bad_arg", 4)


def test_fcall_ro_and_no_writes_functions(r: ClientType, real_server_details: ServerDetails):
    _load(
        r,
        "redis.register_function('reader', function(keys) return redis.call('GET', keys[1]) end)",
        "redis.register_function{function_name='ro_reader', flags={'no-writes'},",
        "  callback=function(keys) return redis.call('GET', keys[1]) end}",
        "redis.register_function{function_name='ro_writer', flags={'no-writes'},",
        "  callback=function(keys) return redis.call('SET', keys[1], 'new') end}",
    )
    r.set("key", "value")
    assert _error(r, "FCALL_RO", "reader", 1, "key") == "Can not execute a script with write flag using *_ro command."
    assert raw_command(r, "FCALL_RO", "ro_reader", 1, "key") == b"value"
    refused = "Write commands are not allowed from read-only scripts." + _located(real_server_details, "ro_writer", 6)
    assert _error(r, "FCALL", "ro_writer", 1, "key") == refused
    assert _error(r, "FCALL_RO", "ro_writer", 1, "key") == refused
    assert r.get("key") == b"value"


def test_fcall_is_not_allowed_from_scripts(r: ClientType):
    raw_command(r, "FUNCTION", "LOAD", LIBRARY)
    with pytest.raises(RESPONSE_ERRORS, match="not allowed from script"):
        r.eval("return redis.call('FCALL', 'get_key', 1, 'key')", 0)


def test_function_setresp(r: ClientType):
    _load(
        r,
        "redis.register_function('hgetall3', function(keys) redis.setresp(3) return redis.call('HGETALL', keys[1]) end)",
    )
    r.hset("hash", "field", "value")
    protocol = int(r.connection_pool.connection_kwargs.get("protocol") or 2)
    expected = {b"field": b"value"} if protocol == 3 else [b"field", b"value"]
    assert raw_command(r, "FCALL", "hgetall3", 1, "hash") == expected


def test_function_version_fields(r: ClientType):
    _load(
        r,
        "local version = redis.REDIS_VERSION",
        "redis.register_function('version', function()",
        "  return {version, redis.REDIS_VERSION_NUM, redis.sha1hex('abc')}",
        "end)",
    )
    version, version_num, sha1 = raw_command(r, "FCALL", "version", 0)
    major, minor, patch = (int(part) for part in version.split(b"."))
    assert version_num == (major << 16) | (minor << 8) | patch
    assert sha1 == b"a9993e364706816aba3e25717850c26c9cd0d89d"


def test_function_list(r: ClientType):
    raw_command(r, "FUNCTION", "LOAD", LIBRARY)
    raw_command(r, "FUNCTION", "LOAD", OTHER_LIBRARY)
    libraries = {library[b"library_name"]: library for library in _libraries(r)}
    assert set(libraries) == {b"mylib", b"other"}
    mylib = libraries[b"mylib"]
    assert mylib[b"engine"] == b"LUA"
    assert b"library_code" not in mylib
    # Libraries and functions come back in hash order, which differs between servers.
    functions = sorted((_as_dict(function) for function in mylib[b"functions"]), key=lambda f: f[b"name"])
    assert functions == [
        {b"name": b"get_key", b"description": b"reads a key", b"flags": [b"no-writes"]},
        {b"name": b"set_key", b"description": None, b"flags": []},
    ]

    assert [library[b"library_name"] for library in _libraries(r, "LIBRARYNAME", "my*")] == [b"mylib"]
    assert _libraries(r, "LIBRARYNAME", "my") == []
    (with_code,) = _libraries(r, "WITHCODE", "LIBRARYNAME", "mylib")
    assert with_code[b"library_code"] == LIBRARY.encode()

    assert _error(r, "FUNCTION", "LIST", "LIBRARYNAME") == "library name argument was not given"
    assert _error(r, "FUNCTION", "LIST", "LIBRARYNAME", "a", "LIBRARYNAME", "b") == "Unknown argument LIBRARYNAME"
    assert _error(r, "FUNCTION", "LIST", "WITHCODE", "WITHCODE") == "Unknown argument WITHCODE"
    assert _error(r, "FUNCTION", "LIST", "BAD") == "Unknown argument BAD"


def test_function_flags_are_listed_in_a_fixed_order(r: ClientType):
    _load(
        r,
        "redis.register_function{function_name='f', callback=function() return 1 end,",
        "  flags={'allow-cross-slot-keys', 'no-cluster', 'allow-stale', 'allow-oom', 'no-writes'}}",
    )
    (library,) = _libraries(r)
    (function,) = [_as_dict(function) for function in library[b"functions"]]
    assert function[b"flags"] == [b"no-writes", b"allow-oom", b"allow-stale", b"no-cluster", b"allow-cross-slot-keys"]


def test_function_delete_flush_and_stats(r: ClientType):
    def lua_stats() -> tuple[Any, dict[Any, Any]]:
        stats = _as_dict(raw_command(r, "FUNCTION", "STATS"))
        return stats[b"running_script"], _as_dict(_as_dict(stats[b"engines"])[b"LUA"])

    assert lua_stats() == (None, {b"libraries_count": 0, b"functions_count": 0})
    raw_command(r, "FUNCTION", "LOAD", LIBRARY)
    raw_command(r, "FUNCTION", "LOAD", OTHER_LIBRARY)
    assert lua_stats() == (None, {b"libraries_count": 2, b"functions_count": 3})

    assert raw_command(r, "FUNCTION", "DELETE", "other") == b"OK"
    assert _error(r, "FUNCTION", "DELETE", "other") == "Library not found"
    assert lua_stats() == (None, {b"libraries_count": 1, b"functions_count": 2})

    assert _error(r, "FUNCTION", "FLUSH", "BAD") == "FUNCTION FLUSH only supports SYNC|ASYNC option"
    assert (
        _error(r, "FUNCTION", "FLUSH", "SYNC", "EXTRA")
        == "unknown subcommand or wrong number of arguments for 'FLUSH'. Try FUNCTION HELP."
    )
    assert raw_command(r, "FUNCTION", "FLUSH", "sync") == b"OK"
    assert _libraries(r) == []


def test_function_kill_without_a_running_function(r: ClientType):
    assert _error(r, "FUNCTION", "KILL") == "NOTBUSY No scripts in execution right now."


def test_function_dump_and_restore(r: ClientType):
    raw_command(r, "FUNCTION", "LOAD", LIBRARY)
    payload = raw_command(r, "FUNCTION", "DUMP")
    assert _error(r, "FUNCTION", "RESTORE", payload) == "Library mylib already exists"
    assert _error(r, "FUNCTION", "RESTORE", payload, "APPEND") == "Library mylib already exists"
    assert (
        _error(r, "FUNCTION", "RESTORE", payload, "NOPE")
        == "Wrong restore policy given, value should be either FLUSH, APPEND or REPLACE."
    )
    assert (
        _error(r, "FUNCTION", "RESTORE", payload, "FLUSH", "EXTRA")
        == "unknown subcommand or wrong number of arguments for 'RESTORE'. Try FUNCTION HELP."
    )
    assert _error(r, "FUNCTION", "RESTORE", "garbage") == "DUMP payload version or checksum are wrong"
    assert raw_command(r, "FUNCTION", "RESTORE", payload, "REPLACE") == b"OK"

    raw_command(r, "FUNCTION", "DELETE", "mylib")
    raw_command(r, "FUNCTION", "LOAD", OTHER_LIBRARY)
    assert raw_command(r, "FUNCTION", "RESTORE", payload) == b"OK"
    assert sorted(library[b"library_name"] for library in _libraries(r)) == [b"mylib", b"other"]

    assert raw_command(r, "FUNCTION", "RESTORE", payload, "FLUSH") == b"OK"
    assert [library[b"library_name"] for library in _libraries(r)] == [b"mylib"]
    assert raw_command(r, "FCALL", "set_key", 1, "key", "value") == b"OK"

    raw_command(r, "FUNCTION", "FLUSH")
    raw_command(r, "FUNCTION", "LOAD", "#!lua name=clash\nredis.register_function('set_key', function() return 1 end)")
    assert _error(r, "FUNCTION", "RESTORE", payload) == "Function set_key already exists"


def test_functions_survive_flushall(r: ClientType):
    raw_command(r, "FUNCTION", "LOAD", LIBRARY)
    r.flushall()
    assert raw_command(r, "FCALL", "set_key", 1, "key", "value") == b"OK"


def test_function_help(r: ClientType):
    lines = raw_command(r, "FUNCTION", "HELP")
    assert lines[0] == b"FUNCTION <subcommand> [<arg> [value] [opt] ...]. Subcommands are:"
    assert b"LOAD [REPLACE] <FUNCTION CODE>" in lines
    assert b"RESTORE <PAYLOAD> [FLUSH|APPEND|REPLACE]" in lines


@pytest.mark.fake
def test_functions_need_redis_7():
    r = fakeredis.FakeStrictRedis(server=fakeredis.FakeServer(version=6))
    with pytest.raises(redis.ResponseError, match="unknown command 'function'"):
        r.function_list()
    with pytest.raises(redis.ResponseError, match="unknown command 'fcall'"):
        r.fcall("f", 0)
