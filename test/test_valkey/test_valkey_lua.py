import pytest

from fakeredis._typing import ClientType

_ = pytest.importorskip("lupa")


@pytest.mark.unsupported_server_types("redis", "dragonfly")
def test_server_is_alias_for_redis(r: ClientType):
    result = r.eval("return tostring(server == redis)", 0)
    assert result == b"true"


@pytest.mark.unsupported_server_types("valkey")
def test_server_alias_not_available_in_redis_mode(r: ClientType):
    # Check if server exists in globals
    result = r.eval("return tostring(rawget(_G, 'server') == nil)", 0)
    assert result == b"true"
