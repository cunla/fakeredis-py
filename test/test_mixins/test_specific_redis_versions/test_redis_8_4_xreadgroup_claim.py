"""Tests for the `XREADGROUP ... CLAIM min-idle-time` option introduced in Redis 8.4.

See https://github.com/cunla/fakeredis-py/issues/527
"""

import time

import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test import testtools
from test.testtools import get_protocol_version, raw_command

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.supported_server_versions(min_redis_ver="8.4"),
        pytest.mark.unsupported_server_types("dragonfly", "valkey"),
    ]
)


def get_stream_message(client: ClientType, stream: str, message_id):
    """Fetch a stream message and format it as a (message_id, fields) pair"""
    response = client.xrange(stream, min=message_id, max=message_id)
    assert len(response) == 1
    return response[0]


def read_entries(r: ClientType, response, stream: str):
    """Extract the per-stream entry list from an xreadgroup response"""
    if get_protocol_version(r) == 3:
        return response[stream.encode()][0]
    assert response[0][0] == stream.encode()
    return response[0][1]


@testtools.run_test_if_redispy_ver("gte", "8.0")
def test_xreadgroup_claim_returns_pending_before_new(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"k1": "v1"})
    m2 = r.xadd(stream, {"k2": "v2"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    time.sleep(0.11)
    m3 = r.xadd(stream, {"k3": "v3"})
    m4 = r.xadd(stream, {"k4": "v4"})

    res = r.xreadgroup(group, consumer, streams={stream: ">"}, claim_min_idle_time=100)
    entries = read_entries(r, res, stream)

    assert len(entries) == 4
    # Claimed pending entries come first (longest idle first), then new entries
    assert [entry[0] for entry in entries] == [m1, m2, m3, m4]
    for entry, expected_msg in zip(entries, [m1, m2, m3, m4]):
        assert (entry[0], entry[1]) == get_stream_message(r, stream, expected_msg)
    # Claimed entries report their idle time and previous delivery count
    assert int(entries[0][2]) >= 100 and int(entries[0][3]) == 1
    assert int(entries[1][2]) >= 100 and int(entries[1][3]) == 1
    # New entries report 0 for both
    assert int(entries[2][2]) == 0 and int(entries[2][3]) == 0
    assert int(entries[3][2]) == 0 and int(entries[3][3]) == 0

    # All four messages remain in the PEL until acknowledged
    assert len(r.xpending_range(stream, group, min="-", max="+", count=10)) == 4


@testtools.run_test_if_redispy_ver("gte", "8.0")
def test_xreadgroup_claim_min_idle_not_reached_returns_only_new(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    r.xadd(stream, {"k1": "v1"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    m2 = r.xadd(stream, {"k2": "v2"})

    res = r.xreadgroup(group, consumer, streams={stream: ">"}, claim_min_idle_time=60_000)
    entries = read_entries(r, res, stream)
    assert entries == [(m2, {b"k2": b"v2"}, 0, 0)]


@testtools.run_test_if_redispy_ver("gte", "8.0")
def test_xreadgroup_claim_from_other_consumer(r: ClientType):
    stream, group = "stream", "group"
    m1 = r.xadd(stream, {"k1": "v1"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, "consumer1", streams={stream: ">"})
    time.sleep(0.11)

    res = r.xreadgroup(group, "consumer2", streams={stream: ">"}, claim_min_idle_time=100)
    entries = read_entries(r, res, stream)
    assert len(entries) == 1
    assert (entries[0][0], entries[0][1]) == (m1, {b"k1": b"v1"})
    assert int(entries[0][2]) >= 100
    assert int(entries[0][3]) == 1

    # Ownership moved to consumer2 and the delivery counter was incremented
    pending = r.xpending_range(stream, group, min="-", max="+", count=10)
    assert len(pending) == 1
    assert pending[0]["consumer"] == b"consumer2"
    assert pending[0]["times_delivered"] == 2


@testtools.run_test_if_redispy_ver("gte", "8.0")
def test_xreadgroup_claim_count_limits_claimed_and_new(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    pending_ids = [r.xadd(stream, {"k": str(i)}) for i in range(3)]
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    time.sleep(0.11)
    new_ids = [r.xadd(stream, {"k": str(i)}) for i in range(3, 6)]

    res = r.xreadgroup(group, consumer, streams={stream: ">"}, count=4, claim_min_idle_time=100)
    entries = read_entries(r, res, stream)
    # COUNT limits the total; claimed entries take priority over new ones
    assert [entry[0] for entry in entries] == pending_ids + new_ids[:1]


@testtools.run_test_if_redispy_ver("gte", "8.0")
def test_xreadgroup_claim_ignored_for_history_read(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"k1": "v1"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    time.sleep(0.11)

    # With an explicit ID the consumer history is served and CLAIM is ignored
    res = r.xreadgroup(group, consumer, streams={stream: "0"}, claim_min_idle_time=100)
    entries = read_entries(r, res, stream)
    assert entries == [(m1, {b"k1": b"v1"})]


@testtools.run_test_if_redispy_ver("gte", "8.0")
def test_xreadgroup_claim_multiple_streams(r: ClientType):
    stream1, stream2, group, consumer = "stream1", "stream2", "group", "consumer"
    m1 = r.xadd(stream1, {"k1": "v1"})
    m2 = r.xadd(stream2, {"k2": "v2"})
    r.xgroup_create(stream1, group, 0)
    r.xgroup_create(stream2, group, 0)
    r.xreadgroup(group, consumer, streams={stream1: ">", stream2: ">"})
    time.sleep(0.11)
    m3 = r.xadd(stream1, {"k3": "v3"})

    res = r.xreadgroup(group, consumer, streams={stream1: ">", stream2: ">"}, claim_min_idle_time=100)
    if get_protocol_version(r) == 3:
        stream1_entries, stream2_entries = res[stream1.encode()][0], res[stream2.encode()][0]
    else:
        assert [row[0] for row in res] == [stream1.encode(), stream2.encode()]
        stream1_entries, stream2_entries = res[0][1], res[1][1]
    assert [entry[0] for entry in stream1_entries] == [m1, m3]
    assert int(stream1_entries[0][2]) >= 100 and int(stream1_entries[0][3]) == 1
    assert int(stream1_entries[1][2]) == 0 and int(stream1_entries[1][3]) == 0
    assert [entry[0] for entry in stream2_entries] == [m2]
    assert int(stream2_entries[0][2]) >= 100 and int(stream2_entries[0][3]) == 1


@testtools.run_test_if_redispy_ver("gte", "8.0")
def test_xreadgroup_claim_noack_keeps_claimed_in_pel(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"k1": "v1"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    time.sleep(0.11)
    r.xadd(stream, {"k2": "v2"})

    res = r.xreadgroup(group, consumer, streams={stream: ">"}, noack=True, claim_min_idle_time=100)
    entries = read_entries(r, res, stream)
    assert len(entries) == 2
    # NOACK applies only to the new entry; the claimed entry stays in the PEL
    pending = r.xpending_range(stream, group, min="-", max="+", count=10)
    assert [p["message_id"] for p in pending] == [m1]


@testtools.run_test_if_redispy_ver("gte", "8.0")
def test_xreadgroup_claim_issue_527(r: ClientType):
    r.xgroup_create(b"test_stream", b"test_group", id="$", mkstream=True)
    r.xadd(b"test_stream", {b"field1": b"value1"})
    r.xreadgroup(b"test_group", b"test_consumer", {b"test_stream": b">"}, count=10, block=1)

    r.xadd(b"test_stream", {b"field1": b"value2"})
    out = r.xreadgroup(
        b"test_group",
        b"test_consumer",
        {b"test_stream": b">"},
        count=10,
        block=1,
        claim_min_idle_time=0,
    )
    entries = read_entries(r, out, "test_stream")
    assert len(entries) == 2
    assert [entry[1] for entry in entries] == [{b"field1": b"value1"}, {b"field1": b"value2"}]


def test_xreadgroup_claim_raw_response_shape(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"k1": "v1"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    time.sleep(0.11)
    m2 = r.xadd(stream, {"k2": "v2"})

    res = raw_command(r, "XREADGROUP", "GROUP", group, consumer, "CLAIM", 100, "STREAMS", stream, ">")
    entries = res[stream.encode()] if get_protocol_version(r) == 3 else res[0][1]
    assert len(entries) == 2
    claimed, new = entries
    assert claimed[0] == m1 and claimed[1] == [b"k1", b"v1"] and claimed[2] >= 100 and claimed[3] == 1
    assert new[0] == m2 and new[1] == [b"k2", b"v2"] and new[2] == 0 and new[3] == 0


def test_xreadgroup_claim_negative_min_idle_time(r: ClientType):
    stream, group = "stream", "group"
    r.xadd(stream, {"k1": "v1"})
    r.xgroup_create(stream, group, 0)
    with pytest.raises(Exception, match="min-idle-time must be a positive integer") as ctx:
        raw_command(r, "XREADGROUP", "GROUP", group, "consumer", "CLAIM", -1, "STREAMS", stream, ">")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.supported_server_versions(min_redis_ver="8.7.2")
def test_xreadgroup_claim_nacked_entries_first(r: ClientType):
    stream, group, consumer = "stream", "group", "consumer"
    m1 = r.xadd(stream, {"k1": "v1"})
    m2 = r.xadd(stream, {"k2": "v2"})
    r.xgroup_create(stream, group, 0)
    r.xreadgroup(group, consumer, streams={stream: ">"})
    raw_command(r, "XNACK", stream, group, "FAIL", "IDS", 1, m2)

    # XNACK-released entries are immediately claimable regardless of min-idle-time,
    # and are reported before other idle pending entries
    res = raw_command(r, "XREADGROUP", "GROUP", group, consumer, "CLAIM", 60_000, "STREAMS", stream, ">")
    entries = res[stream.encode()] if get_protocol_version(r) == 3 else res[0][1]
    assert [entry[0] for entry in entries] == [m2]
    assert entries[0][3] == 1

    pending = r.xpending_range(stream, group, min="-", max="+", count=10)
    assert {p["message_id"]: p["consumer"] for p in pending} == {m1: consumer.encode(), m2: consumer.encode()}
