from time import sleep

import pytest

from fakeredis._typing import ClientType
from test.testtools import key_val_dict, raw_command


def test_sscan_delete_key_while_scanning_should_not_returns_it_in_scan(r: ClientType):
    size = 600
    name = "sscan-test"
    all_keys_set = {f"{i}".encode() for i in range(size)}
    r.sadd(name, *list(all_keys_set))
    assert r.scard(name) == size

    cursor, keys = r.sscan(name, 0)
    assert len(keys) < len(all_keys_set)

    key_to_remove = next(x for x in all_keys_set if x not in keys)
    assert r.srem(name, key_to_remove) == 1
    assert not r.sismember(name, key_to_remove)
    while cursor != 0:
        cursor, data = r.sscan(name, cursor=cursor)
        keys.extend(data)
    assert len(set(keys)) == len(keys)
    assert len(keys) == size - 1
    assert key_to_remove not in keys


def test_hscan_delete_key_while_scanning_should_not_returns_it_in_scan(r: ClientType):
    size = 600
    name = "hscan-test"
    all_keys_dict = key_val_dict(size=size)
    r.hset(name, mapping=all_keys_dict)
    assert len(r.hgetall(name)) == size

    cursor, keys = r.hscan(name, 0)
    assert len(keys) < len(all_keys_dict)

    key_to_remove = next(x for x in all_keys_dict if x not in keys)
    assert r.hdel(name, key_to_remove) == 1
    assert r.hget(name, key_to_remove) is None
    while cursor != 0:
        cursor, data = r.hscan(name, cursor=cursor)
        keys.update(data)
    assert len(set(keys)) == len(keys)
    assert len(keys) == size - 1
    assert key_to_remove not in keys


def test_scan_delete_unseen_key_while_scanning_should_not_returns_it_in_scan(r: ClientType):
    size = 30
    all_keys_dict = key_val_dict(size=size)
    assert all(r.set(k, v) for k, v in all_keys_dict.items())
    assert len(r.keys()) == size

    cursor, keys = r.scan()

    key_to_remove = next(x for x in all_keys_dict if x not in keys)
    assert r.delete(key_to_remove) == 1
    assert r.get(key_to_remove) is None
    while cursor != 0:
        cursor, data = r.scan(cursor=cursor)
        keys.extend(data)
    assert len(set(keys)) == len(keys)
    assert len(keys) == size - 1
    assert key_to_remove not in keys


def test_scan_delete_seen_key_while_scanning_should_return_all_keys(r: ClientType):
    size = 30
    all_keys_dict = key_val_dict(size=size)
    assert all(r.set(k, v) for k, v in all_keys_dict.items())
    assert len(r.keys()) == size

    cursor, keys = r.scan()

    key_to_remove = keys[0]
    assert r.delete(keys[0]) == 1
    assert r.get(key_to_remove) is None
    while cursor != 0:
        cursor, data = r.scan(cursor=cursor)
        keys.extend(data)

    assert len(set(keys)) == len(keys)
    keys = set(keys)
    assert len(keys) == size, f"{set(all_keys_dict).difference(keys)} is not empty but should be"
    assert key_to_remove in keys


def test_zscan_delete_seen_member_while_scanning_should_return_all_members(r: ClientType):
    size = 30
    r.zadd("zs", {f"m{i:02}": i for i in range(size)})
    cursor, members = r.zscan("zs", 0, count=10)
    assert r.zrem("zs", members[0][0]) == 1
    while cursor != 0:
        cursor, data = r.zscan("zs", cursor, count=10)
        members.extend(data)
    assert {m for m, _ in members} == {f"m{i:02}".encode() for i in range(size)}


