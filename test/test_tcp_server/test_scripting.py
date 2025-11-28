import time
from threading import Thread

import pytest
import redis

from fakeredis import TcpFakeServer
from fakeredis._tcp_server import TCP_SERVER_TEST_PORT
from test import testtools


@testtools.run_test_if_lupa_installed()
def test_evalsha_missing_script():
    """Test that EVALSHA with a non-existent script returns NOSCRIPT error."""
    server_address = ("127.0.0.1", TCP_SERVER_TEST_PORT)
    server = TcpFakeServer(server_address)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)

    with redis.Redis(host=server_address[0], port=server_address[1]) as r:
        fake_sha = "0" * 40
        with pytest.raises(redis.exceptions.NoScriptError):
            r.evalsha(fake_sha, 0)

    server.server_close()
    server.shutdown()
    t.join()
