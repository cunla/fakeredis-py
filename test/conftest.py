import sys
from typing import Callable

import pytest
import pytest_asyncio
import redis
from packaging.version import Version

import fakeredis


@pytest_asyncio.fixture(scope="session")
def is_redis_running():
    client = None
    try:
        client = redis.StrictRedis('localhost', port=6379)
        client.ping()
        return True
    except redis.ConnectionError:
        return False
    finally:
        if hasattr(client, 'close'):
            client.close()  # Absent in older versions of redis-py


@pytest_asyncio.fixture(name='fake_server')
def _fake_server(request):
    min_server_marker = request.node.get_closest_marker('min_server')
    server_version = 6
    if min_server_marker and min_server_marker.args[0].startswith('7'):
        server_version = 7
    server = fakeredis.FakeServer(version=server_version)
    server.connected = request.node.get_closest_marker('disconnected') is None
    return server


@pytest_asyncio.fixture
def r(request, create_redis) -> redis.Redis:
    rconn = create_redis(db=0)
    connected = request.node.get_closest_marker('disconnected') is None
    if connected:
        rconn.flushall()
    yield rconn
    if connected:
        rconn.flushall()
    if hasattr(r, 'close'):
        rconn.close()  # Older versions of redis-py don't have this method


def _marker_version_value(request, marker_name: str):
    marker_value = request.node.get_closest_marker(marker_name)
    if marker_value is None:
        val = str(sys.maxsize if marker_name == 'min_server' else 0)
        return None, Version(val)
    return marker_value, Version(marker_value.args[0])


@pytest_asyncio.fixture(
    name='create_redis',
    params=[
        pytest.param('StrictRedis', marks=pytest.mark.real),
        pytest.param('FakeStrictRedis', marks=pytest.mark.fake),
    ]
)
def _create_redis(request) -> Callable[[int], redis.Redis]:
    cls_name = request.param
    min_version, min_server_marker = _marker_version_value(request, 'min_server')
    max_version, max_server_marker = _marker_version_value(request, 'max_server')
    if (not cls_name.startswith('Fake')
            and not request.getfixturevalue('is_redis_running')):
        pytest.skip('Redis is not running')
    decode_responses = request.node.get_closest_marker('decode_responses') is not None

    def factory(db=0):
        if cls_name.startswith('Fake'):
            fake_server = request.getfixturevalue('fake_server')
            cls = getattr(fakeredis, cls_name)
            return cls(db=db, decode_responses=decode_responses, server=fake_server)

        # Real
        cls = getattr(redis, cls_name)
        conn = cls('localhost', port=6379, db=db, decode_responses=decode_responses)
        server_version = conn.info()['redis_version']
        if Version(server_version) < (min_server_marker or sys.maxsize):
            pytest.skip(f'Redis server {min_version} or more required but {server_version} found')
        if Version(server_version) > (max_server_marker or 0):
            pytest.skip(f'Redis server {max_version} or less required but {server_version} found')
        return conn

    return factory
