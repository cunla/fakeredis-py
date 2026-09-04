"""Tests for Redis Array commands (AR*)."""

import pytest

from fakeredis._typing import ClientType
from test import testtools

pytestmark = [
    pytest.mark.supported_server_versions(min_redis_ver="8.8"),
    testtools.run_test_if_redispy_ver("gte", "8.0"),
    pytest.mark.unsupported_server_types("valkey"),
]
try:
    from redis.commands.core import ArrayAggregateOperations, ArrayPredicateType
except ImportError:
    pytest.skip("Array commands are not supported in this redis-py version", allow_module_level=True)

# ── ARSET / ARGET ──────────────────────────────────────────────────────────────


def test_arset_single(r: ClientType):
    assert r.arset("arr", 0, "hello") == 1
    assert r.arget("arr", 0) == b"hello"


def test_arset_multi(r: ClientType):
    assert r.arset("arr", 2, "a", "b", "c") == 3
    assert r.arget("arr", 2) == b"a"
    assert r.arget("arr", 3) == b"b"
    assert r.arget("arr", 4) == b"c"


def test_arset_update_returns_zero(r: ClientType):
    r.arset("arr", 0, "first")
    r.arset("arr", 0, "first")
    assert r.arset("arr", 0, "second") == 0
    assert r.arget("arr", 0) == b"second"


def test_arget_missing_key(r: ClientType):
    assert r.arget("nokey", 0) is None


def test_arget_missing_index(r: ClientType):
    r.arset("arr", 0, "x")
    assert r.arget("arr", 5) is None


# ── ARMSET / ARMGET ────────────────────────────────────────────────────────────


def test_armset_armget(r: ClientType):
    assert r.armset("arr", {0: "alpha", 5: "beta", 100: "gamma"}) == 3
    assert r.armget("arr", 0, 5, 100, 3) == [b"alpha", b"beta", b"gamma", None]


def test_armget_missing_key(r: ClientType):
    assert r.armget("nokey", 0, 1) == [None, None]


# ── ARLEN / ARCOUNT ───────────────────────────────────────────────────────────


def test_arlen_arcount(r: ClientType):
    r.arset("arr", 0, "a")
    r.arset("arr", 5, "b")
    assert r.arlen("arr") == 6  # max_index=5, 5+1=6
    assert r.arcount("arr") == 2


def test_arlen_arcount_missing(r: ClientType):
    assert r.arlen("nokey") == 0
    assert r.arcount("nokey") == 0


# ── ARDEL ─────────────────────────────────────────────────────────────────────


def test_ardel(r: ClientType):
    r.arset("arr", 0, "a")
    r.arset("arr", 1, "b")
    r.arset("arr", 2, "c")
    assert r.ardel("arr", 1) == 1
    assert r.arget("arr", 1) is None
    assert r.arcount("arr") == 2


def test_ardel_multi(r: ClientType):
    r.armset("arr", {0: "a", 1: "b", 2: "c"})
    assert r.ardel("arr", 0, 2) == 2
    assert r.arcount("arr") == 1


def test_ardel_missing_index(r: ClientType):
    r.arset("arr", 0, "x")
    assert r.ardel("arr", 99) == 0


def test_ardel_missing_key(r: ClientType):
    assert r.ardel("nokey", 0) == 0


# ── ARDELRANGE ────────────────────────────────────────────────────────────────


def test_ardelrange(r: ClientType):
    r.armset("arr", {0: "a", 1: "b", 2: "c", 3: "d", 4: "e"})
    assert r.ardelrange("arr", (1, 3)) == 3
    assert r.arcount("arr") == 2
    assert r.arget("arr", 0) == b"a"
    assert r.arget("arr", 4) == b"e"


def test_ardelrange_multi_ranges(r: ClientType):
    r.armset("arr", {0: "a", 1: "b", 2: "c", 3: "d", 4: "e"})
    assert r.ardelrange("arr", (0, 1), (3, 4)) == 4


def test_ardelrange_missing_key(r: ClientType):
    assert r.ardelrange("nokey", (0, 5)) == 0


# ── ARGETRANGE ────────────────────────────────────────────────────────────────