def test_scan_add_key_while_scanning_should_return_all_keys(r: ClientType):
    size = 30
    all_keys_dict = key_val_dict(size=size)
    assert all(r.set(k, v) for k, v in all_keys_dict.items())
    assert len(r.keys()) == size

    cursor, keys = r.scan()

    r.set("new_key", "new val")
    while cursor != 0:
        cursor, data = r.scan(cursor=cursor)
        keys.extend(data)

    keys = set(keys)
    assert len(keys) >= size, f"{set(all_keys_dict).difference(keys)} is not empty but should be"


def test_zscan_reports_the_score_a_member_has_when_it_is_returned(r: ClientType):
    size = 600
    r.zadd("zs", {f"m{i:03}": i for i in range(size)})
    cursor, members = r.zscan("zs", 0, count=10)
    assert cursor != 0
    unseen = next(f"m{i:03}".encode() for i in range(size) if f"m{i:03}".encode() not in dict(members))
    r.zadd("zs", {unseen: 5000})
    while cursor != 0:
        cursor, data = r.zscan("zs", cursor, count=100)
        members.extend(data)
    assert dict(members)[unseen] == 5000
    assert len(dict(members)) == size


def test_scan_with_type_delete_unseen_key_while_scanning(r: ClientType):
    size = 60
    for i in range(size):
        r.set(f"str:{i}", i)
        r.sadd(f"set:{i}", i)
    cursor, keys = r.scan(0, count=10, _type="string")
    assert cursor != 0
    key_to_remove = next(f"str:{i}".encode() for i in range(size) if f"str:{i}".encode() not in keys)
    assert r.delete(key_to_remove) == 1
    while cursor != 0:
        cursor, data = r.scan(cursor, count=10, _type="string")
        keys.extend(data)
    assert set(keys) == {f"str:{i}".encode() for i in range(size)} - {key_to_remove}


def test_hscan_continues_after_the_key_is_deleted(r: ClientType):
    r.hset("h", mapping=key_val_dict(size=600))
    cursor, _ = r.hscan("h", 0, count=10)
    assert cursor != 0
    r.delete("h")
    fields = {}
    while cursor != 0:
        cursor, data = r.hscan("h", cursor, count=100)
        fields.update(data)
    assert fields == {}


def test_sscan_two_iterations_at_once(r: ClientType):
    size = 600
    members = {f"{i}".encode() for i in range(size)}
    r.sadd("s", *members)
    cursor1, seen1 = r.sscan("s", 0, count=50)
    cursor2, seen2 = r.sscan("s", 0, count=70)
    while cursor1 != 0 or cursor2 != 0:
        if cursor1 != 0:
            cursor1, data = r.sscan("s", cursor1, count=50)
            seen1.extend(data)
        if cursor2 != 0:
            cursor2, data = r.sscan("s", cursor2, count=70)
            seen2.extend(data)
    assert set(seen1) == members
    assert set(seen2) == members


@pytest.mark.fake_only
def test_scan_cursors_are_forgotten_when_the_iteration_ends(r: ClientType):
    server = r.connection_pool.connection_kwargs["server"]
    for i in range(100):
        r.set(f"key:{i}", i)
    cursor, keys = r.scan(0, count=10)
    assert len(server.scan_cursors) == 1
    while cursor != 0:
        cursor, data = r.scan(cursor, count=10)
        keys.extend(data)
    assert len(keys) == 100
    assert len(server.scan_cursors) == 0


@pytest.mark.fake_only
def test_scan_with_a_cursor_that_is_not_remembered(r: ClientType):
    server = r.connection_pool.connection_kwargs["server"]
    for i in range(100):
        r.set(f"key:{i}", i)
    cursor, keys = r.scan(0, count=10)
    while cursor != 0:
        server.scan_cursors.clear()
        cursor, data = r.scan(cursor, count=10)
        keys.extend(data)
    assert sorted(keys) == sorted(f"key:{i}".encode() for i in range(100))


