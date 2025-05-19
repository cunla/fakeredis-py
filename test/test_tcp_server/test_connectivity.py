import sys
import time
from threading import Thread

import pytest
import redis

from fakeredis import TcpFakeServer


@pytest.mark.skipif(sys.version_info < (3, 11), reason="TcpFakeServer is only available in Python 3.11+")
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
