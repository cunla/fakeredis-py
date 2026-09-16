import time

import pytest

from fakeredis._helpers import current_time
from fakeredis.model import ExpiringMembersSet

pytestmark = [pytest.mark.fake]


def test_clear_key_expireat_keeps_the_member():
    s = ExpiringMembersSet().update([b"a", b"b"])
    assert s.set_member_expireat(b"a", current_time() + 30) == 1

    assert s.clear_key_expireat(b"a") is True
    assert s.get_key_expireat(b"a") is None
    assert b"a" in s
    time.sleep(0.05)
    assert set(s) == {b"a", b"b"}


def test_clear_key_expireat_without_a_ttl():
    s = ExpiringMembersSet().update([b"a"])
    assert s.clear_key_expireat(b"a") is False
    assert s.clear_key_expireat(b"missing") is False
    assert b"a" in s
    assert b"missing" not in s


def test_clear_key_expireat_does_not_revive_an_expired_member():
    s = ExpiringMembersSet().update([b"a"])
    assert s.set_member_expireat(b"a", current_time() + 30) == 1
    time.sleep(0.05)
    assert s.clear_key_expireat(b"a") is False
    assert b"a" not in s


def test_expiry_at_timestamp_zero():
    s = ExpiringMembersSet({b"a": 0, b"b": None})
    assert set(s) == {b"b"}
    assert len(s) == 1
