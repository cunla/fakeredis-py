import re

import pytest
import redis
import redis.asyncio

from fakeredis import FakeServer, aioredis, FakeAsyncRedis, FakeStrictRedis
from test import testtools

pytestmark = []
fake_only = pytest.mark.parametrize("async_redis", [pytest.param("fake", marks=pytest.mark.fake)], indirect=True)
pytestmark.extend(
    [
        pytest.mark.asyncio,
    ]
)


@fake_only
@testtools.run_test_if_redispy_ver("gte", "5.1")
async def test_repr_redis_51(async_redis: redis.asyncio.Redis):
    assert re.fullmatch(
        r"<redis.asyncio.connection.ConnectionPool\("
        r"<fakeredis.aioredis.FakeConnection\(server=<fakeredis._server.FakeServer object at .*>,db=0\)>\)>",
        repr(async_redis.connection_pool),
    )


@fake_only
@pytest.mark.disconnected
async def test_not_connected(async_redis: redis.asyncio.Redis):
    with pytest.raises(redis.asyncio.ConnectionError):
        await async_redis.ping()


@fake_only
async def test_disconnect_server(async_redis, fake_server):
    await async_redis.ping()
    fake_server.connected = False
    with pytest.raises(redis.asyncio.ConnectionError):
        await async_redis.ping()
    fake_server.connected = True


@pytest.mark.fake
async def test_from_url():
    r0 = aioredis.FakeRedis.from_url("redis://localhost?db=0")
    r1 = aioredis.FakeRedis.from_url("redis://localhost?db=1")
    # Check that they are indeed different databases
    await r0.set("foo", "a")
    await r1.set("foo", "b")
    assert await r0.get("foo") == b"a"
    assert await r1.get("foo") == b"b"
    await r0.connection_pool.disconnect()
    await r1.connection_pool.disconnect()


@pytest.mark.fake
async def test_from_url_with_version():
    r0 = aioredis.FakeRedis.from_url("redis://localhost?db=0", version=(6,))
    r1 = aioredis.FakeRedis.from_url("redis://localhost?db=1", version=(6,))
    # Check that they are indeed different databases
    await r0.set("foo", "a")
    await r1.set("foo", "b")
    assert await r0.get("foo") == b"a"
    assert await r1.get("foo") == b"b"
    await r0.connection_pool.disconnect()
    await r1.connection_pool.disconnect()


@fake_only
async def test_from_url_with_server(async_redis, fake_server):
    r2 = aioredis.FakeRedis.from_url("redis://localhost", server=fake_server)
    await async_redis.set("foo", "bar")
    assert await r2.get("foo") == b"bar"
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


@testtools.run_test_if_redispy_ver("gte", "4.4.0")
@pytest.mark.parametrize("nowait", [False, True])
@pytest.mark.fake
async def test_connection_disconnect(nowait):
    server = FakeServer()
    r = aioredis.FakeRedis(server=server)
    conn = await r.connection_pool.get_connection("_")
    assert conn is not None

    await conn.disconnect(nowait=nowait)

    assert conn._sock is None


@pytest.mark.fake
async def test_init_args():
    sync_r1 = FakeStrictRedis()
    r1 = FakeAsyncRedis()
    r5 = FakeAsyncRedis()
    r2 = FakeAsyncRedis(server=FakeServer())

    shared_server = FakeServer()
    r3 = FakeAsyncRedis(server=shared_server)
    r4 = FakeAsyncRedis(server=shared_server)

    await r1.set("foo", "bar")
    await r3.set("bar", "baz")

    assert await r1.get("foo") == b"bar"
    assert await r5.get("foo") is None
    assert sync_r1.get("foo") is None
    assert await r2.get("foo") is None
    assert await r3.get("foo") is None

    assert await r3.get("bar") == b"baz"
    assert await r4.get("bar") == b"baz"
    assert await r1.get("bar") is None
