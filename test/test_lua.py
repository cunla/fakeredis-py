"""
Tests will run only if module lupa is installed.
"""
import pytest
import pytest_asyncio
import redis
import redis.client
from packaging.version import Version
import fakeredis

lupa = pytest.importorskip("lupa")

REDIS_VERSION = Version(redis.__version__)

redis_below_v3 = pytest.mark.skipif(REDIS_VERSION >= Version('3'), reason="Test is only applicable to redis-py 2.x")
redis3_and_above = pytest.mark.skipif(
    REDIS_VERSION < Version('3'),
    reason="Test is only applicable to redis-py 3.x and above"
)
redis4_and_above = pytest.mark.skipif(
    REDIS_VERSION < Version('4.1.2'),
    reason="Test is only applicable to redis-py 4.1.2 and above"
)
fake_only = pytest.mark.parametrize(
    'create_redis',
    [pytest.param('FakeStrictRedis', marks=pytest.mark.fake)],
    indirect=True
)


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
        pytest.param('FakeStrictRedis', marks=pytest.mark.fake)
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
            min_server_marker = request.node.get_closest_marker('min_server')
            if min_server_marker is not None:
                server_version = conn.info()['redis_version']
                min_version = Version(min_server_marker.args[0])
                if Version(server_version) < min_version:
                    pytest.skip(
                        'Redis server {} required but {} found'.format(min_version, server_version)
                    )
            return conn

    return factory


def test_eval_blpop(r):
    r.rpush('foo', 'bar')
    with pytest.raises(redis.ResponseError, match='not allowed from scripts'):
        r.eval('return redis.pcall("BLPOP", KEYS[1], 1)', 1, 'foo')
