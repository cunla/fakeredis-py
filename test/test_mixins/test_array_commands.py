"""Tests for Redis Array commands (AR*)."""

import pytest

from fakeredis._typing import ClientType
from test.testtools import raw_command


# ── ARSET / ARGET ──────────────────────────────────────────────────────────────


def test_arset_single(r: ClientType):
    assert raw_command(r, "arset", "arr", 0, "hello") == 1
    assert raw_command(r, "arget", "arr", 0) == b"hello"


def test_arset_multi(r: ClientType):
    assert raw_command(r, "arset", "arr", 2, "a", "b", "c") == 3
    assert raw_command(r, "arget", "arr", 2) == b"a"
    assert raw_command(r, "arget", "arr", 3) == b"b"
    assert raw_command(r, "arget", "arr", 4) == b"c"


def test_arset_update_returns_zero(r: ClientType):
    r.arset("arr", 0, "first")
    raw_command(r, "arset", "arr", 0, "first")
    assert raw_command(r, "arset", "arr", 0, "second") == 0
    assert raw_command(r, "arget", "arr", 0) == b"second"


def test_arget_missing_key(r: ClientType):
    assert raw_command(r, "arget", "nokey", 0) is None


def test_arget_missing_index(r: ClientType):
    raw_command(r, "arset", "arr", 0, "x")
    assert raw_command(r, "arget", "arr", 5) is None


# ── ARMSET / ARMGET ────────────────────────────────────────────────────────────


def test_armset_armget(r: ClientType):
    assert raw_command(r, "armset", "arr", 0, "alpha", 5, "beta", 100, "gamma") == 3
    assert raw_command(r, "armget", "arr", 0, 5, 100, 3) == [b"alpha", b"beta", b"gamma", None]


def test_armget_missing_key(r: ClientType):
    assert raw_command(r, "armget", "nokey", 0, 1) == [None, None]


# ── ARLEN / ARCOUNT ───────────────────────────────────────────────────────────


def test_arlen_arcount(r: ClientType):
    raw_command(r, "arset", "arr", 0, "a")
    raw_command(r, "arset", "arr", 5, "b")
    assert raw_command(r, "arlen", "arr") == 6  # max_index=5, 5+1=6
    assert raw_command(r, "arcount", "arr") == 2


def test_arlen_arcount_missing(r: ClientType):
    assert raw_command(r, "arlen", "nokey") == 0
    assert raw_command(r, "arcount", "nokey") == 0


# ── ARDEL ─────────────────────────────────────────────────────────────────────


def test_ardel(r: ClientType):
    raw_command(r, "arset", "arr", 0, "a")
    raw_command(r, "arset", "arr", 1, "b")
    raw_command(r, "arset", "arr", 2, "c")
    assert raw_command(r, "ardel", "arr", 1) == 1
    assert raw_command(r, "arget", "arr", 1) is None
    assert raw_command(r, "arcount", "arr") == 2


def test_ardel_multi(r: ClientType):
    raw_command(r, "armset", "arr", 0, "a", 1, "b", 2, "c")
    assert raw_command(r, "ardel", "arr", 0, 2) == 2
    assert raw_command(r, "arcount", "arr") == 1


def test_ardel_missing_index(r: ClientType):
    raw_command(r, "arset", "arr", 0, "x")
    assert raw_command(r, "ardel", "arr", 99) == 0


def test_ardel_missing_key(r: ClientType):
    assert raw_command(r, "ardel", "nokey", 0) == 0


# ── ARDELRANGE ────────────────────────────────────────────────────────────────


def test_ardelrange(r: ClientType):
    raw_command(r, "armset", "arr", 0, "a", 1, "b", 2, "c", 3, "d", 4, "e")
    assert raw_command(r, "ardelrange", "arr", 1, 3) == 3
    assert raw_command(r, "arcount", "arr") == 2
    assert raw_command(r, "arget", "arr", 0) == b"a"
    assert raw_command(r, "arget", "arr", 4) == b"e"


def test_ardelrange_multi_ranges(r: ClientType):
    raw_command(r, "armset", "arr", 0, "a", 1, "b", 2, "c", 3, "d", 4, "e")
    assert raw_command(r, "ardelrange", "arr", 0, 1, 3, 4) == 4


def test_ardelrange_missing_key(r: ClientType):
    assert raw_command(r, "ardelrange", "nokey", 0, 5) == 0


# ── ARGETRANGE ────────────────────────────────────────────────────────────────


def test_argetrange_forward(r: ClientType):
    raw_command(r, "armset", "arr", 0, "a", 1, "b", 3, "d")
    result = raw_command(r, "argetrange", "arr", 0, 3)
    assert result == [b"a", b"b", None, b"d"]


