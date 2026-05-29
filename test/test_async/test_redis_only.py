import pytest

from fakeredis._typing import AsyncClientType

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.asyncio,
    ]
)


@pytest.mark.asyncio
@pytest.mark.unsupported_server_types("dragonfly", "valkey")
async def test_async_lock(async_redis: AsyncClientType):
    from redis.asyncio.lock import Lock

    lock = Lock(async_redis, "lock_key")

    async with lock:
        pass

    assert not await lock.locked()  # already released
