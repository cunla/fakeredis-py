import time
from threading import Thread

import redis
from redis import Redis
from redis.lock import Lock

from fakeredis import TcpFakeServer
from fakeredis._tcp_server import TCP_SERVER_TEST_PORT
from test import testtools


def test_tcp_server_started():
    server_address = ("127.0.0.1", TCP_SERVER_TEST_PORT)
    server = TcpFakeServer(server_address)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    with redis.Redis(host=server_address[0], port=server_address[1]) as r:
        r.set("foo", "bar")
        assert r.get("foo") == b"bar"
    server.server_close()
    server.shutdown()
    r.shutdown()
    t.join()


@testtools.run_test_if_lupa_installed()
def test_tcp_server_lock():
    server_address = ("127.0.0.1", TCP_SERVER_TEST_PORT)
    server = TcpFakeServer(server_address)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    r = Redis.from_url(f"redis://{server_address[0]}:{server_address[1]}", decode_responses=True)
    lock = Lock(r, "my-lock")
    lock.acquire()
    print(f"Acquired lock {lock.locked()}")
    lock.release()
    r.close()
    server.server_close()
    server.shutdown()
    t.join()


def test_tcp_server_connection_reset_error():
    server_address = ("127.0.0.1", TCP_SERVER_TEST_PORT)
    server = TcpFakeServer(server_address, server_type="redis")
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)

    with redis.Redis(*server_address) as r:
        r.rpush("test", b"foo")

    with redis.Redis(*server_address) as r:
        assert r.rpop("test") == b"foo"

    server.server_close()
    server.shutdown()
    t.join()
