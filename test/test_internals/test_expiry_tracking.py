"""Expired keys and hash fields are found through a heap of pending expiries rather than by scanning everything, so
these check that the heap keeps up with every way an expiry can be set, replaced, cleared or moved."""

import time

import pytest

import fakeredis
from fakeredis._core._database import Database, Item
from fakeredis._helpers import current_time
from fakeredis.model import Hash

pytestmark = [pytest.mark.fake]


def _db_of(r: fakeredis.FakeRedis, index: int = 0) -> Database:
    server = r.connection_pool.connection_kwargs["server"]
    return server.dbs[index]


@pytest.fixture
def fake() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(server=fakeredis.FakeServer(version=(8,)))


def test_dbsize_and_keys_drop_expired_keys(fake):
    fake.set("stays", "v")
    fake.set("short", "v", px=20)
    fake.set("long", "v", ex=100)
    assert fake.dbsize() == 3
    time.sleep(0.05)
    assert fake.dbsize() == 2
    assert sorted(fake.keys()) == [b"long", b"stays"]
    assert fake.randomkey() in {b"long", b"stays"}
    assert sorted(fake.scan_iter()) == [b"long", b"stays"]


def test_expiry_replaced_or_cleared_is_not_applied(fake):
    fake.set("extended", "v", px=20)
    fake.expire("extended", 100)
    fake.set("persisted", "v", px=20)
    fake.persist("persisted")
    fake.set("overwritten", "v", px=20)
    fake.set("overwritten", "v2")
    fake.set("shortened", "v", ex=100)
    fake.pexpire("shortened", 20)
    time.sleep(0.05)
    assert sorted(fake.keys()) == [b"extended", b"overwritten", b"persisted"]
    assert fake.dbsize() == 3


def test_key_recreated_after_delete_keeps_only_its_new_expiry(fake):
    fake.set("k", "v", px=20)
    fake.delete("k")
    fake.set("k", "v")
    time.sleep(0.05)
    assert fake.dbsize() == 1


@pytest.mark.parametrize("command", ["rename", "copy", "move", "restore", "swapdb"])
def test_expiry_follows_the_key(fake, command):
    fake.set("src", "v", px=30)
    target_db = 0
    if command == "rename":
        fake.rename("src", "dst")
    elif command == "copy":
        fake.copy("src", "dst")
        fake.persist("src")
    elif command == "move":
        fake.move("src", 1)
        target_db = 1
    elif command == "restore":
        fake.restore("dst", 30, fake.dump("src"))
        fake.persist("src")
    else:
        fake.swapdb(0, 1)
        target_db = 1
    target = fakeredis.FakeRedis(server=fake.connection_pool.connection_kwargs["server"], db=target_db)
    before = target.dbsize()
    time.sleep(0.06)
    assert target.dbsize() == before - 1
    assert target.keys() == ([b"src"] if command in ("copy", "restore") else [])


def test_flushdb_forgets_pending_expiries(fake):
    for i in range(10):
        fake.set(f"k{i}", "v", ex=100)
    fake.flushdb()
    assert _db_of(fake)._expiry_heap == []


def test_refreshing_a_ttl_does_not_grow_the_heap_without_bound(fake):
    fake.set("k", "v")
    for _ in range(1000):
        fake.expire("k", 100)
    assert len(_db_of(fake)._expiry_heap) < 100
    assert fake.ttl("k") > 0


def test_randomkey_only_returns_live_keys():
    db = Database(None)
    assert db.random_key() is None
    for key in (b"a", b"b", b"c"):
        db[key] = Item(b"v")
    db.time = 10.0
    expiring = Item(b"v")
    expiring.expireat = 5.0
    db[b"gone"] = expiring
    assert {db.random_key() for _ in range(200)} == {b"a", b"b", b"c"}


def test_hash_fields_expire_in_order_and_once():
    h = Hash()
    now = current_time()
    for field in (b"a", b"b", b"c", b"d"):
        h[field] = b"v"
    h.set_key_expireat(b"c", now + 20)
    h.set_key_expireat(b"a", now + 40)
    h.set_key_expireat(b"d", now + 10_000)
    time.sleep(0.03)
    assert h.keys() == [b"a", b"b", b"d"]
    time.sleep(0.03)
    assert h.keys() == [b"b", b"d"]
    assert h.take_expired_fields() == [b"c", b"a"]
    assert h.take_expired_fields() == []


def test_hash_field_ttl_replaced_or_cleared_is_not_applied():
    h = Hash()
    now = current_time()
    for field in (b"extended", b"persisted", b"overwritten", b"deleted", b"shortened"):
        h[field] = b"v"
        h.set_key_expireat(field, now + (10_000 if field == b"shortened" else 20))
    h.set_key_expireat(b"extended", now + 10_000)
    h.clear_key_expireat(b"persisted")
    h[b"overwritten"] = b"v2"
    del h[b"deleted"]
    h[b"deleted"] = b"again"
    h.set_key_expireat(b"shortened", now + 20)
    time.sleep(0.05)
    assert sorted(h.keys()) == [b"deleted", b"extended", b"overwritten", b"persisted"]
    assert h.take_expired_fields() == [b"shortened"]


def test_refreshing_a_field_ttl_does_not_grow_the_heap_without_bound():
    h = Hash()
    h[b"f"] = b"v"
    for i in range(1000):
        h.set_key_expireat(b"f", current_time() + 10_000 + i)
    assert len(h._expiry_heap) < 100
    assert h.get_key_expireat(b"f") is not None
