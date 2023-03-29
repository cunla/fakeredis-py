import redis
from unittest.mock import patch

from fakeredis import FakeRedis


def test_mock():
    # Mock Redis connection
    def bar(redis_host: str, redis_port: int):
        redis_con = redis.Redis(redis_host, redis_port)
        pass

    with patch('redis.Redis', FakeRedis):
        # Call function
        bar('localhost', 6000)

        # Related to #36 - this should fail if mocking Redis does not work
