import pytest
import redis

from test.testtools import key_val_dict


def test_sscan_delete_key_while_scanning_should_not_returns_it_in_scan(r: redis.Redis):
    size = 600
    name = 'sscan-test'
    all_keys_set = {f'{i}'.encode() for i in range(size)}
    r.sadd(name, *[k for k in all_keys_set])
    assert r.scard(name) == size

    cursor, keys = r.sscan(name, 0)
    assert len(keys) < len(all_keys_set)

    key_to_remove = next(x for x in all_keys_set if x not in keys)
    assert r.srem(name, key_to_remove) == 1
    assert r.sismember(name, key_to_remove) is False
    while cursor != 0:
        cursor, data = r.sscan(name, cursor=cursor)
        keys.extend(data)
    assert len(set(keys)) == len(keys)
    assert len(keys) == size - 1
    assert key_to_remove not in keys


def test_hscan_delete_key_while_scanning_should_not_returns_it_in_scan(r: redis.Redis):
    size = 600
    name = 'hscan-test'
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


def test_scan_delete_unseen_key_while_scanning_should_not_returns_it_in_scan(r: redis.Redis):
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


@pytest.mark.xfail
def test_scan_delete_seen_key_while_scanning_should_return_all_keys(r: redis.Redis):
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
