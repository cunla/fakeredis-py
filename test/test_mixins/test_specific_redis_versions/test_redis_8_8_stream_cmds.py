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


# ---------------------------------------------------------------------------
# XNACK (adapted from redis-py test_commands.py @ ea76084)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# XDELEX
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# XACKDEL
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# XIDMPRECORD
# ---------------------------------------------------------------------------


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
