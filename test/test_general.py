import pytest
import redis

from test.testtools import raw_command


def test_asyncioio_is_used():
    """Redis 4.2+ has support for asyncio and should be preferred over aioredis"""
    from fakeredis import aioredis
    assert not hasattr(aioredis, "__version__")


def test_unknown_command(r: redis.Redis):
    with pytest.raises(redis.ResponseError):
        raw_command(r, '0 3 3')


def test_new_server_when_no_params():
    from fakeredis import FakeRedis

    fake_redis_1 = FakeRedis()
    fake_redis_2 = FakeRedis()

    fake_redis_1.set("foo", "bar")

    assert fake_redis_2.get("foo") is None