def test_argetrange_forward(r: ClientType):
    r.armset("arr", {0: "a", 1: "b", 3: "d"})
    result = r.argetrange("arr", 0, 3)
    assert result == [b"a", b"b", None, b"d"]


def test_argetrange_reverse(r: ClientType):
    r.armset("arr", {0: "a", 1: "b", 2: "c"})
    result = r.argetrange("arr", 2, 0)
    assert result == [b"c", b"b", b"a"]


def test_argetrange_missing_key(r: ClientType):
    assert r.argetrange("nokey", 0, 5) == [None, None, None, None, None, None]


# ── ARINSERT / ARNEXT / ARSEEK ────────────────────────────────────────────────


def test_arinsert_basic(r: ClientType):
    assert r.arinsert("arr", "alpha") == 0
    assert r.arinsert("arr", "beta") == 1
    assert r.arinsert("arr", "gamma") == 2
    assert r.arget("arr", 0) == b"alpha"
    assert r.arget("arr", 1) == b"beta"
    assert r.arget("arr", 2) == b"gamma"


def test_arinsert_multi(r: ClientType):
    assert r.arinsert("arr", "a", "b", "c") == 2


def test_arnext_new_key(r: ClientType):
    assert r.arnext("nokey") == 0


def test_arnext_after_insert(r: ClientType):
    r.arinsert("arr", "a", "b")
    assert r.arnext("arr") == 2


def test_arseek(r: ClientType):
    r.arinsert("arr", "a", "b")
    assert r.arseek("arr", 10) == 1
    assert r.arnext("arr") == 10
    r.arinsert("arr", "c")
    assert r.arget("arr", 10) == b"c"


def test_arseek_missing_key(r: ClientType):
    assert r.arseek("nokey", 5) == 0


# ── ARRING ────────────────────────────────────────────────────────────────────


def test_arring_basic(r: ClientType):
    r.arring("ring", 3, "v0")
    r.arring("ring", 3, "v1")
    r.arring("ring", 3, "v2")
    assert r.arring("ring", 3, "v3") == 0  # wraps to idx 0
    assert r.arget("ring", 0) == b"v3"
    assert r.arcount("ring") == 3


def test_arring_truncates(r: ClientType):
    r.armset("arr", {0: "a", 5: "b", 9: "c"})
    assert r.arlen("arr") == 10
    r.arring("arr", 3, "x")
    assert r.arlen("arr") <= 3  # truncated to size 3


# ── ARLASTITEMS ───────────────────────────────────────────────────────────────


def test_arlastitems(r: ClientType):
    r.arinsert("log", "first")
    r.arinsert("log", "second")
    r.arinsert("log", "third")
    assert r.arlastitems("log", 2) == [b"second", b"third"]


def test_arlastitems_rev(r: ClientType):
    r.arinsert("log", "first")
    r.arinsert("log", "second")
    r.arinsert("log", "third")
    assert r.arlastitems("log", 2, rev=True) == [b"third", b"second"]


def test_arlastitems_ring(r: ClientType):
    r.arring("ring", 3, "v0")
    r.arring("ring", 3, "v1")
    r.arring("ring", 3, "v2")
    r.arring("ring", 3, "v3")  # overwrites v0 at idx 0
    items = r.arlastitems("ring", 3)
    assert b"v3" in items
    assert b"v0" not in items


def test_arlastitems_missing_key(r: ClientType):
    assert r.arlastitems("nokey", 3) == []


# ── ARSCAN ────────────────────────────────────────────────────────────────────


def test_arscan_basic(r: ClientType):
    r.arset("arr", 0, "a")
    r.arset("arr", 5, "b")
    r.arset("arr", 9, "c")
    result = r.arscan("arr", 0, 10)
    assert result == [[0, b"a"], [5, b"b"], [9, b"c"]]


def test_arscan_limit(r: ClientType):
    r.arset("arr", 0, "a")
    r.arset("arr", 5, "b")
    r.arset("arr", 9, "c")
    result = r.arscan("arr", 0, 10, limit=2)
    assert result == [[0, b"a"], [5, b"b"]]


def test_arscan_missing_key(r: ClientType):
    assert r.arscan("nokey", 0, 10) == []


# ── ARGREP ────────────────────────────────────────────────────────────────────


