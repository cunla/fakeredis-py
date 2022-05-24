import redis
import packaging.version

# aioredis was integrated into redis in version 4.2.0 as redis.asyncio
if packaging.version.Version(redis.__version__) >= packaging.version.Version("4.2.0"):
    import redis.asyncio as aioredis
    from ._aioredis2 import FakeConnection, FakeRedis  # noqa: F401
else:
    try:
        import aioredis
    except ImportError as e:
        raise ImportError("aioredis is required for redis-py below 4.2.0") from e

    if packaging.version.Version(aioredis.__version__) >= packaging.version.Version('2.0.0a1'):
        from ._aioredis2 import FakeConnection, FakeRedis  # noqa: F401
    else:
        from ._aioredis1 import (  # noqa: F401
            FakeConnectionsPool, create_connection, create_redis, create_pool, create_redis_pool
        )
