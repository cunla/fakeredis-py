import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test import testtools

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("dragonfly", "valkey"),
        pytest.mark.supported_server_versions(min_redis_ver="8.7.2"),
    ]
)


def test_xnack_silent(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    m2 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    result = testtools.raw_command(r, "XNACK", stream, group, "SILENT", "IDS", 2, m1, m2)
    assert result == 2


def test_xnack_fail(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    result = testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 1, m1)
    assert result == 1


def test_xnack_fatal(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    result = testtools.raw_command(r, "XNACK", stream, group, "FATAL", "IDS", 1, m1)
    assert result == 1


def test_xnack_multiple_ids(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    m2 = r.xadd(stream, {"foo": "bar"})
    m3 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    result = testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 3, m1, m2, m3)
    assert result == 3


def test_xnack_some_ids_not_in_pel(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    m2 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    # Only m1 and m2 are in PEL; "999999-0" is not
    result = testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 3, m1, m2, b"999999-0")
    assert result == 2


def test_xnack_retrycount(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    # Explicit retrycount overrides the mode's counter adjustment
    result = testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 1, m1, "RETRYCOUNT", 5)
    assert result == 1


def test_xnack_force(r: ClientType):
    stream, group = "stream", "group"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    # m1 is not in PEL (never read); FORCE creates an unowned PEL entry
    result = testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 1, m1, "FORCE")
    assert result == 1


def test_xnack_invalid_mode(r: ClientType):
    stream, group = "stream", "group"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "XNACK", stream, group, "INVALID", "IDS", 1, m1)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_xnack_no_ids_block(r: ClientType):
    stream, group = "stream", "group"
    r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "XNACK", stream, group, "FAIL")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_xidmprecord_basic(r: ClientType):
    stream = "stream"
    m1 = r.xadd(stream, {"f": "1"})

    res = testtools.raw_command(r, "XIDMPRECORD", stream, b"producer1", b"idem1", m1)
    assert res == b"OK"

    # Idempotent: same mapping returns OK
    res = testtools.raw_command(r, "XIDMPRECORD", stream, b"producer1", b"idem1", m1)
    assert res == b"OK"


def test_xidmprecord_conflict(r: ClientType):
    stream = "stream"
    m1 = r.xadd(stream, {"f": "1"})
    m2 = r.xadd(stream, {"f": "2"})
    testtools.raw_command(r, "XIDMPRECORD", stream, b"producer1", b"idem1", m1)

    # Same pid/iid mapped to a different stream ID must raise an error
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "XIDMPRECORD", stream, b"producer1", b"idem1", m2)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_xidmprecord_deleted_entry(r: ClientType):
    stream = "stream"
    m1 = r.xadd(stream, {"f": "1"})
    r.xdel(stream, m1)

    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "XIDMPRECORD", stream, b"producer1", b"idem1", m1)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_xidmprecord_nonexistent_key(r: ClientType):
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "XIDMPRECORD", "no-such-key", b"p", b"i", b"1-1")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_xidmprecord_multiple_producers(r: ClientType):
    """Different producer IDs share the same stream; each gets its own namespace."""
    stream = "stream"
    m1 = r.xadd(stream, {"f": "1"})
    m2 = r.xadd(stream, {"f": "2"})

    res = testtools.raw_command(r, "XIDMPRECORD", stream, b"prod-A", b"iid-1", m1)
    assert res == b"OK"
    res = testtools.raw_command(r, "XIDMPRECORD", stream, b"prod-B", b"iid-1", m2)
    assert res == b"OK"

    # prod-A/iid-1 still maps to m1 (namespace isolation)
    res = testtools.raw_command(r, "XIDMPRECORD", stream, b"prod-A", b"iid-1", m1)
    assert res == b"OK"


def test_xidmprecord_multiple_iids_same_producer(r: ClientType):
    """One producer can register several distinct iid→entry mappings."""
    stream = "stream"
    m1 = r.xadd(stream, {"f": "1"})
    m2 = r.xadd(stream, {"f": "2"})

    testtools.raw_command(r, "XIDMPRECORD", stream, b"prod", b"iid-1", m1)
    testtools.raw_command(r, "XIDMPRECORD", stream, b"prod", b"iid-2", m2)

    # Both idempotent re-registrations succeed
    assert testtools.raw_command(r, "XIDMPRECORD", stream, b"prod", b"iid-1", m1) == b"OK"
    assert testtools.raw_command(r, "XIDMPRECORD", stream, b"prod", b"iid-2", m2) == b"OK"


