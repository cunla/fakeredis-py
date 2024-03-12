import asyncio
import re
import sys

from fakeredis._server import _create_version
from test.conftest import _marker_version_value

if sys.version_info >= (3, 11):
    from asyncio import timeout as async_timeout
else:
    from async_timeout import timeout as async_timeout
import pytest
import pytest_asyncio
import redis
import redis.asyncio

from fakeredis import FakeServer, aioredis, FakeAsyncRedis, FakeStrictRedis
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


@pytest_asyncio.fixture(
    name='req_aioredis2',
    params=[
        pytest.param('fake', marks=pytest.mark.fake),
        pytest.param('real', marks=pytest.mark.real)
    ]
)
async def _req_aioredis2(request) -> redis.asyncio.Redis:
    server_version = request.getfixturevalue('real_redis_version')
    if request.param != 'fake' and not server_version:
        pytest.skip('Redis is not running')
    server_version = _create_version(server_version) or (6,)
    min_server_marker = _marker_version_value(request, 'min_server')
    max_server_marker = _marker_version_value(request, 'max_server')
    if server_version < min_server_marker:
        pytest.skip(f'Redis server {min_server_marker} or more required but {server_version} found')
    if server_version > max_server_marker:
        pytest.skip(f'Redis server {max_server_marker} or less required but {server_version} found')
    if request.param == 'fake':
        fake_server = request.getfixturevalue('fake_server')
        ret = aioredis.FakeRedis(server=fake_server)
    else:
        ret = redis.asyncio.Redis(host='localhost', port=6380, db=2)
        fake_server = None
    if not fake_server or fake_server.connected:
        await ret.flushall()

    yield ret

    if not fake_server or fake_server.connected:
        await ret.flushall()
    await ret.connection_pool.disconnect()


@pytest_asyncio.fixture
async def conn(req_aioredis2: redis.asyncio.Redis):
    """A single connection, rather than a pool."""
    async with req_aioredis2.client() as conn:
        yield conn


async def test_ping(req_aioredis2: redis.asyncio.Redis):
    pong = await req_aioredis2.ping()
    assert pong is True


async def test_types(req_aioredis2: redis.asyncio.Redis):
    await req_aioredis2.hset('hash', mapping={'key1': 'value1', 'key2': 'value2', 'key3': 123})
    result = await req_aioredis2.hgetall('hash')
    assert result == {
        b'key1': b'value1',
        b'key2': b'value2',
        b'key3': b'123'
    }


async def test_transaction(req_aioredis2: redis.asyncio.Redis):
    async with req_aioredis2.pipeline(transaction=True) as tr:
        tr.set('key1', 'value1')
        tr.set('key2', 'value2')
        ok1, ok2 = await tr.execute()
    assert ok1
    assert ok2
    result = await req_aioredis2.get('key1')
    assert result == b'value1'


async def test_transaction_fail(req_aioredis2: redis.asyncio.Redis):
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

    async with async_timeout(5), req_aioredis2.pubsub() as ps:
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
async def test_pubsub_timeout(req_aioredis2: redis.asyncio.Redis):
    async with req_aioredis2.pubsub() as ps:
        await ps.subscribe('channel')
        await ps.get_message(timeout=0.5)  # Subscription message
        message = await ps.get_message(timeout=0.5)
        assert message is None


@pytest.mark.slow
async def test_pubsub_disconnect(req_aioredis2: redis.asyncio.Redis):
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


async def test_wrongtype_error(req_aioredis2: redis.asyncio.Redis):
    await req_aioredis2.set('foo', 'bar')
    with pytest.raises(redis.asyncio.ResponseError, match='^WRONGTYPE'):
        await req_aioredis2.rpush('foo', 'baz')


async def test_syntax_error(req_aioredis2: redis.asyncio.Redis):
    with pytest.raises(redis.asyncio.ResponseError,
                       match="^wrong number of arguments for 'get' command$"):
        await req_aioredis2.execute_command('get')


@testtools.run_test_if_lupa
class TestScripts:
    async def test_no_script_error(self, req_aioredis2: redis.asyncio.Redis):
        with pytest.raises(redis.exceptions.NoScriptError):
            await req_aioredis2.evalsha('0123456789abcdef0123456789abcdef', 0)

    @pytest.mark.max_server('6.2.7')
    async def test_failed_script_error6(self, req_aioredis2):
        await req_aioredis2.set('foo', 'bar')
        with pytest.raises(redis.asyncio.ResponseError, match='^Error running script'):
            await req_aioredis2.eval('return redis.call("ZCOUNT", KEYS[1])', 1, 'foo')

    @pytest.mark.min_server('7')
    async def test_failed_script_error7(self, req_aioredis2):
        await req_aioredis2.set('foo', 'bar')
        with pytest.raises(redis.asyncio.ResponseError):
            await req_aioredis2.eval('return redis.call("ZCOUNT", KEYS[1])', 1, 'foo')


