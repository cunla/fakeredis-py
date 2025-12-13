from typing import Tuple

import pytest
import redis


pytestmark = []
pytestmark.extend(
    [
        pytest.mark.tcp_server,
    ]
)


def test_tcp_server_started(tcp_server_address: Tuple[str, int]):
    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1]) as r:
        r.set("foo", "bar")
        assert r.get("foo") == b"bar"


def test_tcp_server_connection_reset_error(tcp_server_address: Tuple[str, int]):
    with redis.Redis(*tcp_server_address) as r:
        r.rpush("test", b"foo")

    with redis.Redis(*tcp_server_address) as r:
        assert r.rpop("test") == b"foo"


def test_bulk_string_length(real_server_address: Tuple[str, int], tcp_server_address: Tuple[str, int]):
    """Test that malformed bulk string input is handled correctly."""
    from contextlib import closing
    import socket

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


# todo: re-enable when fake-tcp-server supports protocol 3
# def test_tcp_server_started_protocol_3(tcp_server_address: Tuple[str, int]):
#     with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1], protocol=3) as r:
#         r.set("foo", "bar")
#         assert r.get("foo") == b"bar"
