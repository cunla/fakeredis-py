import importlib.util
import itertools
import time
from datetime import datetime
from typing import Any

import pytest
import redis
from packaging.version import Version

from fakeredis._commands import Float

REDIS_PY_VERSION = Version(redis.__version__)


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


def raw_command(r: redis.Redis, *args):
    """Like execute_command, but does not do command-specific response parsing"""
    response_callbacks = r.response_callbacks
    try:
        r.response_callbacks = {}
        return r.execute_command(*args)
    finally:
        r.response_callbacks = response_callbacks


ALLOWED_CONDITIONS = {"eq", "gte", "lte", "lt", "gt", "ne"}


def run_test_if_redispy_ver(condition: str, ver: str):
    if condition not in ALLOWED_CONDITIONS:
        raise ValueError(f"condition {condition} is not in allowed conditions ({ALLOWED_CONDITIONS})")
    cond = False
    cond = cond or condition == "eq" and REDIS_PY_VERSION == Version(ver)
    cond = cond or condition == "gte" and REDIS_PY_VERSION >= Version(ver)
    cond = cond or condition == "lte" and REDIS_PY_VERSION <= Version(ver)
    cond = cond or condition == "lt" and REDIS_PY_VERSION < Version(ver)
    cond = cond or condition == "gt" and REDIS_PY_VERSION > Version(ver)
    cond = cond or condition == "ne" and REDIS_PY_VERSION != Version(ver)
    return pytest.mark.skipif(
        not cond, reason=f"Test is not applicable to redis-py {REDIS_PY_VERSION} ({condition}, {ver})"
    )


_lua_module = importlib.util.find_spec("lupa")
run_test_if_lupa = pytest.mark.skipif(_lua_module is None, reason="Test is only applicable if lupa is installed")

fake_only = pytest.mark.parametrize(
    "create_connection", [pytest.param("FakeStrictRedis2", marks=pytest.mark.fake)], indirect=True
)


def redis_server_time(r: redis.Redis) -> datetime:
    seconds, milliseconds = r.time()
    timestamp = float(f"{seconds}.{milliseconds}")
    return datetime.fromtimestamp(timestamp)


def current_time() -> int:
    """Return current_time in ms"""
    return int(time.time() * 1000)
