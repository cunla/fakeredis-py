import threading
import time
from threading import Thread

import pytest
import redis

from fakeredis._tcp_server import TcpFakeServer
from test.conftest import ServerDetails
from test.testtools import REDIS_PY_VERSION

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


def test_bulk_string_length(
    real_server_address: tuple[str, int],
    tcp_server_address: tuple[str, int],
    real_server_details: ServerDetails,
):
    """Test that malformed bulk string input is handled correctly."""
    import socket
    from contextlib import closing

    # Dragonfly reports unknown commands in its own wording, without echoing the arguments back.
    if real_server_details.server_type == "dragonfly":
        expected = "-ERR unknown command `$`\r\n"
    else:
        expected = "-ERR unknown command '$', with args beginning with: '1' \r\n"

    connections = [real_server_address, tcp_server_address]
    for conn in connections:
        host, port = conn[0], conn[1]
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.connect((host, port))
            s.sendall(b"$ 1\ntest")
            data = s.recv(1024).decode()
            assert data == expected, f"Failed for server at {host}:{port}"


def test_tcp_server_started_protocol_3(tcp_server_address: tuple[str, int]):
    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1], protocol=3) as r:
        r.set("foo", "bar")
        assert r.get("foo") == b"bar"


def test_handler_threads_are_reaped_when_clients_disconnect():
    """Each disconnecting client's handler thread must exit, not park in the read loop."""
    server = TcpFakeServer(("127.0.0.1", 0))
    port = server.server_address[1]
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        time.sleep(0.1)
        threads_before = threading.active_count()

        for _ in range(10):
            client = redis.Redis(host="127.0.0.1", port=port)
            client.ping()
            client.close()
            client.connection_pool.disconnect()

        deadline = time.time() + 5.0
        while time.time() < deadline and threading.active_count() > threads_before:
            time.sleep(0.05)

        assert threading.active_count() == threads_before, (
            f"{threading.active_count() - threads_before} handler threads leaked"
        )
        assert server.clients == {}
    finally:
        server.shutdown()
        server.server_close()
        t.join()


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


@pytest.mark.parametrize("protocol", [2, 3])
def test_tcp_server_reply_types(tcp_server_address: tuple[str, int], protocol: int):
    """Nulls, doubles, maps and sets are encoded differently under RESP2 and RESP3."""
    if REDIS_PY_VERSION.major < 5:
        if protocol == 3:
            pytest.skip("RESP3 needs redis-py 5")
        kwargs = {}
    else:
        kwargs = {"protocol": protocol}
    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1], **kwargs) as r:
        assert r.get("missing") is None
        r.hset("hash", mapping={"field": "1"})
        assert r.hgetall("hash") == {b"field": b"1"}
        r.zadd("zset", {"member": 1.5})
        assert r.zscore("zset", "member") == 1.5
        r.sadd("set", "a", "b")
        assert r.smembers("set") == {b"a", b"b"}
        assert r.incrbyfloat("float", 0.5) == 0.5


def test_tcp_server_keeps_the_connection_after_a_shutdown_value(tcp_server_address: tuple[str, int]):
    # A reply whose value was the string "shutdown" used to make the server close the connection.
    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1]) as r:
        client_id = r.client_id()
        r.set("key", "SHUTDOWN")
        assert r.get("key") == b"SHUTDOWN"
        assert r.client_id() == client_id
