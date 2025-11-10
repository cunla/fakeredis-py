import time
from threading import Thread

import redis

from fakeredis import TcpFakeServer
from test import testtools


@testtools.run_test_if_lupa_installed()
def test_eval_multiline_script():
    """Test that EVAL works with multi-line Lua scripts."""
    server_address = ("127.0.0.1", 19000)
    server = TcpFakeServer(server_address)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)

    with redis.Redis(host=server_address[0], port=server_address[1]) as r:
        # Multi-line script with trailing newline
        script = """
local key = KEYS[1]
local value = ARGV[1]
redis.call('SET', key, value)
return redis.call('GET', key)
"""
        result = r.eval(script, 1, "testkey", "testvalue")
        assert result == b"testvalue"

    server.server_close()
    server.shutdown()
    t.join()


@testtools.run_test_if_lupa_installed()
def test_script_load_multiline():
    """Test that SCRIPT LOAD works with multi-line Lua scripts."""
    server_address = ("127.0.0.1", 19001)
    server = TcpFakeServer(server_address)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)

    with redis.Redis(host=server_address[0], port=server_address[1]) as r:
        # Multi-line script
        script = """local x = 1
local y = 2
return x + y"""
        sha = r.script_load(script)
        result = r.evalsha(sha, 0)
        assert result == 3

    server.server_close()
    server.shutdown()
    t.join()


@testtools.run_test_if_lupa_installed()
def test_eval_script_with_trailing_newline():
    """Test that scripts with trailing newlines are preserved."""
    server_address = ("127.0.0.1", 19002)
    server = TcpFakeServer(server_address)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)

    with redis.Redis(host=server_address[0], port=server_address[1]) as r:
        # Script with explicit trailing newline
        script = "return 'hello'\n"
        result = r.eval(script, 0)
        assert result == b"hello"

    server.server_close()
    server.shutdown()
    t.join()
