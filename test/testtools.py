import importlib

import pytest
import redis
from packaging.version import Version

REDIS_VERSION = Version(redis.__version__)


def raw_command(r, *args):
    """Like execute_command, but does not do command-specific response parsing"""
    response_callbacks = r.response_callbacks
    try:
        r.response_callbacks = {}
        return r.execute_command(*args)
    finally:
        r.response_callbacks = response_callbacks


# Wrap some redis commands to abstract differences between redis-py 2 and 3.
def zadd(r, key, d, *args, **kwargs):
    if REDIS_VERSION >= Version('3'):
        return r.zadd(key, d, *args, **kwargs)
    else:
        return r.zadd(key, **d)


ALLOWED_CONDITIONS = {'above', 'below'}


def run_test_if_redispy_ver(condition: str, ver: str):
    if condition not in ALLOWED_CONDITIONS:
        raise ValueError(f'condition {condition} is not in allowed conditions ({ALLOWED_CONDITIONS})')
    cond = REDIS_VERSION >= Version(ver) if condition == 'above' else REDIS_VERSION <= Version(ver)
    return pytest.mark.skipif(
        not cond,
        reason=f"Test is not applicable to redis-py {REDIS_VERSION} ({condition}, {ver})"
    )


_lua_module = importlib.util.find_spec("lupa")
run_test_if_lupa = pytest.mark.skipif(
    _lua_module is None,
    reason="Test is only applicable if lupa is installed"
)

fake_only = pytest.mark.parametrize(
    'create_redis',
    [pytest.param('FakeStrictRedis', marks=pytest.mark.fake)],
    indirect=True
)
