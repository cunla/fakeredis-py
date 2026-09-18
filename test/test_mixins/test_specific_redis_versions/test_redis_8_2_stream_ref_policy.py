"""Tests for the `KEEPREF | DELREF | ACKED` consumer-group reference policies introduced in Redis 8.2.

See https://github.com/cunla/fakeredis-py/issues/583
"""

from __future__ import annotations

import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test import testtools

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("dragonfly", "valkey", "kividb"),
        pytest.mark.supported_server_versions(min_redis_ver="8.2"),
    ]
)

REF_POLICIES = ["KEEPREF", "DELREF", "ACKED"]


def _setup_stream(r: ClientType) -> None:
    """Stream `s` with entries 1-0..10-0; group `g` has delivered 1-0..6-0 to consumer `c`, which acked 1-0 and 3-0.

    That leaves 2-0, 4-0, 5-0 and 6-0 pending, and 7-0..10-0 not yet delivered.
    """
    for i in range(1, 11):
        r.xadd("s", {"f": i}, id=f"{i}-0")
    r.xgroup_create("s", "g", 0)
    r.xreadgroup("g", "c", {"s": ">"}, count=6)
    r.xack("s", "g", "1-0", "3-0")


def _ids(r: ClientType) -> list[bytes]:
    return [entry[0] for entry in r.xrange("s")]


def _pending_ids(r: ClientType) -> list[bytes]:
    return [p["message_id"] for p in r.xpending_range("s", "g", min="-", max="+", count=100)]


@testtools.run_test_if_redispy_ver("gte", "6.3.0")
@pytest.mark.parametrize("ref_policy", REF_POLICIES)
def test_xadd_with_ref_policy(r: ClientType, ref_policy: str):
    for i in range(20):
        r.xadd("s", {"f": i}, maxlen=10, approximate=False, ref_policy=ref_policy)
    assert r.xlen("s") == 10


@testtools.run_test_if_redispy_ver("gte", "6.3.0")
@pytest.mark.parametrize("ref_policy", REF_POLICIES)
def test_xtrim_with_ref_policy(r: ClientType, ref_policy: str):
    for i in range(20):
        r.xadd("s", {"f": i})
    assert r.xtrim("s", maxlen=10, approximate=False, ref_policy=ref_policy) == 10
    assert r.xlen("s") == 10


def test_xtrim_keepref_keeps_pending_entries(r: ClientType):
    _setup_stream(r)
    assert testtools.raw_command(r, "XTRIM", "s", "MAXLEN", "=", 3, "KEEPREF") == 7
    assert _ids(r) == [b"8-0", b"9-0", b"10-0"]
    assert _pending_ids(r) == [b"2-0", b"4-0", b"5-0", b"6-0"]


def test_xtrim_delref_removes_pending_entries(r: ClientType):
    _setup_stream(r)
    assert testtools.raw_command(r, "XTRIM", "s", "MAXLEN", "=", 3, "DELREF") == 7
    assert _ids(r) == [b"8-0", b"9-0", b"10-0"]
    assert _pending_ids(r) == []
    assert r.xinfo_consumers("s", "g")[0]["pending"] == 0


def test_xtrim_acked_skips_referenced_entries(r: ClientType):
    _setup_stream(r)
    # Only the acknowledged entries go: the pending ones and those not yet delivered stay, even though that leaves the
    # stream longer than MAXLEN.
    assert testtools.raw_command(r, "XTRIM", "s", "MAXLEN", "=", 3, "ACKED") == 2
    assert _ids(r) == [b"2-0", b"4-0", b"5-0", b"6-0", b"7-0", b"8-0", b"9-0", b"10-0"]
    assert _pending_ids(r) == [b"2-0", b"4-0", b"5-0", b"6-0"]


@pytest.mark.parametrize(
    "ref_policy,trimmed,remaining,pending",
    [
        ("KEEPREF", 8, [b"9-0", b"10-0"], [b"2-0", b"4-0", b"5-0", b"6-0"]),
        ("DELREF", 8, [b"9-0", b"10-0"], []),
        (
            "ACKED",
            2,
            [b"2-0", b"4-0", b"5-0", b"6-0", b"7-0", b"8-0", b"9-0", b"10-0"],
            [b"2-0", b"4-0", b"5-0", b"6-0"],
        ),
    ],
)
def test_xtrim_minid_with_ref_policy(r: ClientType, ref_policy, trimmed, remaining, pending):
    _setup_stream(r)
    assert testtools.raw_command(r, "XTRIM", "s", "MINID", "=", "9-0", ref_policy) == trimmed
    assert _ids(r) == remaining
    assert _pending_ids(r) == pending


@pytest.mark.parametrize("ref_policy,trimmed,pending", [("KEEPREF", 200, 30), ("DELREF", 240, 0), ("ACKED", 120, 30)])
def test_xtrim_approximate_with_ref_policy(r: ClientType, real_server_details, ref_policy, trimmed, pending):
    pipe = r.pipeline(transaction=False)
    for i in range(1, 251):  # nodes of 100, 100 and 50 entries
        pipe.xadd("s", {"f": i}, id=f"{i}-1")
    pipe.execute()
    r.xgroup_create("s", "g", 0)
    r.xreadgroup("g", "c", {"s": ">"}, count=150)
    r.xack("s", "g", *[f"{i}-1" for i in range(1, 121)])
    if ref_policy != "KEEPREF" and real_server_details.server_version < (8, 6):
        # Approximate trimming used to drop whole nodes only, which DELREF and ACKED never do; since 8.6 they go
        # through a node's entries one by one instead.
        trimmed, pending = 0, 30
    assert testtools.raw_command(r, "XTRIM", "s", "MAXLEN", "~", 10, ref_policy) == trimmed
    assert r.xlen("s") == 250 - trimmed
    assert r.xpending("s", "g")["pending"] == pending


