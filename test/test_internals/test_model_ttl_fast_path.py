import time

import pytest

from fakeredis._helpers import current_time
from fakeredis.model import ExpiringMembersSet, Hash

pytestmark = [pytest.mark.fake]


def test_hash_field_ttl_still_expires():
    h = Hash()
    h[b"a"] = b"1"
    h[b"b"] = b"2"
    assert h.set_key_expireat(b"a", current_time() + 30) == 1
    time.sleep(0.05)
    assert h.keys() == [b"b"]
    assert h.take_expired_fields() == [b"a"]


def test_hash_without_ttls_returns_its_fields():
    h = Hash()
    h.update({b"a": b"1", b"b": b"2"}, clear_expiration=True)
    assert h.getall() == {b"a": b"1", b"b": b"2"}
    assert h.items() == [(b"a", b"1"), (b"b", b"2")]
    assert h.values() == [b"1", b"2"]


def test_member_ttl_survives_copy_and_union():
    with_ttl = ExpiringMembersSet().update([b"a", b"b"])
    assert with_ttl.set_member_expireat(b"a", current_time() + 30) == 1
    plain = ExpiringMembersSet().update([b"c"])

    # `plain` has no TTLs of its own, so the union only expires `a` if it inherits `with_ttl`'s.
    union = plain | with_ttl
    copied = with_ttl.copy()
    time.sleep(0.05)

    assert set(union) == {b"b", b"c"}
    assert set(copied) == {b"b"}
    assert len(with_ttl) == 1
