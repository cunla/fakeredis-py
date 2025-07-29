import pytest

from fakeredis import FakeValkey, FakeAsyncValkey


def test_init_args():
    conn = FakeValkey()
    conn.set("key1", "value1")
    assert conn.get("key1") == b"value1"


@pytest.mark.asyncio
async def test_async_init_kwargs():
    conn = FakeAsyncValkey()
    await conn.set("key2", "value2")
    assert await conn.get("key2") == b"value2"
