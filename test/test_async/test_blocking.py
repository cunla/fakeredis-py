import asyncio

import pytest
import pytest_asyncio

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
