import pytest

import fakeredis

_ = pytest.importorskip("lupa")


def test_server_call():
    r = fakeredis.FakeStrictValkey(server_type="valkey")
    r.set("key", "value")
    result = r.eval("return server.call('GET', KEYS[1])", 1, "key")
    assert result == b"value"


def test_server_pcall():
    r = fakeredis.FakeStrictValkey(server_type="valkey")
    r.set("key", "value")
    result = r.eval("return server.pcall('GET', KEYS[1])", 1, "key")
    assert result == b"value"


def test_server_alias_not_available_in_redis_mode():
    r = fakeredis.FakeStrictRedis()
    with pytest.raises(Exception, match="server"):
        r.eval("return server.call('SET', KEYS[1], ARGV[1])", 1, "key", "value")
