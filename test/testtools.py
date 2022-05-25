import importlib

import pytest
import redis
from packaging.version import Version

REDIS_VERSION = Version(redis.__version__)

# Wrap some redis commands to abstract differences between redis-py 2 and 3.
def zadd(r, key, d, *args, **kwargs):
    if REDIS_VERSION >= Version('3'):
        return r.zadd(key, d, *args, **kwargs)
    else:
        return r.zadd(key, **d)


def run_test_if_redis_ver(condition: str, ver: str):
    cond = REDIS_VERSION < Version(ver) if condition == 'above' else REDIS_VERSION > Version(ver)
    return pytest.mark.skipif(
        cond,
        reason=f"Test is only applicable to redis-py {ver} and above"
    )


fake_only = pytest.mark.parametrize(
    'create_redis',
    [pytest.param('FakeStrictRedis', marks=pytest.mark.fake)],
    indirect=True
)

_lua_module = importlib.util.find_spec("lupa")
run_test_if_lupa = pytest.mark.skipif(
    _lua_module is None,
    reason="Test is only applicable if lupa is installed"
)

_aioredis_module = importlib.util.find_spec("aioredis")
run_test_if_no_aioredis = pytest.mark.skipif(
    _aioredis_module is not None,
    reason="Test is only applicable if aioredis is not installed",
)
