import redis


def connect_redis_conn(redis_host: str, redis_port: int) -> redis.Redis:
    redis_con = redis.Redis(redis_host, redis_port)
    return redis_con


def bar():
    redis_con = connect_redis_conn('localhost', 6000)
    pass


from unittest.mock import patch
from fakeredis import FakeRedis


def test_bar():
    # Mock Redis connection
    with patch('redis.Redis', FakeRedis):
        # Call function
        bar()

        # Related to #36 - this should fail if mocking Redis does not work
