import asyncio
import re

import async_timeout
import pytest
import pytest_asyncio
import redis
import redis.asyncio
from packaging.version import Version

from fakeredis import FakeServer, aioredis
from test import testtools

pytestmark = [
]
fake_only = pytest.mark.parametrize(
    'req_aioredis2',
    [pytest.param('fake', marks=pytest.mark.fake)],
    indirect=True
)
pytestmark.extend([
    pytest.mark.asyncio,
])
server_version = None


@pytest_asyncio.fixture(
    params=[
        pytest.param('fake', marks=pytest.mark.fake),
        pytest.param('real', marks=pytest.mark.real)
    ]
)
async def req_aioredis2(request):
    global server_version
    if request.param == 'fake':
        fake_server = request.getfixturevalue('fake_server')
        ret = aioredis.FakeRedis(server=fake_server)
    else:
        if not request.getfixturevalue('is_redis_running'):
            pytest.skip('Redis is not running')
        ret = redis.asyncio.Redis()
        server_version = server_version or (await ret.info())['redis_version']
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

        fake_server = None
    if not fake_server or fake_server.connected:
        await ret.flushall()

    yield ret

    if not fake_server or fake_server.connected:
        await ret.flushall()
    await ret.connection_pool.disconnect()


@pytest_asyncio.fixture
async def conn(req_aioredis2):
    """A single connection, rather than a pool."""
    async with req_aioredis2.client() as conn:
        yield conn


async def test_ping(req_aioredis2):
    pong = await req_aioredis2.ping()
    assert pong is True


async def test_types(req_aioredis2):
    await req_aioredis2.hset('hash', mapping={'key1': 'value1', 'key2': 'value2', 'key3': 123})
    result = await req_aioredis2.hgetall('hash')
    assert result == {
        b'key1': b'value1',
        b'key2': b'value2',
        b'key3': b'123'
    }


async def test_transaction(req_aioredis2):
    async with req_aioredis2.pipeline(transaction=True) as tr:
        tr.set('key1', 'value1')
        tr.set('key2', 'value2')
        ok1, ok2 = await tr.execute()
    assert ok1
    assert ok2
    result = await req_aioredis2.get('key1')
    assert result == b'value1'


async def test_transaction_fail(req_aioredis2):
    await req_aioredis2.set('foo', '1')
    async with req_aioredis2.pipeline(transaction=True) as tr:
        await tr.watch('foo')
        await req_aioredis2.set('foo', '2')  # Different connection
        tr.multi()
        tr.get('foo')
        with pytest.raises(redis.asyncio.WatchError):
            await tr.execute()


async def test_pubsub(req_aioredis2, event_loop):
    queue = asyncio.Queue()

    async def reader(ps):
        while True:
            message = await ps.get_message(ignore_subscribe_messages=True, timeout=5)
            if message is not None:
                if message.get('data') == b'stop':
                    break
                queue.put_nowait(message)

    async with async_timeout.timeout(5), req_aioredis2.pubsub() as ps:
        await ps.subscribe('channel')
        task = event_loop.create_task(reader(ps))
        await req_aioredis2.publish('channel', 'message1')
        await req_aioredis2.publish('channel', 'message2')
        result1 = await queue.get()
        result2 = await queue.get()
        assert result1 == {
            'channel': b'channel',
            'pattern': None,
            'type': 'message',
            'data': b'message1'
        }
        assert result2 == {
            'channel': b'channel',
            'pattern': None,
            'type': 'message',
            'data': b'message2'
        }
        await req_aioredis2.publish('channel', 'stop')
        await task


@pytest.mark.slow
async def test_pubsub_timeout(req_aioredis2):
    async with req_aioredis2.pubsub() as ps:
        await ps.subscribe('channel')
        await ps.get_message(timeout=0.5)  # Subscription message
        message = await ps.get_message(timeout=0.5)
        assert message is None


@pytest.mark.slow
async def test_pubsub_disconnect(req_aioredis2):
    async with req_aioredis2.pubsub() as ps:
        await ps.subscribe('channel')
        await ps.connection.disconnect()
        message = await ps.get_message(timeout=0.5)  # Subscription message
        assert message is not None
        message = await ps.get_message(timeout=0.5)
        assert message is None


async def test_blocking_ready(req_aioredis2, conn):
    """Blocking command which does not need to block."""
    await req_aioredis2.rpush('list', 'x')
    result = await conn.blpop('list', timeout=1)
    assert result == (b'list', b'x')


