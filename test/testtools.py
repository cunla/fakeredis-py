from __future__ import annotations

import importlib.util
import inspect
import itertools
import json
import time
from datetime import datetime
from typing import Any

import pytest
import redis
from packaging.version import Version

from fakeredis._commands import Float
from fakeredis._typing import ClientType

REDIS_PY_VERSION = Version(redis.__version__)


def pool_get_connection(pool: Any) -> Any:
    """Get a connection from `pool`, papering over the differing signatures.

    redis-py made `command_name` optional in 5.0 and deprecated it in 5.3, while
    valkey-py still requires it, so the installed redis-py version says nothing about
    the pool actually in use. Inspect the pool itself instead.

    Async pools return a coroutine, so the caller awaits the result as usual.
    """
    command_name = inspect.signature(pool.get_connection).parameters.get("command_name")
    if command_name is not None and command_name.default is inspect.Parameter.empty:
        return pool.get_connection("_")
    return pool.get_connection()


def tuple_to_list(x: Any) -> Any:
    if isinstance(x, (tuple, list)):
        return [tuple_to_list(x) for x in x]
    return x


def get_protocol_version(r: redis.Redis) -> int:
    return int(r.connection_pool.connection_kwargs.get("protocol", 2))


def convert_to_resp2(val: Any) -> Any:
    if isinstance(val, str):
        return val.encode()
    if isinstance(val, float):
        return Float.encode(val, humanfriendly=False)
    if isinstance(val, dict):
        result = list(itertools.chain(*val.items()))
        return [convert_to_resp2(item) for item in result]
    if isinstance(val, list):
        res = [convert_to_resp2(item) for item in val]
        return res
    if isinstance(val, tuple):
        res = tuple(convert_to_resp2(item) for item in val)
        return res
    return val


def resp_conversion(r: redis.Redis, val_resp3: Any, val_resp2: Any) -> Any:
    res = val_resp2 if get_protocol_version(r) == 2 else val_resp3
    return res


def resp_conversion_from_resp2(r: redis.Redis, val: Any) -> Any:
    return resp_conversion(r, tuple_to_list(val), val)


def key_val_dict(size=100):
    return {f"key:{i}".encode(): f"val:{i}".encode() for i in range(size)}


def raw_command(r: ClientType, *args):
    """Like execute_command, but does not do command-specific response parsing"""
    response_callbacks = r.response_callbacks
    try:
        r.response_callbacks = {}
        return r.execute_command(*args)
    finally:
        r.response_callbacks = response_callbacks


ALLOWED_CONDITIONS = {"eq", "gte", "lte", "lt", "gt", "ne"}


def run_test_if_lupa_installed():
    try:
        import lupa  # noqa: F401

        return pytest.mark.skipif(False, reason="lupa is installed")
    except ImportError:
        return pytest.mark.skipif(True, reason="lupa is not installed")


def run_test_if_redispy_ver(condition: str, ver: str):
    if condition not in ALLOWED_CONDITIONS:
        raise ValueError(f"condition {condition} is not in allowed conditions ({ALLOWED_CONDITIONS})")
    cond = False
    cond = cond or (condition == "eq" and REDIS_PY_VERSION == Version(ver))
    cond = cond or (condition == "gte" and REDIS_PY_VERSION >= Version(ver))
    cond = cond or (condition == "lte" and REDIS_PY_VERSION <= Version(ver))
    cond = cond or (condition == "lt" and REDIS_PY_VERSION < Version(ver))
    cond = cond or (condition == "gt" and REDIS_PY_VERSION > Version(ver))
    cond = cond or (condition == "ne" and REDIS_PY_VERSION != Version(ver))
    return pytest.mark.skipif(
        not cond, reason=f"Test is not applicable to redis-py {REDIS_PY_VERSION} ({condition}, {ver})"
    )


_lua_module = importlib.util.find_spec("lupa")
run_test_if_lupa = pytest.mark.skipif(_lua_module is None, reason="Test is only applicable if lupa is installed")


def redis_server_time(r: redis.Redis) -> datetime:
    seconds, milliseconds = r.time()
    timestamp = float(f"{seconds}.{milliseconds}")
    return datetime.fromtimestamp(timestamp)


def current_time() -> int:
    """Return current_time in ms"""
    return int(time.time() * 1000)


def far_future_expiry(server_type: str) -> int:
    """An absolute expiry timestamp (seconds) that the server under test will accept.

    Dragonfly refuses to store a deadline more than 2**28-1 seconds away, so it gets a
    nearer -- but still far future -- timestamp instead of the year-3021 one.
    """
    if server_type == "dragonfly":
        return int(time.time()) + 10_000_000
    return 33177117420


