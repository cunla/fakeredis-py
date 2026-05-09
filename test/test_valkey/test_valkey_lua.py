import pytest

import redis
import valkey

_ = pytest.importorskip("lupa")


@pytest.mark.unsupported_server_types("redis", "dragonfly")
def test_server_call(r: valkey.Valkey):
    r.set("key", "value")
    result = r.eval("return server.call('GET', KEYS[1])", 1, "key")
    assert result == b"value"


@pytest.mark.unsupported_server_types("redis", "dragonfly")
def test_server_pcall(r: valkey.Valkey):
    r.set("key", "value")
    result = r.eval("return server.pcall('GET', KEYS[1])", 1, "key")
    assert result == b"value"


@pytest.mark.unsupported_server_types("valkey")
def test_server_alias_not_available_in_redis_mode(r: redis.Redis):
    with pytest.raises(redis.exceptions.ResponseError, match="'server'"):
        r.eval("return server.call('SET', KEYS[1], ARGV[1])", 1, "key", "value")
