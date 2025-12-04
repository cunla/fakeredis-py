from typing import Tuple

import pytest
import redis
from redis import Redis
from redis.lock import Lock

lupa_tests = pytest.importorskip("lupa")

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.tcp_server,
    ]
)


def test_evalsha_missing_script(tcp_server_address: Tuple[str, int]):
    """Test that EVALSHA with a non-existent script returns NOSCRIPT error."""
    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1]) as r:
        fake_sha = "0" * 40
        with pytest.raises(redis.exceptions.NoScriptError):
            r.evalsha(fake_sha, 0)


def test_tcp_server_lock(tcp_server_address: Tuple[str, int]):
    r = Redis.from_url(f"redis://{tcp_server_address[0]}:{tcp_server_address[1]}", decode_responses=True)
    lock = Lock(r, "my-lock")
    lock.acquire()
    assert lock.locked() is True
    lock.release()


def test_eval_multiline_script(tcp_server_address: Tuple[str, int]):
    """Test that EVAL works with multi-line Lua scripts."""
    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1]) as r:
        # Multi-line script with trailing newline
        script = """
local key = KEYS[1]
local value = ARGV[1]
redis.call('SET', key, value)
return redis.call('GET', key)
"""
        result = r.eval(script, 1, "testkey", "testvalue")
        assert result == b"testvalue"


def test_script_load_multiline(tcp_server_address: Tuple[str, int]):
    """Test that SCRIPT LOAD works with multi-line Lua scripts."""
    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1]) as r:
        # Multi-line script
        script = """local x = 1
local y = 2
return x + y"""
        sha = r.script_load(script)
        result = r.evalsha(sha, 0)
        assert result == 3


def test_eval_script_with_trailing_newline(tcp_server_address: Tuple[str, int]):
    """Test that scripts with trailing newlines are preserved."""
    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1]) as r:
        # Script with explicit trailing newline
        script = "return 'hello'\n"
        result = r.eval(script, 0)
        assert result == b"hello"
