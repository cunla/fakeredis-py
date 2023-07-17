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

def test_new_server_with_positional_args():
    from fakeredis import FakeRedis

    # same host, default port and db index
    fake_redis_1 = FakeRedis('localhost')
    fake_redis_2 = FakeRedis('localhost')

    fake_redis_1.set("foo", "bar")

    assert fake_redis_2.get("foo") == b'bar'

    # same host and port
    fake_redis_1 = FakeRedis('localhost', 6000)
    fake_redis_2 = FakeRedis('localhost', 6000)

    fake_redis_1.set("foo", "bar")

    assert fake_redis_2.get("foo") == b'bar'

    # same connection parameters, but different db index
    fake_redis_1 = FakeRedis('localhost', 6000, 0)
    fake_redis_2 = FakeRedis('localhost', 6000, 1)

    fake_redis_1.set("foo", "bar")

    assert fake_redis_2.get("foo") is None

    # mix of positional arguments and keyword args
    fake_redis_1 = FakeRedis('localhost', port=6000, db=0)
    fake_redis_2 = FakeRedis('localhost', port=6000, db=1)

    fake_redis_1.set("foo", "bar")

    assert fake_redis_2.get("foo") is None
