from redis import Redis


def connect_redis(redis_host: str, redis_port: int) -> Redis:
    redis_con = Redis(redis_host, redis_port)
    return redis_con


def bar(zip, zap):
    redis_con = connect_redis('localhost', 6379)


from unittest.mock import patch
from fakeredis import FakeRedis


def test_bar():
    # Mock Redis connection
    with patch('test_mock.Redis', FakeRedis):
        # Call function
        bar(zip, [])
