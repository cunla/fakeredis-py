import socket
import time
from contextlib import closing
from threading import Thread

import pytest
import redis

from fakeredis import TcpFakeServer
from test import testtools


@pytest.fixture(scope="function")
def redis_server():
    host = "127.0.0.1"
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = s.getsockname()[1]

    class TcpFakeServerWithExceptions(TcpFakeServer):
        def handle_error(self, request, client_address):
            super().handle_error(request, client_address)
            # Send an error message back to the client here
            request.sendall(b"An error occurred on the server.")

    server_address = (host, port)
    server = TcpFakeServerWithExceptions(server_address)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.1)

    try:
        with redis.Redis(host=host, port=port) as r:
            yield r
    finally:
        server.server_close()
        server.shutdown()
        thread.join()


@testtools.run_test_if_lupa_installed()
def test_eval_multiline_script(redis_server):
    """Test that EVAL works with multi-line Lua scripts."""
    # Multi-line script with trailing newline
    script = """
local key = KEYS[1]
local value = ARGV[1]
redis.call('SET', key, value)
return redis.call('GET', key)
"""
    result = redis_server.eval(script, 1, "testkey", "testvalue")
    assert result == b"testvalue"


@testtools.run_test_if_lupa_installed()
def test_script_load_multiline(redis_server):
    """Test that SCRIPT LOAD works with multi-line Lua scripts."""
    # Multi-line script
    script = """local x = 1
local y = 2
return x + y"""
    sha = redis_server.script_load(script)
    result = redis_server.evalsha(sha, 0)
    assert result == 3


@testtools.run_test_if_lupa_installed()
def test_eval_script_with_trailing_newline(redis_server):
    """Test that scripts with trailing newlines are preserved."""
    # Script with explicit trailing newline
    script = "return 'hello'\n"
    result = redis_server.eval(script, 0)
    assert result == b"hello"


@testtools.run_test_if_lupa_installed()
def test_bulk_string_length(redis_server):
    """Test that malformed bulk string input is handled correctly."""
    host = redis_server.connection_pool.connection_kwargs.get("host")
    port = redis_server.connection_pool.connection_kwargs.get("port")

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.connect((host, port))
        s.sendall(b"$ 1\ntest")
        data = s.recv(1024).decode()
        assert data != "An error occurred on the server."