def test_argrep_exact(r: ClientType):
    r.armset("log", {0: "boot: ok", 1: "warn: disk", 2: "ERROR: cpu", 3: "info: ready"})
    result = r.argrep("log", 0, 3, [(ArrayPredicateType.EXACT, "info: ready")])
    assert result == [3]


def test_argrep_match(r: ClientType):
    r.armset("log", {0: "boot: ok", 1: "warn: disk", 2: "ERROR: cpu", 3: "info: ready", 4: "error: net"})
    result = r.argrep("log", 0, 4, [(ArrayPredicateType.MATCH, "error")], nocase=True)
    assert result == [2, 4]


def test_argrep_withvalues(r: ClientType):
    r.armset("log", {0: "boot: ok", 1: "warn: disk", 2: "ERROR: cpu"})
    result = r.argrep("log", 0, 2, [(ArrayPredicateType.MATCH, "error")], nocase=True, withvalues=True)
    assert result == [[2, b"ERROR: cpu"]]


def test_argrep_glob(r: ClientType):
    r.armset("arr", {0: "warn: disk", 1: "error: cpu", 2: "info: ok"})
    result = r.argrep("arr", 0, 2, [(ArrayPredicateType.GLOB, "warn:*")])
    assert result == [0]


def test_argrep_re(r: ClientType):
    r.armset("arr", {0: "foo123", 1: "bar456", 2: "baz"})
    result = r.argrep("arr", 0, 2, [(ArrayPredicateType.RE, r"[a-z]+\d+")])
    assert 0 in result
    assert 1 in result
    assert 2 not in result


def test_argrep_limit(r: ClientType):
    r.armset("arr", {0: "error: a", 1: "error: b", 2: "error: c"})
    result = r.argrep("arr", 0, 2, [(ArrayPredicateType.MATCH, "error")], limit=2)
    assert len(result) == 2


def test_argrep_missing_key(r: ClientType):
    assert r.argrep("nokey", 0, 10, [(ArrayPredicateType.MATCH, "x")]) == []


# ── AROP ──────────────────────────────────────────────────────────────────────


def test_arop_sum(r: ClientType):
    r.armset("arr", {0: "10", 1: "20", 2: "30"})
    assert r.arop("arr", 0, 2, ArrayAggregateOperations.SUM) == b"60"


def test_arop_min(r: ClientType):
    r.armset("arr", {0: "10", 1: "5", 2: "30"})
    assert r.arop("arr", 0, 2, ArrayAggregateOperations.MIN) == b"5"


def test_arop_max(r: ClientType):
    r.armset("arr", {0: "10", 1: "5", 2: "30"})
    assert r.arop("arr", 0, 2, ArrayAggregateOperations.MAX) == b"30"


def test_arop_used(r: ClientType):
    r.arset("arr", 0, "a")
    r.arset("arr", 5, "b")
    assert r.arop("arr", 0, 9, ArrayAggregateOperations.USED) == 2


def test_arop_match(r: ClientType):
    r.armset("arr", {0: "foo", 1: "bar", 2: "foo"})
    assert r.arop("arr", 0, 2, ArrayAggregateOperations.MATCH, "foo") == 2


def test_arop_missing_key(r: ClientType):
    assert r.arop("nokey", 0, 5, ArrayAggregateOperations.SUM) is None


# ── ARINFO ────────────────────────────────────────────────────────────────────


def test_arinfo_basic(r: ClientType):
    r.armset("arr", {0: "a", 1: "b", 100: "c"})
    result = r.arinfo("arr")
    assert result["len"] == 101
    assert result["count"] == 3
    assert result["next-insert-index"] == 0


def test_arinfo_missing_key(r: ClientType):
    with pytest.raises(Exception, match="no such key"):
        r.arinfo("nokey")


def test_arinfo_full(r: ClientType):
    r.arset("arr", 0, "x")
    result = r.arinfo("arr", full=True)
    assert "slices" in result
    assert "dense-slices" in result


# ── WRONGTYPE ─────────────────────────────────────────────────────────────────


def test_arset_wrong_type(r: ClientType):
    r.set("str_key", "value")
    with pytest.raises(Exception) as ctx:
        r.arset("str_key", 0, "x")
    assert "WRONGTYPE" in str(ctx.value)