def empty_blocking_reply(r: redis.Redis, server_type: str) -> Any:
    """What a timed-out BLPOP/BRPOP/BZPOPMIN looks like on the server under test.

    Redis sends a null array, which RESP3 renders as nil. Dragonfly sends an empty array,
    so a RESP3 client sees `[]`. Under RESP2 both encode to `*-1` and read back as None.
    """
    if server_type == "dragonfly" and get_protocol_version(r) == 3:
        return []
    return None


def disable_xread_parsing(r: ClientType, server_type: str) -> bool:
    """Drop redis-py's XREAD callback when it cannot parse the reply of the server under test.

    A blocking XREAD woken by a new entry is answered by dragonfly with the RESP2-style
    array, where Redis sends a map; redis-py's RESP3 parser assumes the map. Returns whether
    the callback was dropped, i.e. whether XREAD now answers in the RESP2 shape.
    """
    if server_type != "dragonfly" or get_protocol_version(r) != 3:
        return False
    r.response_callbacks.pop("XREAD", None)
    return True


def json_legacy_reply(r: ClientType, server_type: str, value: Any) -> Any:
    """What a JSON command answers with for a legacy path (`.a`) on the server under test.

    RedisJSON sends the value itself. Dragonfly sends the one-element array it sends for the
    equivalent JSONPath, but only under RESP3; under RESP2 the two agree.
    """
    if server_type == "dragonfly" and get_protocol_version(r) == 3:
        return [value]
    return value


def json_legacy_value(r: ClientType, server_type: str, reply: Any) -> Any:
    """The value inside a legacy-path JSON reply, for tests that post-process it.

    The inverse of `json_legacy_reply`: it unwraps the one-element array dragonfly answers a
    legacy path with under RESP3, and leaves every other reply alone.
    """
    if server_type == "dragonfly" and get_protocol_version(r) == 3:
        assert isinstance(reply, list) and len(reply) == 1, reply
        return reply[0]
    return reply


def json_arrpop_reply(r: ClientType, server_type: str, value: Any) -> Any:
    """What JSON.ARRPOP answers with for a legacy path on the server under test.

    The reply is the JSON text of the popped element, which redis-py parses back into a value
    -- but not through the array dragonfly wraps it in under RESP3, where it stays text.
    """
    if server_type == "dragonfly" and get_protocol_version(r) == 3:
        return [json.dumps(value)]
    return value


def json_toggle_reply(r: ClientType, server_type: str, value: bool) -> Any:
    """What JSON.TOGGLE answers with for a legacy path on the server under test.

    Dragonfly answers with the JSON text of the new value, wrapped under RESP3 the way every
    legacy path is; redis-py parses the bare text back into a boolean, so only the wrapped
    reply differs from the boolean RedisJSON sends.
    """
    if server_type == "dragonfly" and get_protocol_version(r) == 3:
        return ["true" if value else "false"]
    return value


def json_type_reply(r: ClientType, server_type: str, types: list[Any]) -> Any:
    """What JSON.TYPE answers with for a JSONPath on the server under test.

    Under RESP3 RedisJSON wraps the whole list of matched types in one array, where dragonfly
    wraps each match in an array of its own. Under RESP2 neither wraps.
    """
    if get_protocol_version(r) == 2:
        return types
    return [[item] for item in types] if server_type == "dragonfly" else [types]


def json_number_reply(r: ClientType, server_type: str, value: float) -> Any:
    """What JSON.NUMINCRBY / JSON.NUMMULTBY answers with for a legacy path.

    RedisJSON wraps the new value in an array under RESP3; dragonfly never does.
    """
    if server_type == "dragonfly":
        return value
    return resp_conversion(r, [value], value)


def assert_empty_stream_read(r: redis.Redis, server_type: str, *raw_args: Any) -> None:
    """Assert that an XREAD/XREADGROUP matched nothing.

    Redis answers with an empty map under RESP3 and an empty array under RESP2. Dragonfly
    answers with an empty array in both, and redis-py's RESP3 parser cannot consume that,
    so on dragonfly the raw reply is checked instead of the parsed one.
    """
    if server_type == "dragonfly" and get_protocol_version(r) == 3:
        assert raw_command(r, *raw_args) == []
        return
    method, args = raw_args[0], raw_args[1:]
    assert r.execute_command(method, *args) == resp_conversion(r, {}, [])
