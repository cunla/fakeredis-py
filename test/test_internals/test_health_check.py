"""Connections created with health_check_interval > 0 (https://github.com/cunla/fakeredis-py/issues/658)."""

import asyncio
from typing import Any
from unittest import mock

import pytest
import redis
import testtools

import fakeredis
from test.testtools import RESPONSE_ERRORS, pool_get_connection

# The valkey clients are only exported when valkey-py is installed.
SYNC_CLIENTS = [getattr(fakeredis, name) for name in ("FakeRedis", "FakeValkey") if hasattr(fakeredis, name)]
ASYNC_CLIENTS = [getattr(fakeredis, name) for name in ("FakeAsyncRedis", "FakeAsyncValkey") if hasattr(fakeredis, name)]

pytestmark = [
    pytest.mark.fake,
    testtools.run_test_if_redispy_ver("gte", "5"),
]

DEFAULT_CLIENT_KWARGS = {
    "server": fakeredis.FakeServer(),
    "health_check_interval": 30,
    "client_name": "c",
    "db": 1,
}


@pytest.mark.timeout(10)
@pytest.mark.parametrize(
    "pool_kwargs", [{}, {"retry_on_error": [redis.TimeoutError]}], ids=["default", "retry_on_error"]
)
def test_connection_pool_from_url_with_health_check_interval(pool_kwargs: dict[str, Any]):
    # The reproduction from the issue. With redis-py 8.2, the first command raised `Bad response from PING health
    # check`, or with retry_on_error blocked forever in read_response, hence the timeout.
    pool = redis.ConnectionPool.from_url(
        "redis://localhost:6379/0",
        connection_class=fakeredis.FakeRedisConnection,
        server=fakeredis.FakeServer(),
        health_check_interval=30,
        **pool_kwargs,
    )
    assert redis.Redis(connection_pool=pool).get("key") is None


@pytest.mark.parametrize("client_class", SYNC_CLIENTS)
def test_connection_handshake_with_health_check_interval(client_class: Any):
    r = client_class(**DEFAULT_CLIENT_KWARGS)
    assert r.set("foo", "bar") is True
    assert r.get("foo") == b"bar"
    assert r.client_getname() in ("c", b"c")


@pytest.mark.parametrize("client_class", SYNC_CLIENTS)
def test_health_check_pings_only_once_the_interval_has_passed(client_class: Any):
    r = client_class(**DEFAULT_CLIENT_KWARGS)
    r.set("foo", "bar")
    conn = pool_get_connection(r.connection_pool)
    try:
        assert conn.next_health_check > conn._health_check_clock() + 25
        with mock.patch.object(conn, "_send_ping", wraps=conn._send_ping) as send_ping:
            conn.send_command("GET", "foo")
            assert conn.read_response() == b"bar"
            send_ping.assert_not_called()

            conn.next_health_check = 0
            conn.send_command("GET", "foo")
            assert conn.read_response() == b"bar"
            send_ping.assert_called_once()
    finally:
        r.connection_pool.release(conn)


@pytest.mark.parametrize("client_class", SYNC_CLIENTS)
def test_error_reply_postpones_health_check(client_class: Any):
    r = client_class(**DEFAULT_CLIENT_KWARGS)
    r.set("foo", "bar")
    conn = pool_get_connection(r.connection_pool)
    try:
        conn.next_health_check = 0
        conn.send_command("LPUSH", "foo", "x", check_health=False)
        with pytest.raises(RESPONSE_ERRORS, match="WRONGTYPE"):
            conn.read_response()
        assert conn.next_health_check > conn._health_check_clock() + 25
    finally:
        r.connection_pool.release(conn)


@pytest.mark.asyncio
@pytest.mark.parametrize("client_class", ASYNC_CLIENTS)
async def test_async_connection_handshake_with_health_check_interval(client_class: Any):
    r = client_class(**DEFAULT_CLIENT_KWARGS)
    assert await r.set("foo", "bar") is True
    assert await r.get("foo") == b"bar"
    assert await r.client_getname() in ("c", b"c")


@pytest.mark.asyncio
@pytest.mark.parametrize("client_class", ASYNC_CLIENTS)
async def test_async_health_check_pings_only_once_the_interval_has_passed(client_class: Any):
    r = client_class(**DEFAULT_CLIENT_KWARGS)
    await r.set("foo", "bar")
    conn = await pool_get_connection(r.connection_pool)
    try:
        assert conn.next_health_check > asyncio.get_running_loop().time() + 25
        with mock.patch.object(conn, "_send_ping", wraps=conn._send_ping) as send_ping:
            await conn.send_command("GET", "foo")
            assert await conn.read_response() == b"bar"
            send_ping.assert_not_called()

            conn.next_health_check = 0
            await conn.send_command("GET", "foo")
            assert await conn.read_response() == b"bar"
            send_ping.assert_called_once()
    finally:
        await r.connection_pool.release(conn)
