from typing import Callable, Union

import pytest
import pytest_asyncio
import redis

import fakeredis
from fakeredis._server import _create_version


@pytest_asyncio.fixture(scope="session")
def real_redis_version() -> Union[None, str]:
    """Returns server's version or None if server is not running"""
    client = None
    try:
        client = redis.StrictRedis('localhost', port=6380, db=2)
        server_version = client.info()['redis_version']
        return server_version
    except redis.ConnectionError:
        return None
    finally:
        if hasattr(client, 'close'):
            client.close()  # Absent in older versions of redis-py


@pytest_asyncio.fixture(name='fake_server')
def _fake_server(request):
    min_server_marker = request.node.get_closest_marker('min_server')
    server_version = min_server_marker.args[0] if min_server_marker else '6.2'
    server = fakeredis.FakeServer(version=server_version)
    server.connected = request.node.get_closest_marker('disconnected') is None
    return server


@pytest_asyncio.fixture
def r(request, create_redis) -> redis.Redis:
    rconn = create_redis(db=2)
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
        return (0,) if marker_name == 'min_server' else (100,)
    return _create_version(marker_value.args[0])


@pytest_asyncio.fixture(
    name='create_redis',
    params=[
        pytest.param('StrictRedis', marks=pytest.mark.real),
        pytest.param('FakeStrictRedis', marks=pytest.mark.fake),
    ]
)
def _create_redis(request) -> Callable[[int], redis.Redis]:
    cls_name = request.param
    server_version = request.getfixturevalue('real_redis_version')
    if not cls_name.startswith('Fake') and not server_version:
        pytest.skip('Redis is not running')
    server_version = _create_version(server_version) or (6,)
    min_server = _marker_version_value(request, 'min_server')
    max_server = _marker_version_value(request, 'max_server')
    if server_version < min_server:
        pytest.skip(f'Redis server {min_server} or more required but {server_version} found')
    if server_version > max_server:
        pytest.skip(f'Redis server {max_server} or less required but {server_version} found')
    decode_responses = request.node.get_closest_marker('decode_responses') is not None

    def factory(db=2):
        if cls_name.startswith('Fake'):
            fake_server = request.getfixturevalue('fake_server')
            cls = getattr(fakeredis, cls_name)
            return cls(db=db, decode_responses=decode_responses, server=fake_server)
        # Real
        cls = getattr(redis, cls_name)
        return cls('localhost', port=6380, db=db, decode_responses=decode_responses)

    return factory