def test_scan(r: ClientType):
    # Set up the data
    for ix in range(20):
        k = f"scan-test:{ix}"
        v = f"result:{ix}"
        r.set(k, v)
    expected = r.keys()
    assert len(expected) == 20  # Ensure we know what we're testing

    # Test that we page through the results and get everything out
    results = []
    cursor = "0"
    while cursor != 0:
        cursor, data = r.scan(cursor, count=6)
        results.extend(data)
    assert set(expected) == set(results)

    # Now test that the MATCH functionality works
    results = []
    cursor = "0"
    while cursor != 0:
        cursor, data = r.scan(cursor, match="*7", count=100)
        results.extend(data)
    assert b"scan-test:7" in results
    assert b"scan-test:17" in results
    assert len(set(results)) == 2

    # Test the match on iterator
    results = list(r.scan_iter(match="*7"))
    assert b"scan-test:7" in results
    assert b"scan-test:17" in results
    assert len(set(results)) == 2


def test_scan_single(r: ClientType):
    r.set("foo1", "bar1")
    assert r.scan(match="foo*") == (0, [b"foo1"])


def test_scan_iter_single_page(r: ClientType):
    r.set("foo1", "bar1")
    r.set("foo2", "bar2")
    assert set(r.scan_iter(match="foo*")) == {b"foo1", b"foo2"}
    assert set(r.scan_iter()) == {b"foo1", b"foo2"}
    assert set(r.scan_iter(match="")) == set()
    assert set(r.scan_iter(match="foo1", _type="string")) == {
        b"foo1",
    }


def test_scan_iter_multiple_pages(r: ClientType):
    all_keys = key_val_dict(size=100)
    assert all(r.set(k, v) for k, v in all_keys.items())
    assert set(r.scan_iter()) == set(all_keys)


def test_scan_iter_multiple_pages_with_match(r: ClientType):
    all_keys = key_val_dict(size=100)
    assert all(r.set(k, v) for k, v in all_keys.items())
    # Now add a few keys that don't match the key:<number> pattern.
    r.set("otherkey", "foo")
    r.set("andanother", "bar")
    actual = set(r.scan_iter(match="key:*"))
    assert actual == set(all_keys)


def test_scan_multiple_pages_with_count_arg(r: ClientType):
    all_keys = key_val_dict(size=100)
    assert all(r.set(k, v) for k, v in all_keys.items())
    assert set(r.scan_iter(count=1000)) == set(all_keys)


def test_scan_all_in_single_call(r: ClientType):
    all_keys = key_val_dict(size=100)
    assert all(r.set(k, v) for k, v in all_keys.items())
    # Specify way more than the 100 keys we've added.
    actual = r.scan(count=1000)
    assert set(actual[1]) == set(all_keys)
    assert actual[0] == 0


@pytest.mark.slow
def test_scan_expired_key(r: ClientType):
    r.set("expiringkey", "value")
    r.pexpire("expiringkey", 1)
    sleep(1)
    assert r.scan()[1] == []


def test_scan_stream(r: ClientType):
    r.xadd("mystream", {"test": "value"})
    assert r.type("mystream") == b"stream"
    for s in r.scan_iter(_type="STRING"):
        print(s)


def test_scan_family_count_not_positive(r: ClientType, real_server_details):
    r.sadd("set", "m")
    r.hset("hash", "f", "v")
    r.zadd("zset", {"m": 1})
    is_dragonfly = real_server_details.server_type == "dragonfly"
    commands = (("scan", 0), ("sscan", "set", 0), ("hscan", "hash", 0), ("zscan", "zset", 0))
    for count in (0, -1):
        # Dragonfly reads COUNT as unsigned: 0 is accepted and uses the default batch size, while a negative value fails
        # to decode.
        if is_dragonfly and count == 0:
            for args in commands:
                raw_command(r, *args, "COUNT", count)
            continue
        expected = "value is not an integer or out of range" if is_dragonfly else "syntax error"
        for args in commands:
            with pytest.raises(Exception, match=expected):
                raw_command(r, *args, "COUNT", count)
