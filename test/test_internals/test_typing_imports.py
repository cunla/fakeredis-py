import importlib
import sys

import redis


def test_typing_imports_without_preimported_redis_asyncio(monkeypatch):
    """Regression test for #493.

    redis-py < 5 does not bind the ``redis.asyncio`` submodule on a plain
    ``import redis``. ``fakeredis._typing`` references ``redis.asyncio.Redis``
    at module level, so without an explicit ``import redis.asyncio`` importing
    fakeredis raised ``AttributeError: module 'redis' has no attribute
    'asyncio'`` at import time. Here we reproduce that state regardless of the
    installed redis-py version by removing the cached submodule, then check
    that re-importing ``_typing`` succeeds.
    """
    monkeypatch.delattr(redis, "asyncio", raising=False)
    monkeypatch.delitem(sys.modules, "redis.asyncio", raising=False)
    monkeypatch.delitem(sys.modules, "fakeredis._typing", raising=False)

    module = importlib.import_module("fakeredis._typing")

    assert module.AsyncClientType is not None
