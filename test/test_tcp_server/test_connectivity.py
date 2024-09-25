import time
from threading import Thread

import redis

from fakeredis import TcpFakeServer


def test_tcp_server_started():
    server_address = ("127.0.0.1", 19000)
    server = TcpFakeServer(server_address)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    r = redis.Redis(host=server_address[0], port=server_address[1])
    r.set("foo", "bar")
    assert r.get("foo") == b"bar"
    server.shutdown()
