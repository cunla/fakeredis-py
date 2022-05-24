import pytest
import redis
import redis.client
from packaging.version import Version

REDIS_VERSION = Version(redis.__version__)

below_redis_4_2 = pytest.mark.skipif(
    REDIS_VERSION >= Version("4.2.0"),
    reason="Test is only applicable to redis-py below 4.2.0",
)
redis4_2_and_above = pytest.mark.skipif(
    REDIS_VERSION < Version("4.2.0"),
    reason="Test is only applicable to redis-py 4.2.0 and above",
)
import importlib

aioredis_module = importlib.util.find_spec("aioredis")
without_aioredis = pytest.mark.skipif(
    aioredis_module is not None,
    reason="Test is only applicable if aioredis is not installed",
)


@redis4_2_and_above
@without_aioredis
def test_fakeredis_aioredis_uses_redis_asyncio():
    import fakeredis.aioredis as aioredis

    assert not hasattr(aioredis, "__version__")


@below_redis_4_2
@without_aioredis
def test_fakeredis_aioredis_raises_if_missing_aioredis():
    with pytest.raises(
        ImportError, match="aioredis is required for redis-py below 4.2.0"
    ):
        import fakeredis.aioredis as aioredis
