import pytest
import valkey


@pytest.mark.valkey_client_test
def test_raises_valkey_response_error(r: valkey.Valkey):
    with pytest.raises(valkey.ResponseError):
        r.incr("foo", 2.0)
