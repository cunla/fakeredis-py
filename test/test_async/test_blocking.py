import asyncio

import pytest
import pytest_asyncio
import redis
import valkey

from fakeredis._typing import AsyncClientType
from test.testtools import resp_conversion

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.asyncio,
    ]
)


@pytest_asyncio.fixture
async def conn(async_redis: AsyncClientType):
    """A single connection, rather than a pool."""
    async with async_redis.client() as conn:
        yield conn


async def test_blocking_ready(async_redis, conn):
    """Blocking command which does not need to block."""
    await async_redis.rpush("list", "x")
    result = await conn.blpop("list", timeout=1)
    assert result == resp_conversion(async_redis, [b"list", b"x"], (b"list", b"x"))


@pytest.mark.slow
async def test_blocking_timeout(conn):
    """Blocking command that times out without completing."""
    result = await conn.blpop("missing", timeout=1)
    assert result is None


@pytest.mark.slow
async def test_blocking_unblock(async_redis, conn):
    """Blocking command that gets unblocked after some time."""

    async def unblock():
        await asyncio.sleep(0.1)
        await async_redis.rpush("list", "y")

    task = asyncio.get_running_loop().create_task(unblock())
    result = await conn.blpop("list", timeout=1)
    assert result == resp_conversion(async_redis, [b"list", b"y"], (b"list", b"y"))
    await task


async def _block_on_blpop(conn) -> asyncio.Task:
    task = asyncio.get_running_loop().create_task(conn.blpop("missing", timeout=5))
    # Give the client time to actually park in the blocking command.
    await asyncio.sleep(0.3)
    return task


@pytest.mark.slow
@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
async def test_blocking_client_unblock_timeout(async_redis, conn):
    """CLIENT UNBLOCK wakes a blocked client as though the command had timed out."""
    client_id = await conn.client_id()
    task = await _block_on_blpop(conn)
    try:
        assert await async_redis.execute_command("CLIENT", "UNBLOCK", str(client_id)) == 1
        assert await asyncio.wait_for(task, timeout=3) is None
    finally:
        if not task.done():
            task.cancel()


@pytest.mark.slow
@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
async def test_blocking_client_unblock_error(async_redis, conn):
    """CLIENT UNBLOCK ... ERROR makes the blocked command fail instead."""
    client_id = await conn.client_id()
    task = await _block_on_blpop(conn)
    try:
        assert await async_redis.execute_command("CLIENT", "UNBLOCK", str(client_id), "ERROR") == 1
        with pytest.raises((redis.ResponseError, valkey.ResponseError), match="UNBLOCKED"):
            await asyncio.wait_for(task, timeout=3)
    finally:
        if not task.done():
            task.cancel()


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
async def test_client_unblock_not_blocked(async_redis, conn):
    assert await async_redis.execute_command("CLIENT", "UNBLOCK", str(await conn.client_id())) == 0
