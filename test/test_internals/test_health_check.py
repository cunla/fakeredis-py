"""Connections created with health_check_interval > 0 (https://github.com/cunla/fakeredis-py/issues/658)."""

from collections.abc import Callable
from typing import Any
from unittest import mock

import pytest
import redis

import fakeredis
from fakeredis import FakeRedis
from fakeredis._typing import AsyncClientType, ClientType
from test import testtools
from test.testtools import RESPONSE_ERRORS, pool_get_connection

pytestmark = [
    pytest.mark.fake,
    testtools.run_test_if_redispy_ver("gte", "5"),
]


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


def test_connection_handshake_with_health_check_interval():
    r = FakeRedis(server=fakeredis.FakeServer(), health_check_interval=30, client_name="c", db=1)
    assert r.set("foo", "bar") is True
    assert r.get("foo") == b"bar"
    assert r.client_getname() in ("c", b"c")


@testtools.run_test_if_redispy_ver("gte", "6.0")
def test_health_check_pings_only_once_the_interval_has_passed(create_connection: Callable[..., ClientType]):
    client = create_connection(db=2, health_check_interval=30)
    client.set("foo", "bar")
    conn = pool_get_connection(client.connection_pool)
    try:
        with mock.patch.object(conn, "_send_ping", wraps=conn._send_ping) as send_ping:
            conn.send_command("GET", "foo")
            assert conn.read_response() == b"bar"
            send_ping.assert_not_called()

            conn.next_health_check = 0
            conn.send_command("GET", "foo")
            assert conn.read_response() == b"bar"
            send_ping.assert_called_once()
    finally:
        client.connection_pool.release(conn)


@testtools.run_test_if_redispy_ver("gte", "6.0")
def test_error_reply_postpones_health_check(create_connection: Callable[..., ClientType]):
    client = create_connection(db=2, health_check_interval=30)
    client.set("foo", "bar")
    conn = pool_get_connection(client.connection_pool)
    try:
        conn.next_health_check = 0
        conn.send_command("LPUSH", "foo", "x", check_health=False)
        with pytest.raises(RESPONSE_ERRORS, match="WRONGTYPE"):
            conn.read_response()
        # The error reply restarted the interval, so the next command goes out without a PING. Checked through the
        # behaviour rather than next_health_check, whose clock differs between redis-py versions.
        with mock.patch.object(conn, "_send_ping", wraps=conn._send_ping) as send_ping:
            conn.send_command("GET", "foo")
            assert conn.read_response() == b"bar"
            send_ping.assert_not_called()
    finally:
        client.connection_pool.release(conn)


@pytest.mark.asyncio
async def test_async_connection_handshake_with_health_check_interval(
    create_async_connection: Callable[..., AsyncClientType],
):
    client = create_async_connection(db=2, health_check_interval=30, client_name="c")
    assert await client.set("foo", "bar") is True
    assert await client.get("foo") == b"bar"
    assert await client.client_getname() in ("c", b"c")


@pytest.mark.asyncio
async def test_async_health_check_pings_only_once_the_interval_has_passed(
    create_async_connection: Callable[..., AsyncClientType],
):
    client = create_async_connection(db=2, health_check_interval=30)
    await client.set("foo", "bar")
    conn = await pool_get_connection(client.connection_pool)
    try:
        with mock.patch.object(conn, "_send_ping", wraps=conn._send_ping) as send_ping:
            await conn.send_command("GET", "foo")
            assert await conn.read_response() == b"bar"
            send_ping.assert_not_called()

            conn.next_health_check = 0
            await conn.send_command("GET", "foo")
            assert await conn.read_response() == b"bar"
            send_ping.assert_called_once()
    finally:
        await client.connection_pool.release(conn)
