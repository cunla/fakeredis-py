import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test import testtools

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.supported_redis_versions(min_ver="8.6"),
        testtools.run_test_if_redispy_ver("gte", "7.2"),
    ]
)


def test_xadd_idmp(r: ClientType):
    stream = "stream"

    # XADD with IDMP - first write
    message_id1 = r.xadd(stream, {"field1": "value1"}, idmp=("producer1", b"msg1"))

    # Test XADD with IDMP - duplicate write returns same ID
    message_id2 = r.xadd(stream, {"field1": "value1"}, idmp=("producer1", b"msg1"))
    assert message_id1 == message_id2

    # Test XADD with IDMP - different iid creates new entry
    message_id3 = r.xadd(stream, {"field1": "value1"}, idmp=("producer1", b"msg2"))
    assert message_id3 != message_id1

    # Test XADD with IDMP - different producer creates new entry
    message_id4 = r.xadd(stream, {"field1": "value1"}, idmp=("producer2", b"msg1"))
    assert message_id4 != message_id1

    # Test XADD with IDMP - shorter binary iid
    r.xadd(stream, {"field1": "value1"}, idmp=("producer1", b"\x01"))

    # Verify stream has 4 entries
    assert r.xlen(stream) == 4


def test_xadd_idmp_validation(r: ClientType):
    stream = "stream"

    # Test error: both idmpauto and idmp specified
    with pytest.raises(Exception) as ctx:
        r.xadd(stream, {"foo": "bar"}, idmpauto="producer1", idmp=("producer1", b"msg1"))

    assert isinstance(ctx.value, (redis.DataError, valkey.DataError))
    # Test error: idmpauto with explicit id
    with pytest.raises(Exception) as ctx:
        r.xadd(stream, {"foo": "bar"}, id="1234567890-0", idmpauto="producer1")

    assert isinstance(ctx.value, (redis.DataError, valkey.DataError))
    # Test error: idmp with explicit id
    with pytest.raises(Exception) as ctx:
        r.xadd(stream, {"foo": "bar"}, id="1234567890-0", idmp=("producer1", b"msg1"))

    assert isinstance(ctx.value, (redis.DataError, valkey.DataError))
    # Test error: idmp not a tuple
    with pytest.raises(Exception) as ctx:
        r.xadd(stream, {"foo": "bar"}, idmp="invalid")

    assert isinstance(ctx.value, (redis.DataError, valkey.DataError))
    # Test error: idmp tuple with wrong number of elements
    with pytest.raises(Exception) as ctx:
        r.xadd(stream, {"foo": "bar"}, idmp=("producer1",))

    assert isinstance(ctx.value, (redis.DataError, valkey.DataError))
    # Test error: idmp tuple with wrong number of elements
    with pytest.raises(Exception) as ctx:
        r.xadd(stream, {"foo": "bar"}, idmp=("producer1", b"msg1", "extra"))

    assert isinstance(ctx.value, (redis.DataError, valkey.DataError))


def test_xinfo_stream_idempotent_fields(r: ClientType):
    stream = "stream"

    # Create stream with regular entry
    r.xadd(stream, {"foo": "bar"})
    info = r.xinfo_stream(stream)

    # Verify new idempotent producer fields are present with default values
    assert "idmp-duration" in info
    assert "idmp-maxsize" in info
    assert "pids-tracked" in info
    assert "iids-tracked" in info
    assert "iids-added" in info
    assert "iids-duplicates" in info

    # Default values (before any idempotent entries)
    assert info["pids-tracked"] == 0
    assert info["iids-tracked"] == 0
    assert info["iids-added"] == 0
    assert info["iids-duplicates"] == 0

    # Add idempotent entry
    r.xadd(stream, {"field1": "value1"}, idmpauto="producer1")
    info = r.xinfo_stream(stream)

    # After adding idempotent entry
    assert info["pids-tracked"] == 1  # One producer tracked
    assert info["iids-tracked"] == 1  # One iid tracked
    assert info["iids-added"] == 1  # One idempotent entry added
    assert info["iids-duplicates"] == 0  # No duplicates yet

    # Add duplicate entry
    r.xadd(stream, {"field1": "value1"}, idmpauto="producer1")
    info = r.xinfo_stream(stream)

    # After duplicate
    assert info["pids-tracked"] == 1  # Still one producer
    assert info["iids-tracked"] == 1  # Still one iid (duplicate doesn't add new)
    assert info["iids-added"] == 1  # Still one unique entry
    assert info["iids-duplicates"] == 1  # One duplicate detected

    # Add entry from different producer
    r.xadd(stream, {"field2": "value2"}, idmpauto="producer2")
    info = r.xinfo_stream(stream)

    # After second producer
    assert info["pids-tracked"] == 2  # Two producers tracked
    assert info["iids-tracked"] == 2  # Two iids tracked
    assert info["iids-added"] == 2  # Two unique entries
    assert info["iids-duplicates"] == 1  # Still one duplicate


def test_xinfo_stream_idempotent_fields_config(r: ClientType):
    stream = "stream"
    r.xadd(stream, {"foo": "bar"})
    r.xcfgset(stream, 300)
    info = r.xinfo_stream(stream)
    assert "idmp-duration" in info
    assert "idmp-maxsize" in info
    assert info["idmp-duration"] == 300

    with pytest.raises(Exception) as excinfo:
        testtools.raw_command(r, "XCFGSET", stream, "idmp-duration", -1)
    assert isinstance(excinfo.value, (redis.ResponseError, valkey.ResponseError))
    assert str(excinfo.value) == "IDMP-DURATION must be between 1 and 86400 seconds"

    with pytest.raises(Exception) as excinfo:
        testtools.raw_command(r, "XCFGSET", stream, "idmp-maxsize", -1)
    assert isinstance(excinfo.value, (redis.ResponseError, valkey.ResponseError))
    assert str(excinfo.value) == "IDMP-MAXSIZE must be between 1 and 10000 entries"
