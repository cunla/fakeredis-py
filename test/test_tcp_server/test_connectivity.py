from __future__ import annotations

import threading
import time
from threading import Thread

import pytest
import redis

from fakeredis._tcp_server import TcpFakeServer

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.tcp_server,
    ]
)


def test_tcp_server_started(tcp_server_address: tuple[str, int]):
    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1]) as r:
        r.set("foo", "bar")
        assert r.get("foo") == b"bar"


def test_tcp_server_connection_reset_error(tcp_server_address: tuple[str, int]):
    with redis.Redis(*tcp_server_address) as r:
        r.rpush("test", b"foo")

    with redis.Redis(*tcp_server_address) as r:
        assert r.rpop("test") == b"foo"


def test_bulk_string_length(real_server_address: tuple[str, int], tcp_server_address: tuple[str, int]):
    """Test that malformed bulk string input is handled correctly."""
    import socket
    from contextlib import closing

    connections = [real_server_address, tcp_server_address]
    for conn in connections:
        host, port = conn[0], conn[1]
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.connect((host, port))
            s.sendall(b"$ 1\ntest")
            data = s.recv(1024).decode()
            assert data == "-ERR unknown command '$', with args beginning with: '1' \r\n", (
                f"Failed for server at {host}:{port}"
            )


def test_tcp_server_started_protocol_3(tcp_server_address: tuple[str, int]):
    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1], protocol=3) as r:
        r.set("foo", "bar")
        assert r.get("foo") == b"bar"


def test_tcp_server_clean_shutdown():
    """Verify that shutdown() + server_close() leaves no lingering handler threads."""
    port = 19100
    server = TcpFakeServer(("127.0.0.1", port))
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.05)

    threads_before = set(threading.enumerate())

    with redis.Redis(host="127.0.0.1", port=port) as r:
        r.set("k", "v")
        assert r.get("k") == b"v"

    # Allow handler thread to be created
    time.sleep(0.05)
    handler_threads = set(threading.enumerate()) - threads_before

    server.shutdown()
    server.server_close()

    for ht in handler_threads:
        ht.join(timeout=2.0)
        assert not ht.is_alive(), f"Handler thread {ht.name} is still alive after shutdown"