@fake_only
@testtools.run_test_if_redispy_ver('lt', '5.1.0b1')
async def test_repr_redis_until_51(req_aioredis2: redis.asyncio.Redis):
    assert re.fullmatch(
        r'ConnectionPool<FakeConnection<server=<fakeredis._server.FakeServer object at .*>,db=0>>',
        repr(req_aioredis2.connection_pool)
    )


@testtools.run_test_if_redispy_ver('gte', '5.1')
async def test_repr_redis_51(req_aioredis2: redis.asyncio.Redis):
    assert re.fullmatch(
        r'<redis.asyncio.connection.ConnectionPool('
        r'<fakeredis.aioredis.FakeConnection(server=<fakeredis._server.FakeServer object at .*>,db=0)>)>',
        repr(req_aioredis2.connection_pool)
    )


@fake_only
@pytest.mark.disconnected
async def test_not_connected(req_aioredis2: redis.asyncio.Redis):
    with pytest.raises(redis.asyncio.ConnectionError):
        await req_aioredis2.ping()


@fake_only
async def test_disconnect_server(req_aioredis2, fake_server):
    await req_aioredis2.ping()
    fake_server.connected = False
    with pytest.raises(redis.asyncio.ConnectionError):
        await req_aioredis2.ping()
    fake_server.connected = True


async def test_type(req_aioredis2: redis.asyncio.Redis):
    await req_aioredis2.set('string_key', "value")
    await req_aioredis2.lpush("list_key", "value")
    await req_aioredis2.sadd("set_key", "value")
    await req_aioredis2.zadd("zset_key", {"value": 1})
    await req_aioredis2.hset('hset_key', 'key', 'value')

    assert b'string' == await req_aioredis2.type('string_key')  # noqa: E721
    assert b'list' == await req_aioredis2.type('list_key')  # noqa: E721
    assert b'set' == await req_aioredis2.type('set_key')  # noqa: E721
    assert b'zset' == await req_aioredis2.type('zset_key')  # noqa: E721
    assert b'hash' == await req_aioredis2.type('hset_key')  # noqa: E721
    assert b'none' == await req_aioredis2.type('none_key')  # noqa: E721


async def test_xdel(req_aioredis2: redis.asyncio.Redis):
    stream = "stream"

    # deleting from an empty stream doesn't do anything
    assert await req_aioredis2.xdel(stream, 1) == 0

    m1 = await req_aioredis2.xadd(stream, {"foo": "bar"})
    m2 = await req_aioredis2.xadd(stream, {"foo": "bar"})
    m3 = await req_aioredis2.xadd(stream, {"foo": "bar"})

    # xdel returns the number of deleted elements
    assert await req_aioredis2.xdel(stream, m1) == 1
    assert await req_aioredis2.xdel(stream, m2, m3) == 2


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


@pytest.mark.fake
async def test_from_url_with_version():
    r0 = aioredis.FakeRedis.from_url('redis://localhost?db=0', version=(6,))
    r1 = aioredis.FakeRedis.from_url('redis://localhost?db=1', version=(6,))
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


@testtools.run_test_if_redispy_ver('gte', '4.4.0')
@pytest.mark.parametrize('nowait', [False, True])
@pytest.mark.fake
async def test_connection_disconnect(nowait):
    server = FakeServer()
    r = aioredis.FakeRedis(server=server)
    conn = await r.connection_pool.get_connection("_")
    assert conn is not None

    await conn.disconnect(nowait=nowait)

    assert conn._sock is None


async def test_connection_with_username_and_password():
    server = FakeServer()
    r = aioredis.FakeRedis(server=server, username='username', password='password')

    test_value = "this_is_a_test"
    await r.hset('test:key', "test_hash", test_value)
    result = await r.hget('test:key', "test_hash")
    assert result.decode() == test_value


@pytest.mark.fake
async def test_init_args():
    sync_r1 = FakeStrictRedis()
    r1 = FakeAsyncRedis()
    r5 = FakeAsyncRedis()
    r2 = FakeAsyncRedis(server=FakeServer())

    shared_server = FakeServer()
    r3 = FakeAsyncRedis(server=shared_server)
    r4 = FakeAsyncRedis(server=shared_server)

    await r1.set('foo', 'bar')
    await r3.set('bar', 'baz')

    assert await r1.get('foo') == b'bar'
    assert await r5.get('foo') is None
    assert sync_r1.get('foo') is None
    assert await r2.get('foo') is None
    assert await r3.get('foo') is None

    assert await r3.get('bar') == b'baz'
    assert await r4.get('bar') == b'baz'
    assert await r1.get('bar') is None
