"""Tests for stream commands introduced in Redis 8.7.2 / 8.8:
XNACK, XDELEX, XACKDEL, XIDMPRECORD.

XNACK tests are adapted from redis-py test_commands.py @ ea76084.
"""

import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test import testtools

pytestmark = [
    pytest.mark.supported_redis_versions(min_ver="8.7.2"),
]


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


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xdelex_keepref(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    m2 = r.xadd(stream, {"f": "2"})
    m3 = r.xadd(stream, {"f": "3"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})

    # KEEPREF: delete from stream but preserve PEL references
    res = testtools.raw_command(r, "XDELEX", stream, "KEEPREF", "IDS", 2, m1, m2)
    assert res == [1, 1]
    assert r.xlen(stream) == 1
    # PEL entries must still exist for the deleted IDs
    pending = r.xpending_range(stream, group, min="-", max="+", count=10)
    pending_ids = [p["message_id"] for p in pending]
    assert m1 in pending_ids
    assert m2 in pending_ids
    assert m3 in pending_ids


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xdelex_delref(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    m2 = r.xadd(stream, {"f": "2"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})

    # DELREF: delete from stream AND strip all PEL references
    res = testtools.raw_command(r, "XDELEX", stream, "DELREF", "IDS", 1, m1)
    assert res == [1]
    assert r.xlen(stream) == 1
    pending = r.xpending_range(stream, group, min="-", max="+", count=10)
    pending_ids = [p["message_id"] for p in pending]
    assert m1 not in pending_ids
    assert m2 in pending_ids


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xdelex_acked(r: ClientType):
    stream, group1, group2, consumer = "stream", "group1", "group2", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    r.xgroup_create(stream, group1, 0)
    r.xgroup_create(stream, group2, 0)
    r.xreadgroup(group1, consumer, streams={stream: ">"})
    r.xreadgroup(group2, consumer, streams={stream: ">"})

    # m1 is in both PELs — must not be deleted (returns 2)
    res = testtools.raw_command(r, "XDELEX", stream, "ACKED", "IDS", 1, m1)
    assert res == [2]
    assert r.xlen(stream) == 1

    # After both groups ack, ACKED mode can delete
    r.xack(stream, group1, m1)
    r.xack(stream, group2, m1)
    res = testtools.raw_command(r, "XDELEX", stream, "ACKED", "IDS", 1, m1)
    assert res == [1]
    assert r.xlen(stream) == 0


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xdelex_nonexistent(r: ClientType):
    stream = "stream"
    r.xadd(stream, {"f": "1"})

    # Non-existent ID returns -1
    res = testtools.raw_command(r, "XDELEX", stream, "IDS", 1, b"99999-0")
    assert res == [-1]

    # Non-existent key returns -1 per ID
    res = testtools.raw_command(r, "XDELEX", "no-such-key", "IDS", 2, b"1-1", b"2-2")
    assert res == [-1, -1]


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xdelex_default_mode_is_keepref(r: ClientType):
    """Omitting the mode flag defaults to KEEPREF behaviour."""
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})

    res = testtools.raw_command(r, "XDELEX", stream, "IDS", 1, m1)
    assert res == [1]
    assert r.xlen(stream) == 0
    # PEL entry preserved (KEEPREF default)
    assert r.xpending(stream, group)["pending"] == 1


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xdelex_mixed_results(r: ClientType):
    """Per-ID results: 1 deleted, -1 not found, in one call."""
    stream = "stream"
    m1 = r.xadd(stream, {"f": "1"})

    res = testtools.raw_command(r, "XDELEX", stream, "IDS", 3, m1, b"99999-0", b"99999-1")
    assert res == [1, -1, -1]
    assert r.xlen(stream) == 0


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xdelex_delref_updates_pending_count(r: ClientType):
    """DELREF removes the PEL entry so the consumer's pending count drops."""
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    m2 = r.xadd(stream, {"f": "2"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    assert r.xpending(stream, group)["pending"] == 2

    testtools.raw_command(r, "XDELEX", stream, "DELREF", "IDS", 1, m1)
    assert r.xpending(stream, group)["pending"] == 1
    remaining = r.xpending_range(stream, group, min="-", max="+", count=10)
    assert remaining[0]["message_id"] == m2


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xdelex_acked_one_group_still_pending(r: ClientType):
    """ACKED skips deletion when at least one group still holds the entry in PEL."""
    stream, group1, group2, consumer = "stream", "group1", "group2", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    r.xgroup_create(stream, group1, 0)
    r.xgroup_create(stream, group2, 0)
    r.xreadgroup(group1, consumer, streams={stream: ">"})
    r.xreadgroup(group2, consumer, streams={stream: ">"})

    r.xack(stream, group1, m1)  # group1 done, group2 still pending

    res = testtools.raw_command(r, "XDELEX", stream, "ACKED", "IDS", 1, m1)
    assert res == [2]  # cannot delete — group2 still has it
    assert r.xlen(stream) == 1

    r.xack(stream, group2, m1)
    res = testtools.raw_command(r, "XDELEX", stream, "ACKED", "IDS", 1, m1)
    assert res == [1]
    assert r.xlen(stream) == 0


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xackdel_basic(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    r.xadd(stream, {"f": "2"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    assert r.xpending(stream, group)["pending"] == 2

    res = testtools.raw_command(r, "XACKDEL", stream, group, "KEEPREF", "IDS", 1, m1)
    assert res == [1]
    assert r.xlen(stream) == 1
    assert r.xpending(stream, group)["pending"] == 1


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xackdel_delref(r: ClientType):
    stream, group1, group2, consumer = "stream", "group1", "group2", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    r.xgroup_create(stream, group1, 0)
    r.xgroup_create(stream, group2, 0)
    r.xreadgroup(group1, consumer, streams={stream: ">"})
    r.xreadgroup(group2, consumer, streams={stream: ">"})

    # DELREF acks in group1 and removes from all PEL entries (including group2)
    res = testtools.raw_command(r, "XACKDEL", stream, group1, "DELREF", "IDS", 1, m1)
    assert res == [1]
    assert r.xlen(stream) == 0
    assert r.xpending(stream, group1)["pending"] == 0
    assert r.xpending(stream, group2)["pending"] == 0


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xackdel_acked_cross_group(r: ClientType):
    stream, group1, group2, consumer = "stream", "group1", "group2", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    r.xgroup_create(stream, group1, 0)
    r.xgroup_create(stream, group2, 0)
    r.xreadgroup(group1, consumer, streams={stream: ">"})
    r.xreadgroup(group2, consumer, streams={stream: ">"})

    # m1 still in group2's PEL — acked in group1 but cannot delete (returns 2)
    res = testtools.raw_command(r, "XACKDEL", stream, group1, "ACKED", "IDS", 1, m1)
    assert res == [2]
    assert r.xlen(stream) == 1
    assert r.xpending(stream, group1)["pending"] == 0
    assert r.xpending(stream, group2)["pending"] == 1


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xackdel_nonexistent(r: ClientType):
    stream, group = "stream", "group"
    r.xadd(stream, {"f": "1"})
    r.xgroup_create(stream, group, 0)

    # Non-existent ID returns -1
    res = testtools.raw_command(r, "XACKDEL", stream, group, "IDS", 1, b"99999-0")
    assert res == [-1]

    # Non-existent key returns -1
    res = testtools.raw_command(r, "XACKDEL", "no-such-key", group, "IDS", 1, b"1-1")
    assert res == [-1]

    # Non-existent group returns -1
    res = testtools.raw_command(r, "XACKDEL", stream, "no-such-group", "IDS", 1, b"1-1")
    assert res == [-1]


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xackdel_default_mode_is_keepref(r: ClientType):
    """Omitting the mode flag defaults to KEEPREF: entry deleted from stream,
    PEL refs to other groups are preserved."""
    stream, group1, group2, consumer = "stream", "group1", "group2", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    r.xgroup_create(stream, group1, 0)
    r.xgroup_create(stream, group2, 0)
    r.xreadgroup(group1, consumer, streams={stream: ">"})
    r.xreadgroup(group2, consumer, streams={stream: ">"})

    res = testtools.raw_command(r, "XACKDEL", stream, group1, "IDS", 1, m1)
    assert res == [1]
    assert r.xlen(stream) == 0
    assert r.xpending(stream, group1)["pending"] == 0
    # group2's PEL reference is still intact (KEEPREF)
    assert r.xpending(stream, group2)["pending"] == 1


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xackdel_multiple_ids_mixed(r: ClientType):
    """Per-ID results for a batch: 1 acked+deleted, -1 not found."""
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    r.xadd(stream, {"f": "2"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})

    res = testtools.raw_command(r, "XACKDEL", stream, group, "IDS", 2, m1, b"99999-0")
    assert res == [1, -1]
    assert r.xlen(stream) == 1


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xackdel_entry_not_in_pel(r: ClientType):
    """XACKDEL on an entry that exists in the stream but not in this group's PEL
    still deletes it from the stream (ack is a no-op)."""
    stream, group = "stream", "group"
    m1 = r.xadd(stream, {"f": "1"})
    r.xgroup_create(stream, group, 0)
    # Do NOT read — m1 is not in PEL

    res = testtools.raw_command(r, "XACKDEL", stream, group, "KEEPREF", "IDS", 1, m1)
    assert res == [-1]
    assert r.xlen(stream) == 1


@pytest.mark.supported_redis_versions(min_ver="8.2")
def test_xackdel_acked_then_deletable(r: ClientType):
    """Once all groups have acked, ACKED mode can remove the entry."""
    stream, group1, group2, consumer = "stream", "group1", "group2", "consumer"
    m1 = r.xadd(stream, {"f": "1"})
    r.xgroup_create(stream, group1, 0)
    r.xgroup_create(stream, group2, 0)
    r.xreadgroup(group1, consumer, streams={stream: ">"})
    r.xreadgroup(group2, consumer, streams={stream: ">"})

    # group2 acks first, group1 uses XACKDEL ACKED — still blocked
    r.xack(stream, group2, m1)
    res = testtools.raw_command(r, "XACKDEL", stream, group1, "ACKED", "IDS", 1, m1)
    assert res == [1]  # group1 ack removes last reference → deleted
    assert r.xlen(stream) == 0


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
