import sys
import time
from threading import Thread

import pytest
import redis
from redis import Redis
from redis.lock import Lock

from fakeredis import TcpFakeServer

pytestmark = []
pytestmark.extend(
    [pytest.mark.skipif(sys.version_info < (3, 11), reason="TcpFakeServer is only available in Python 3.11+")]
)


def test_tcp_server_started():
    server_address = ("127.0.0.1", 19000)
    server = TcpFakeServer(server_address)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    with redis.Redis(host=server_address[0], port=server_address[1]) as r:
        r.set("foo", "bar")
        assert r.get("foo") == b"bar"
    server.shutdown()
    server.server_close()
    t.join()


def test_tcp_server_lock():
    server_address = ("127.0.0.1", 19000)
    server = TcpFakeServer(server_address)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    r = Redis.from_url("redis://localhost:19000", decode_responses=True)
    lock = Lock(r, "my-lock")
    lock.acquire()
    print(f"Acquired lock {lock.locked()}")
    lock.release()
    server.shutdown()
