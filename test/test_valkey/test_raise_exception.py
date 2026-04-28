import pytest
import valkey


@pytest.mark.unsupported_server_types("redis", "dragonfly")
def test_raises_valkey_response_error(r: valkey.Valkey):
    with pytest.raises(valkey.ResponseError):
        r.incr("foo", 2.0)
