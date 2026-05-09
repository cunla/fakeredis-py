import pytest

import fakeredis
import redis
import valkey

_ = pytest.importorskip("lupa")


@pytest.mark.unsupported_server_types("redis")
def test_server_call(r: valkey.Valkey):
    r.set("key", "value")
    result = r.eval("return server.call('GET', KEYS[1])", 1, "key")
    assert result == b"value"


@pytest.mark.unsupported_server_types("redis")
def test_server_pcall(r: valkey.Valkey):
    r.set("key", "value")
    result = r.eval("return server.pcall('GET', KEYS[1])", 1, "key")
    assert result == b"value"


@pytest.mark.unsupported_server_types("valkey")
def test_server_alias_not_available_in_redis_mode(r: redis.Redis):
    with pytest.raises(Exception, match="server"):
        r.eval("return server.call('SET', KEYS[1], ARGV[1])", 1, "key", "value")