def test_argetrange_reverse(r: ClientType):
    raw_command(r, "armset", "arr", 0, "a", 1, "b", 2, "c")
    result = raw_command(r, "argetrange", "arr", 2, 0)
    assert result == [b"c", b"b", b"a"]


def test_argetrange_missing_key(r: ClientType):
    assert raw_command(r, "argetrange", "nokey", 0, 5) == []


# ── ARINSERT / ARNEXT / ARSEEK ────────────────────────────────────────────────


def test_arinsert_basic(r: ClientType):
    assert raw_command(r, "arinsert", "arr", "alpha") == 0
    assert raw_command(r, "arinsert", "arr", "beta") == 1
    assert raw_command(r, "arinsert", "arr", "gamma") == 2
    assert raw_command(r, "arget", "arr", 0) == b"alpha"
    assert raw_command(r, "arget", "arr", 1) == b"beta"
    assert raw_command(r, "arget", "arr", 2) == b"gamma"


def test_arinsert_multi(r: ClientType):
    assert raw_command(r, "arinsert", "arr", "a", "b", "c") == 2


def test_arnext_new_key(r: ClientType):
    assert raw_command(r, "arnext", "nokey") == 0


def test_arnext_after_insert(r: ClientType):
    raw_command(r, "arinsert", "arr", "a", "b")
    assert raw_command(r, "arnext", "arr") == 2


def test_arseek(r: ClientType):
    raw_command(r, "arinsert", "arr", "a", "b")
    assert raw_command(r, "arseek", "arr", 10) == 1
    assert raw_command(r, "arnext", "arr") == 10
    raw_command(r, "arinsert", "arr", "c")
    assert raw_command(r, "arget", "arr", 10) == b"c"


def test_arseek_missing_key(r: ClientType):
    assert raw_command(r, "arseek", "nokey", 5) == 0


# ── ARRING ────────────────────────────────────────────────────────────────────


def test_arring_basic(r: ClientType):
    raw_command(r, "arring", "ring", 3, "v0")
    raw_command(r, "arring", "ring", 3, "v1")
    raw_command(r, "arring", "ring", 3, "v2")
    assert raw_command(r, "arring", "ring", 3, "v3") == 0  # wraps to idx 0
    assert raw_command(r, "arget", "ring", 0) == b"v3"
    assert raw_command(r, "arcount", "ring") == 3


def test_arring_truncates(r: ClientType):
    raw_command(r, "armset", "arr", 0, "a", 5, "b", 9, "c")
    assert raw_command(r, "arlen", "arr") == 10
    raw_command(r, "arring", "arr", 3, "x")
    assert raw_command(r, "arlen", "arr") <= 3  # truncated to size 3


# ── ARLASTITEMS ───────────────────────────────────────────────────────────────


def test_arlastitems(r: ClientType):
    raw_command(r, "arinsert", "log", "first")
    raw_command(r, "arinsert", "log", "second")
    raw_command(r, "arinsert", "log", "third")
    assert raw_command(r, "arlastitems", "log", 2) == [b"second", b"third"]


def test_arlastitems_rev(r: ClientType):
    raw_command(r, "arinsert", "log", "first")
    raw_command(r, "arinsert", "log", "second")
    raw_command(r, "arinsert", "log", "third")
    assert raw_command(r, "arlastitems", "log", 2, "REV") == [b"third", b"second"]


def test_arlastitems_ring(r: ClientType):
    raw_command(r, "arring", "ring", 3, "v0")
    raw_command(r, "arring", "ring", 3, "v1")
    raw_command(r, "arring", "ring", 3, "v2")
    raw_command(r, "arring", "ring", 3, "v3")  # overwrites v0 at idx 0
    items = raw_command(r, "arlastitems", "ring", 3)
    assert b"v3" in items
    assert b"v0" not in items


def test_arlastitems_missing_key(r: ClientType):
    assert raw_command(r, "arlastitems", "nokey", 3) == []


# ── ARSCAN ────────────────────────────────────────────────────────────────────


def test_arscan_basic(r: ClientType):
    raw_command(r, "arset", "arr", 0, "a")
    raw_command(r, "arset", "arr", 5, "b")
    raw_command(r, "arset", "arr", 9, "c")
    result = raw_command(r, "arscan", "arr", 0, 10)
    assert result == [0, b"a", 5, b"b", 9, b"c"]


def test_arscan_limit(r: ClientType):
    raw_command(r, "arset", "arr", 0, "a")
    raw_command(r, "arset", "arr", 5, "b")
    raw_command(r, "arset", "arr", 9, "c")
    result = raw_command(r, "arscan", "arr", 0, 10, "LIMIT", 2)
    assert result == [0, b"a", 5, b"b"]


