import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test import testtools

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.supported_server_versions(min_redis_ver="8.7.2"),
        pytest.mark.unsupported_server_types("dragonfly", "valkey"),
    ]
)


def _as_floats(res) -> list:
    """INCREX BYFLOAT replies are bulk strings in RESP2 and doubles in RESP3."""
    return [float(x) for x in res]


def test_increx_default_increment(r: ClientType):
    assert testtools.raw_command(r, "INCREX", "key") == [1, 1]
    assert testtools.raw_command(r, "INCREX", "key") == [2, 1]


def test_increx_byint(r: ClientType):
    r.set("key", 100)
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 5) == [105, 5]
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", -10) == [95, -10]


def test_increx_byfloat(r: ClientType):
    r.set("key", 1.5)
    assert _as_floats(testtools.raw_command(r, "INCREX", "key", "BYFLOAT", 0.25)) == [1.75, 0.25]
    # Integer values can be incremented in float mode
    r.set("key2", 6)
    assert _as_floats(testtools.raw_command(r, "INCREX", "key2", "BYFLOAT", 0.5)) == [6.5, 0.5]


def test_increx_byint_on_float_value(r: ClientType):
    r.set("key", 1.5)
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "INCREX", "key", "BYINT", 1)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert "not an integer" in str(ctx.value)


def test_increx_non_numeric_value(r: ClientType):
    r.set("key", "hello")
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "INCREX", "key")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_increx_wrong_type(r: ClientType):
    r.lpush("key", "x")
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "INCREX", "key")
    assert "WRONGTYPE" in str(ctx.value)


def test_increx_ubound_skips_operation(r: ClientType):
    r.set("key", 99)
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 5, "UBOUND", 100) == [99, 0]
    assert r.get("key") == b"99"


def test_increx_ubound_saturate(r: ClientType):
    r.set("key", 99)
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 5, "UBOUND", 100, "SATURATE") == [100, 1]
    assert r.get("key") == b"100"


def test_increx_lbound_skips_operation(r: ClientType):
    r.set("key", 5)
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", -10, "LBOUND", 0) == [5, 0]


def test_increx_lbound_saturate(r: ClientType):
    r.set("key", 5)
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", -10, "LBOUND", 0, "SATURATE") == [0, -5]


def test_increx_byfloat_bounds(r: ClientType):
    r.set("key", 5)
    assert _as_floats(testtools.raw_command(r, "INCREX", "key", "BYFLOAT", 2.5, "UBOUND", 7.4)) == [5.0, 0.0]
    assert _as_floats(testtools.raw_command(r, "INCREX", "key", "BYFLOAT", 2.5, "UBOUND", 7.4, "SATURATE")) == [
        7.4,
        2.4,
    ]


def test_increx_int_overflow(r: ClientType):
    r.set("key", 2**63 - 2)
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 5) == [2**63 - 2, 0]
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 5, "SATURATE") == [2**63 - 1, 1]


def test_increx_skip_does_not_create_key(r: ClientType):
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 10, "UBOUND", 5) == [0, 0]
    assert r.exists("key") == 0


def test_increx_expiration(r: ClientType):
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "EX", 100) == [1, 1]
    assert 90 < r.ttl("key") <= 100
    # Without an expiration option, the existing TTL is preserved
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 1) == [2, 1]
    assert 90 < r.ttl("key") <= 100


def test_increx_enx(r: ClientType):
    r.set("key", 10)
    # ENX sets the TTL since the key has none
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "EX", 100, "ENX") == [11, 1]
    assert 90 < r.ttl("key") <= 100
    # ENX leaves the existing TTL unchanged, but the increment is still applied
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "EX", 10, "ENX") == [12, 1]
    assert 90 < r.ttl("key") <= 100


def test_increx_persist(r: ClientType):
    r.set("key", 5, ex=100)
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "PERSIST") == [6, 1]
    assert r.ttl("key") == -1


def test_increx_skip_leaves_ttl_untouched(r: ClientType):
    r.set("key", 99, ex=100)
    assert testtools.raw_command(r, "INCREX", "key", "BYINT", 5, "UBOUND", 100, "EX", 500) == [99, 0]
    assert 90 < r.ttl("key") <= 100


def test_increx_errors(r: ClientType):
    r.set("key", 5)
    with pytest.raises(Exception, match="LBOUND can't be greater than UBOUND"):
        testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "LBOUND", 10, "UBOUND", 5)
    with pytest.raises(Exception, match="ENX flag requires an expiration"):
        testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "ENX")
    with pytest.raises(Exception, match="syntax error"):
        testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "PERSIST", "ENX")
    with pytest.raises(Exception, match="syntax error"):
        testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "BYFLOAT", 2.5)
    with pytest.raises(Exception, match="syntax error"):
        testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "EX", 5, "PX", 500)
    with pytest.raises(Exception, match="invalid expire time"):
        testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "EX", -5)
    with pytest.raises(Exception, match="LBOUND is not an integer or out of range"):
        testtools.raw_command(r, "INCREX", "key", "BYINT", 1, "LBOUND", 1.5)
    with pytest.raises(Exception, match="LBOUND is not a valid float"):
        testtools.raw_command(r, "INCREX", "key", "BYFLOAT", 1.5, "LBOUND", "abc")
