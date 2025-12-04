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