def test_arscan_missing_key(r: ClientType):
    assert raw_command(r, "arscan", "nokey", 0, 10) == []


# ── ARGREP ────────────────────────────────────────────────────────────────────


def test_argrep_exact(r: ClientType):
    raw_command(r, "armset", "log", 0, "boot: ok", 1, "warn: disk", 2, "ERROR: cpu", 3, "info: ready")
    result = raw_command(r, "argrep", "log", 0, 3, "EXACT", "info: ready")
    assert result == [3]


def test_argrep_match(r: ClientType):
    raw_command(r, "armset", "log", 0, "boot: ok", 1, "warn: disk", 2, "ERROR: cpu", 3, "info: ready", 4, "error: net")
    result = raw_command(r, "argrep", "log", 0, 4, "MATCH", "error", "NOCASE")
    assert result == [2, 4]


def test_argrep_withvalues(r: ClientType):
    raw_command(r, "armset", "log", 0, "boot: ok", 1, "warn: disk", 2, "ERROR: cpu")
    result = raw_command(r, "argrep", "log", 0, 2, "MATCH", "error", "NOCASE", "WITHVALUES")
    assert result == [2, b"ERROR: cpu"]


def test_argrep_glob(r: ClientType):
    raw_command(r, "armset", "arr", 0, "warn: disk", 1, "error: cpu", 2, "info: ok")
    result = raw_command(r, "argrep", "arr", 0, 2, "GLOB", "warn:*")
    assert result == [0]


def test_argrep_re(r: ClientType):
    raw_command(r, "armset", "arr", 0, "foo123", 1, "bar456", 2, "baz")
    result = raw_command(r, "argrep", "arr", 0, 2, "RE", r"[a-z]+\d+")
    assert 0 in result
    assert 1 in result
    assert 2 not in result


def test_argrep_limit(r: ClientType):
    raw_command(r, "armset", "arr", 0, "error: a", 1, "error: b", 2, "error: c")
    result = raw_command(r, "argrep", "arr", 0, 2, "MATCH", "error", "LIMIT", 2)
    assert len(result) == 2


def test_argrep_missing_key(r: ClientType):
    assert raw_command(r, "argrep", "nokey", 0, 10, "MATCH", "x") == []


# ── AROP ──────────────────────────────────────────────────────────────────────


def test_arop_sum(r: ClientType):
    raw_command(r, "armset", "arr", 0, "10", 1, "20", 2, "30")
    assert raw_command(r, "arop", "arr", 0, 2, "SUM") == b"60"


def test_arop_min(r: ClientType):
    raw_command(r, "armset", "arr", 0, "10", 1, "5", 2, "30")
    assert raw_command(r, "arop", "arr", 0, 2, "MIN") == b"5"


def test_arop_max(r: ClientType):
    raw_command(r, "armset", "arr", 0, "10", 1, "5", 2, "30")
    assert raw_command(r, "arop", "arr", 0, 2, "MAX") == b"30"


def test_arop_used(r: ClientType):
    raw_command(r, "arset", "arr", 0, "a")
    raw_command(r, "arset", "arr", 5, "b")
    assert raw_command(r, "arop", "arr", 0, 9, "USED") == 2


def test_arop_match(r: ClientType):
    raw_command(r, "armset", "arr", 0, "foo", 1, "bar", 2, "foo")
    assert raw_command(r, "arop", "arr", 0, 2, "MATCH", "foo") == 2


def test_arop_missing_key(r: ClientType):
    assert raw_command(r, "arop", "nokey", 0, 5, "SUM") is None


# ── ARINFO ────────────────────────────────────────────────────────────────────


def test_arinfo_basic(r: ClientType):
    raw_command(r, "armset", "arr", 0, "a", 1, "b", 100, "c")
    result = raw_command(r, "arinfo", "arr")
    info = dict(zip(result[::2], result[1::2]))
    assert info[b"length"] == 101
    assert info[b"count"] == 3
    assert info[b"cursor"] == 0


def test_arinfo_missing_key(r: ClientType):
    assert raw_command(r, "arinfo", "nokey") is None


def test_arinfo_full(r: ClientType):
    raw_command(r, "arset", "arr", 0, "x")
    result = raw_command(r, "arinfo", "arr", "FULL")
    assert b"slices" in result
    assert b"fill_rate" in result


# ── WRONGTYPE ─────────────────────────────────────────────────────────────────


def test_arset_wrong_type(r: ClientType):
    r.set("str_key", "value")
    with pytest.raises(Exception) as ctx:
        raw_command(r, "arset", "str_key", 0, "x")
    assert "WRONGTYPE" in str(ctx.value)
