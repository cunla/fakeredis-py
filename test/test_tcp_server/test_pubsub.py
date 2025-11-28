import asyncio
import logging
import socket
from contextlib import contextmanager, closing
from threading import Thread

import pytest
import pytest_asyncio

@pytest.fixture
def tcp_server():
    from fakeredis import TcpFakeServer

    host = "localhost"
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = s.getsockname()[1]

    server = TcpFakeServer((host, port), server_type="redis")
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        logging.info(f"Redis server started at {host}:{port}")
        yield host, port
    finally:
        server.shutdown()
        server.server_close()
        t.join()


@pytest.mark.asyncio
async def test_pubsub(tcp_server):
    import redis.asyncio as redis

    host, port = tcp_server

    create_redis_client = lambda: redis.Redis(
        connection_pool=redis.ConnectionPool(
            host=host,
            port=port,
            decode_responses=False,
            socket_timeout = 5.0,
            socket_connect_timeout = 5.0,
        )
    )

    payload = b"test message"

    async def listen():
        redis_client = create_redis_client()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe("channel1", "channel2")
        num_received = 0
        for i in range(5):
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=5
            )
            if not message:
                logging.error(f"Timed out: {message}")
                continue

            data = message.get("data")
            logging.error(f"Received message: {data}")
            assert data == payload
            num_received += 1
        
        await pubsub.unsubscribe("channel1", "channel2")
        await asyncio.sleep(1)
        assert num_received == 5
        
    async def publish():
        redis_client = create_redis_client()
        for i in range(10):
            try:
                channel = f"channel{i%2+1}"
                logging.error(f"Publishing to {channel}: {payload}")
                await redis_client.publish(channel, payload)
            except Exception:
                logging.exception("Failed to publish message")
            await asyncio.sleep(0.5)

    t1 = asyncio.create_task(listen())
    t2 = asyncio.create_task(publish())

    await t2
    await t1