@pytest.mark.slow
async def test_blocking_timeout(conn):
    """Blocking command that times out without completing."""
    result = await conn.blpop('missing', timeout=1)
    assert result is None


@pytest.mark.slow
async def test_blocking_unblock(req_aioredis2, conn, event_loop):
    """Blocking command that gets unblocked after some time."""

    async def unblock():
        await asyncio.sleep(0.1)
        await req_aioredis2.rpush('list', 'y')

    task = event_loop.create_task(unblock())
    result = await conn.blpop('list', timeout=1)
    assert result == (b'list', b'y')
    await task


async def test_wrongtype_error(req_aioredis2):
    await req_aioredis2.set('foo', 'bar')
    with pytest.raises(redis.asyncio.ResponseError, match='^WRONGTYPE'):
        await req_aioredis2.rpush('foo', 'baz')


async def test_syntax_error(req_aioredis2):
    with pytest.raises(redis.asyncio.ResponseError,
                       match="^wrong number of arguments for 'get' command$"):
        await req_aioredis2.execute_command('get')


async def test_no_script_error(req_aioredis2):
    with pytest.raises(redis.exceptions.NoScriptError):
        await req_aioredis2.evalsha('0123456789abcdef0123456789abcdef', 0)


@testtools.run_test_if_lupa
class TestScripts:

    @pytest.mark.max_server('6.2.7')
    async def test_failed_script_error6(self, req_aioredis2):
        await req_aioredis2.set('foo', 'bar')
        with pytest.raises(redis.asyncio.ResponseError, match='^Error running script'):
            await req_aioredis2.eval('return redis.call("ZCOUNT", KEYS[1])', 1, 'foo')

    @pytest.mark.min_server('7')
    async def test_failed_script_error7(self, req_aioredis2):
        await req_aioredis2.set('foo', 'bar')
        with pytest.raises(redis.asyncio.ResponseError,
                           match='^Wrong number of args calling Redis command from script'):
            await req_aioredis2.eval('return redis.call("ZCOUNT", KEYS[1])', 1, 'foo')


@fake_only
async def test_repr(req_aioredis2):
    assert re.fullmatch(
        r'ConnectionPool<FakeConnection<server=<fakeredis._server.FakeServer object at .*>,db=0>>',
        repr(req_aioredis2.connection_pool)
    )


@fake_only
@pytest.mark.disconnected
async def test_not_connected(req_aioredis2):
    with pytest.raises(redis.asyncio.ConnectionError):
        await req_aioredis2.ping()


@fake_only
async def test_disconnect_server(req_aioredis2, fake_server):
    await req_aioredis2.ping()
    fake_server.connected = False
    with pytest.raises(redis.asyncio.ConnectionError):
        await req_aioredis2.ping()
    fake_server.connected = True


@pytest.mark.fake
async def test_from_url():
    r0 = aioredis.FakeRedis.from_url('redis://localhost?db=0')
    r1 = aioredis.FakeRedis.from_url('redis://localhost?db=1')
    # Check that they are indeed different databases
    await r0.set('foo', 'a')
    await r1.set('foo', 'b')
    assert await r0.get('foo') == b'a'
    assert await r1.get('foo') == b'b'
    await r0.connection_pool.disconnect()
    await r1.connection_pool.disconnect()


@fake_only
async def test_from_url_with_server(req_aioredis2, fake_server):
    r2 = aioredis.FakeRedis.from_url('redis://localhost', server=fake_server)
    await req_aioredis2.set('foo', 'bar')
    assert await r2.get('foo') == b'bar'
    await r2.connection_pool.disconnect()


@pytest.mark.fake
async def test_without_server():
    r = aioredis.FakeRedis()
    assert await r.ping()


@pytest.mark.fake
async def test_without_server_disconnected():
    r = aioredis.FakeRedis(connected=False)
    with pytest.raises(redis.asyncio.ConnectionError):
        await r.ping()


@pytest.mark.fake
async def test_async():
    # arrange
    cache = aioredis.FakeRedis()
    # act
    await cache.set("fakeredis", "plz")
    x = await cache.get("fakeredis")
    # assert
    assert x == b"plz"


@testtools.run_test_if_redispy_ver('above', '4.4.0rc2')
@pytest.mark.parametrize('nowait', [False, True])
@pytest.mark.fake
async def test_connection_disconnect(nowait):
    server = FakeServer()
    r = aioredis.FakeRedis(server=server)
    conn = await r.connection_pool.get_connection("_")
    assert conn is not None

    await conn.disconnect(nowait=nowait)

    assert conn._sock is None
