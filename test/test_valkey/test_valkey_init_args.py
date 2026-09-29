import pytest
import valkey

import fakeredis
from fakeredis._clients._valkey import FakeAsyncValkeyConnection, FakeValkeyConnection


def test_init_args():
    conn = fakeredis.FakeValkey()
    conn.set("key1", "value1")
    assert conn.get("key1") == b"value1"


@pytest.mark.asyncio
async def test_async_init_kwargs():
    conn = fakeredis.FakeAsyncValkey()
    await conn.set("key2", "value2")
    assert await conn.get("key2") == b"value2"


@pytest.mark.parametrize("cls", [fakeredis.FakeValkey, fakeredis.FakeStrictValkey])
@pytest.mark.parametrize("scheme", ["valkey", "redis"])
def test_from_url(cls, scheme):
    conn = cls.from_url(f"{scheme}://localhost:6390/0")
    assert isinstance(conn.connection_pool, valkey.ConnectionPool)
    assert conn.connection_pool.connection_class is FakeValkeyConnection
    conn.set("key1", "value1")
    assert conn.get("key1") == b"value1"
    assert conn.connection_pool.make_connection()._server.server_type == "valkey"
    with pytest.raises(valkey.ResponseError):
        conn.incr("key1")


def test_from_url_db():
    db0 = fakeredis.FakeValkey.from_url("valkey://localhost:6390/0")
    db1 = fakeredis.FakeValkey.from_url("valkey://localhost:6390/1")
    db0.set("foo", "foo0")
    db1.set("foo", "foo1")
    assert db0.get("foo") == b"foo0"
    assert db1.get("foo") == b"foo1"


def test_from_url_rejects_other_server_types():
    with pytest.raises(ValueError, match="server_type must be valkey"):
        fakeredis.FakeValkey.from_url("valkey://localhost:6390/0", server_type="redis")


@pytest.mark.asyncio
@pytest.mark.parametrize("scheme", ["valkey", "redis"])
async def test_async_from_url(scheme):
    conn = fakeredis.FakeAsyncValkey.from_url(f"{scheme}://localhost:6390/0")
    assert isinstance(conn.connection_pool, valkey.asyncio.ConnectionPool)
    assert conn.connection_pool.connection_class is FakeAsyncValkeyConnection
    await conn.set("key2", "value2")
    assert await conn.get("key2") == b"value2"
    assert conn.connection_pool.make_connection()._server.server_type == "valkey"
    with pytest.raises(valkey.ResponseError):
        await conn.incr("key2")
    await conn.aclose()


@pytest.mark.asyncio
async def test_async_from_url_rejects_other_server_types():
    with pytest.raises(ValueError, match="server_type must be valkey"):
        fakeredis.FakeAsyncValkey.from_url("valkey://localhost:6390/0", server_type="redis")
