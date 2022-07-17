import pytest
import pytest_asyncio
import redis
from packaging.version import Version

import fakeredis


@pytest_asyncio.fixture(scope="session")
def is_redis_running():
    try:
        r = redis.StrictRedis('localhost', port=6379)
        r.ping()
        return True
    except redis.ConnectionError:
        return False
    finally:
        if hasattr(r, 'close'):
            r.close()  # Absent in older versions of redis-py


@pytest_asyncio.fixture
def fake_server(request):
    server = fakeredis.FakeServer()
    server.connected = request.node.get_closest_marker('disconnected') is None
    return server


@pytest_asyncio.fixture
def r(request, create_redis):
    rconn = create_redis(db=0)
    connected = request.node.get_closest_marker('disconnected') is None
    if connected:
        rconn.flushall()
    yield rconn
    if connected:
        rconn.flushall()
    if hasattr(r, 'close'):
        rconn.close()  # Older versions of redis-py don't have this method


@pytest_asyncio.fixture(
    params=[
        pytest.param('StrictRedis', marks=pytest.mark.real),
        pytest.param('FakeStrictRedis', marks=pytest.mark.fake),
    ]
)
def create_redis(request):
    name = request.param
    if not name.startswith('Fake') and not request.getfixturevalue('is_redis_running'):
        pytest.skip('Redis is not running')
    decode_responses = request.node.get_closest_marker('decode_responses') is not None

    def factory(db=0):
        if name.startswith('Fake'):
            fake_server = request.getfixturevalue('fake_server')
            cls = getattr(fakeredis, name)
            return cls(db=db, decode_responses=decode_responses, server=fake_server)
        else:
            cls = getattr(redis, name)
            conn = cls('localhost', port=6379, db=db, decode_responses=decode_responses)
            server_version = conn.info()['redis_version']
            min_server_marker = request.node.get_closest_marker('min_server')
            if min_server_marker is not None:
                min_version = Version(min_server_marker.args[0])
                if Version(server_version) < min_version:
                    pytest.skip(
                        'Redis server {} or more required but {} found'.format(min_version, server_version)
                    )
            max_server_marker = request.node.get_closest_marker('max_server')
            if max_server_marker is not None:
                max_server = Version(max_server_marker.args[0])
                if Version(server_version) > max_server:
                    pytest.skip(
                        'Redis server {} or less required but {} found'.format(max_server, server_version)
                    )
            return conn

    return factory