def test_xtrim_acked_without_groups_trims_everything(r: ClientType):
    for i in range(1, 11):
        r.xadd("s", {"f": i}, id=f"{i}-0")
    assert testtools.raw_command(r, "XTRIM", "s", "MAXLEN", "=", 3, "ACKED") == 7
    assert _ids(r) == [b"8-0", b"9-0", b"10-0"]


def test_xtrim_acked_keeps_entries_a_group_has_not_read(r: ClientType):
    for i in range(1, 11):
        r.xadd("s", {"f": i}, id=f"{i}-0")
    r.xgroup_create("s", "at-end", "$")
    r.xgroup_create("s", "behind", "4-0")
    # "at-end" references nothing, but "behind" has yet to read 5-0 onwards.
    assert testtools.raw_command(r, "XTRIM", "s", "MAXLEN", "=", 3, "ACKED") == 4
    assert _ids(r) == [b"5-0", b"6-0", b"7-0", b"8-0", b"9-0", b"10-0"]


def test_xadd_delref(r: ClientType):
    for i in range(1, 6):
        r.xadd("s", {"f": i}, id=f"{i}-0")
    r.xgroup_create("s", "g", 0)
    r.xreadgroup("g", "c", {"s": ">"})
    assert testtools.raw_command(r, "XADD", "s", "DELREF", "MAXLEN", "=", 2, "6-0", "f", 6) == b"6-0"
    assert _ids(r) == [b"5-0", b"6-0"]
    assert _pending_ids(r) == [b"5-0"]
    assert r.xinfo_consumers("s", "g")[0]["pending"] == 1


def test_xadd_acked(r: ClientType):
    for i in range(1, 6):
        r.xadd("s", {"f": i}, id=f"{i}-0")
    r.xgroup_create("s", "g", 0)
    r.xreadgroup("g", "c", {"s": ">"}, count=3)
    r.xack("s", "g", "2-0")
    assert testtools.raw_command(r, "XADD", "s", "MAXLEN", "=", 2, "ACKED", "6-0", "f", 6) == b"6-0"
    assert _ids(r) == [b"1-0", b"3-0", b"4-0", b"5-0", b"6-0"]
    assert _pending_ids(r) == [b"1-0", b"3-0"]


def test_ref_policy_position_and_case(r: ClientType):
    for i in range(1, 6):
        r.xadd("s", {"f": i}, id=f"{i}-0")
    assert testtools.raw_command(r, "XADD", "s", "keepref", "NOMKSTREAM", "MAXLEN", 5, "6-0", "f", 6) == b"6-0"
    assert testtools.raw_command(r, "XADD", "s", "MAXLEN", 5, "Acked", "7-0", "f", 7) == b"7-0"
    assert testtools.raw_command(r, "XTRIM", "s", "delref", "MAXLEN", 4) == 1
    assert testtools.raw_command(r, "XTRIM", "s", "MINID", "5-0", "ACKED") == 1
    # Without a trimming option there is nothing for the policy to act on.
    assert testtools.raw_command(r, "XADD", "s", "DELREF", "8-0", "f", 8) == b"8-0"
    # A policy name after the entry ID is just a field.
    assert testtools.raw_command(r, "XADD", "s", "9-0", "ACKED", "v") == b"9-0"
    assert _ids(r) == [b"5-0", b"6-0", b"7-0", b"8-0", b"9-0"]


def test_ref_policy_given_twice(r: ClientType):
    r.xadd("s", {"f": 1}, id="1-0")
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "XADD", "s", "KEEPREF", "DELREF", "*", "f", "v")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert str(ctx.value) == "Invalid stream ID specified as stream command argument"
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "XTRIM", "s", "MAXLEN", 1, "ACKED", "DELREF")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert str(ctx.value) == "syntax error"


def test_xadd_ref_policy_without_entry(r: ClientType):
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "XADD", "s", "KEEPREF", "*")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_xdelex_acked_keeps_entries_a_group_has_not_read(r: ClientType):
    for i in range(1, 4):
        r.xadd("s", {"f": i}, id=f"{i}-0")
    r.xgroup_create("s", "g", "1-0")
    res = testtools.raw_command(r, "XDELEX", "s", "ACKED", "IDS", 3, "1-0", "2-0", "3-0")
    assert res == [1, 2, 2]
    assert _ids(r) == [b"2-0", b"3-0"]


def test_xackdel_acked_keeps_entries_another_group_has_not_read(r: ClientType):
    r.xadd("s", {"f": 1}, id="1-0")
    r.xgroup_create("s", "g", 0)
    r.xgroup_create("s", "later", 0)
    r.xreadgroup("g", "c", {"s": ">"})
    # "later" has not read 1-0 yet, so acknowledging it in "g" is not enough to delete it.
    assert testtools.raw_command(r, "XACKDEL", "s", "g", "ACKED", "IDS", 1, "1-0") == [2]
    assert _ids(r) == [b"1-0"]
    assert _pending_ids(r) == []