def test_xidmprecord_wrong_key_type(r: ClientType):
    """Calling XIDMPRECORD on a non-stream key raises a type error."""
    r.set("not-a-stream", "value")
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "XIDMPRECORD", "not-a-stream", b"p", b"i", b"1-1")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_xnack_releases_entry_as_unowned(r: ClientType):
    """A NACKed entry becomes unowned with idle time -1, and leaves the consumer's pending count."""
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    m2 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})

    assert testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 1, m1) == 1

    pending = r.xpending_range(stream, group, min="-", max="+", count=10)
    by_id = {p["message_id"]: p for p in pending}
    assert by_id[m1]["consumer"] == b""
    assert by_id[m1]["time_since_delivered"] == -1
    assert by_id[m1]["times_delivered"] == 1
    assert by_id[m2]["consumer"] == consumer.encode()

    # The summary counts the NACKed entry in the total, but not under any consumer
    summary = r.xpending(stream, group)
    assert summary["pending"] == 2
    assert summary["consumers"] == [{"name": consumer.encode(), "pending": 1}]


def test_xnack_silent_decrements_counter(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})

    assert testtools.raw_command(r, "XNACK", stream, group, "SILENT", "IDS", 1, m1) == 1
    pending = r.xpending_range(stream, group, min="-", max="+", count=10)
    assert pending[0]["times_delivered"] == 0


def test_xnack_fatal_sets_counter_to_max(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})

    assert testtools.raw_command(r, "XNACK", stream, group, "FATAL", "IDS", 1, m1) == 1
    pending = r.xpending_range(stream, group, min="-", max="+", count=10)
    assert pending[0]["times_delivered"] == 2**63 - 1


def test_xnack_retrycount_sets_counter(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})

    assert testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 1, m1, "RETRYCOUNT", 42) == 1
    pending = r.xpending_range(stream, group, min="-", max="+", count=10)
    assert pending[0]["times_delivered"] == 42


def test_xnack_force_creates_unowned_entry(r: ClientType):
    """FORCE creates a PEL entry with delivery counter 0 for an entry that was never delivered."""
    stream, group = "stream", "group"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)

    assert testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 1, m1, "FORCE") == 1
    pending = r.xpending_range(stream, group, min="-", max="+", count=10)
    assert pending[0]["consumer"] == b""
    assert pending[0]["times_delivered"] == 0

    # FORCE does not create entries for IDs missing from the stream
    assert testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 1, b"999999-0", "FORCE") == 0


def test_xnack_released_entry_is_claimable(r: ClientType):
    """A NACKed entry can be claimed immediately, regardless of min-idle-time."""
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})

    assert testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 1, m1) == 1
    claimed = r.xclaim(stream, group, "other-consumer", min_idle_time=100000, message_ids=[m1])
    assert [record[0] for record in claimed] == [m1]


def test_xnack_invalid_mode_message(r: ClientType):
    stream, group = "stream", "group"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    with pytest.raises(Exception, match="mode must be SILENT, FAIL, or FATAL"):
        testtools.raw_command(r, "XNACK", stream, group, "BOGUS", "IDS", 1, m1)


def test_xack_after_xnack_releases_the_entry(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})

    # XNACK leaves the entry pending but unowned, so XACK has no consumer to charge it back to.
    assert testtools.raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 1, m1) == 1
    assert r.xack(stream, group, m1) == 1
    assert r.xpending(stream, group)["pending"] == 0


def test_xnack_nogroup_errors(r: ClientType):
    stream, group = "stream", "group"
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xgroup_create(stream, group, 0)
    with pytest.raises(Exception, match="NOGROUP No such key 'stream' or consumer group 'nogroup'"):
        testtools.raw_command(r, "XNACK", stream, "nogroup", "FAIL", "IDS", 1, m1)
    with pytest.raises(Exception, match="NOGROUP No such key 'nokey' or consumer group 'group'"):
        testtools.raw_command(r, "XNACK", "nokey", group, "FAIL", "IDS", 1, m1)
