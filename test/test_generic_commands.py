from datetime import datetime, timedelta
from time import sleep, time

import pytest
import redis

import testtools


@pytest.mark.slow
def test_expireat_should_expire_key_by_datetime(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    r.expireat('foo', datetime.now() + timedelta(seconds=1))
    sleep(1.5)
    assert r.get('foo') is None
    assert r.expireat('bar', datetime.now()) is False


@pytest.mark.slow
def test_expireat_should_expire_key_by_timestamp(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    r.expireat('foo', int(time() + 1))
    sleep(1.5)
    assert r.get('foo') is None
    assert r.expire('bar', 1) is False


def test_expireat_should_return_true_for_existing_key(r):
    r.set('foo', 'bar')
    assert r.expireat('foo', int(time() + 1)) is True


def test_expireat_should_return_false_for_missing_key(r):
    assert r.expireat('missing', int(time() + 1)) is False


def test_del_operator(r):
    r['foo'] = 'bar'
    del r['foo']
    assert r.get('foo') is None


def test_expire_should_not_handle_floating_point_values(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError, match='value is not an integer or out of range'):
        r.expire('something_new', 1.2)
        r.pexpire('something_new', 1000.2)
        r.expire('some_unused_key', 1.2)
        r.pexpire('some_unused_key', 1000.2)


def test_ttl_should_return_minus_one_for_non_expiring_key(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    assert r.ttl('foo') == -1


def test_scan(r):
    # Set up the data
    for ix in range(20):
        k = 'scan-test:%s' % ix
        v = 'result:%s' % ix
        r.set(k, v)
    expected = r.keys()
    assert len(expected) == 20  # Ensure we know what we're testing

    # Test that we page through the results and get everything out
    results = []
    cursor = '0'
    while cursor != 0:
        cursor, data = r.scan(cursor, count=6)
        results.extend(data)
    assert set(expected) == set(results)

    # Now test that the MATCH functionality works
    results = []
    cursor = '0'
    while cursor != 0:
        cursor, data = r.scan(cursor, match='*7', count=100)
        results.extend(data)
    assert b'scan-test:7' in results
    assert b'scan-test:17' in results
    assert len(results) == 2

    # Test the match on iterator
    results = [r for r in r.scan_iter(match='*7')]
    assert b'scan-test:7' in results
    assert b'scan-test:17' in results
    assert len(results) == 2


def test_sort_range_offset_range(r):
    r.rpush('foo', '2')
    r.rpush('foo', '1')
    r.rpush('foo', '4')
    r.rpush('foo', '3')

    assert r.sort('foo', start=0, num=2) == [b'1', b'2']


def test_sort_range_offset_range_and_desc(r):
    r.rpush('foo', '2')
    r.rpush('foo', '1')
    r.rpush('foo', '4')
    r.rpush('foo', '3')

    assert r.sort("foo", start=0, num=1, desc=True) == [b"4"]


def test_sort_range_offset_norange(r):
    with pytest.raises(redis.RedisError):
        r.sort('foo', start=1)


def test_sort_range_with_large_range(r):
    r.rpush('foo', '2')
    r.rpush('foo', '1')
    r.rpush('foo', '4')
    r.rpush('foo', '3')
    # num=20 even though len(foo) is 4.
    assert r.sort('foo', start=1, num=20) == [b'2', b'3', b'4']


def test_sort_descending(r):
    r.rpush('foo', '1')
    r.rpush('foo', '2')
    r.rpush('foo', '3')
    assert r.sort('foo', desc=True) == [b'3', b'2', b'1']


def test_sort_alpha(r):
    r.rpush('foo', '2a')
    r.rpush('foo', '1b')
    r.rpush('foo', '2b')
    r.rpush('foo', '1a')

    assert r.sort('foo', alpha=True) == [b'1a', b'1b', b'2a', b'2b']


def test_sort_foo(r):
    r.rpush('foo', '2a')
    r.rpush('foo', '1b')
    r.rpush('foo', '2b')
    r.rpush('foo', '1a')
    with pytest.raises(redis.ResponseError):
        r.sort('foo', alpha=False)


def test_sort_empty(r):
    assert r.sort('foo') == []


def test_sort_wrong_type(r):
    r.set('string', '3')
    with pytest.raises(redis.ResponseError):
        r.sort('string')


def test_sort_with_store_option(r):
    r.rpush('foo', '2')
    r.rpush('foo', '1')
    r.rpush('foo', '4')
    r.rpush('foo', '3')

    assert r.sort('foo', store='bar') == 4
    assert r.lrange('bar', 0, -1) == [b'1', b'2', b'3', b'4']


def test_sort_with_by_and_get_option(r):
    r.rpush('foo', '2')
    r.rpush('foo', '1')
    r.rpush('foo', '4')
    r.rpush('foo', '3')

    r['weight_1'] = '4'
    r['weight_2'] = '3'
    r['weight_3'] = '2'
    r['weight_4'] = '1'

    r['data_1'] = 'one'
    r['data_2'] = 'two'
    r['data_3'] = 'three'
    r['data_4'] = 'four'

    assert (
            r.sort('foo', by='weight_*', get='data_*')
            == [b'four', b'three', b'two', b'one']
    )
    assert r.sort('foo', by='weight_*', get='#') == [b'4', b'3', b'2', b'1']
    assert (
            r.sort('foo', by='weight_*', get=('data_*', '#'))
            == [b'four', b'4', b'three', b'3', b'two', b'2', b'one', b'1']
    )
    assert r.sort('foo', by='weight_*', get='data_1') == [None, None, None, None]


def test_sort_with_hash(r):
    r.rpush('foo', 'middle')
    r.rpush('foo', 'eldest')
    r.rpush('foo', 'youngest')
    r.hset('record_youngest', 'age', 1)
    r.hset('record_youngest', 'name', 'baby')

    r.hset('record_middle', 'age', 10)
    r.hset('record_middle', 'name', 'teen')

    r.hset('record_eldest', 'age', 20)
    r.hset('record_eldest', 'name', 'adult')

    assert r.sort('foo', by='record_*->age') == [b'youngest', b'middle', b'eldest']
    assert (
            r.sort('foo', by='record_*->age', get='record_*->name')
            == [b'baby', b'teen', b'adult']
    )


def test_sort_with_set(r):
    r.sadd('foo', '3')
    r.sadd('foo', '1')
    r.sadd('foo', '2')
    assert r.sort('foo') == [b'1', b'2', b'3']


def test_ttl_should_return_minus_two_for_non_existent_key(r):
    assert r.get('foo') is None
    assert r.ttl('foo') == -2


def test_type(r):
    r.set('string_key', "value")
    r.lpush("list_key", "value")
    r.sadd("set_key", "value")
    testtools.zadd(r, "zset_key", {"value": 1})
    r.hset('hset_key', 'key', 'value')

    assert r.type('string_key') == b'string'
    assert r.type('list_key') == b'list'
    assert r.type('set_key') == b'set'
    assert r.type('zset_key') == b'zset'
    assert r.type('hset_key') == b'hash'
    assert r.type('none_key') == b'none'


@testtools.run_test_if_redispy_ver('above', '3')
def test_unlink(r):
    r.set('foo', 'bar')
    r.unlink('foo')
    assert r.get('foo') is None


def test_dump_missing(r):
    assert r.dump('foo') is None


def test_dump_restore(r):
    r.set('foo', 'bar')
    dump = r.dump('foo')
    r.restore('baz', 0, dump)
    assert r.get('baz') == b'bar'
    assert r.ttl('baz') == -1


def test_dump_restore_ttl(r):
    r.set('foo', 'bar')
    dump = r.dump('foo')
    r.restore('baz', 2000, dump)
    assert r.get('baz') == b'bar'
    assert 1000 <= r.pttl('baz') <= 2000


def test_dump_restore_replace(r):
    r.set('foo', 'bar')
    dump = r.dump('foo')
    r.set('foo', 'baz')
    r.restore('foo', 0, dump, replace=True)
    assert r.get('foo') == b'bar'


def test_restore_exists(r):
    r.set('foo', 'bar')
    dump = r.dump('foo')
    with pytest.raises(redis.exceptions.ResponseError):
        r.restore('foo', 0, dump)


def test_restore_invalid_dump(r):
    r.set('foo', 'bar')
    dump = r.dump('foo')
    with pytest.raises(redis.exceptions.ResponseError):
        r.restore('baz', 0, dump[:-1])


def test_restore_invalid_ttl(r):
    r.set('foo', 'bar')
    dump = r.dump('foo')
    with pytest.raises(redis.exceptions.ResponseError):
        r.restore('baz', -1, dump)


def test_set_then_get(r):
    assert r.set('foo', 'bar') is True
    assert r.get('foo') == b'bar'


def test_exists(r):
    assert 'foo' not in r
    r.set('foo', 'bar')
    assert 'foo' in r


@pytest.mark.slow
def test_expire_should_expire_key(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    r.expire('foo', 1)
    sleep(1.5)
    assert r.get('foo') is None
    assert r.expire('bar', 1) is False


@testtools.run_test_if_redispy_ver('above', '4.2.0')
@pytest.mark.max_server('7')
def test_expire_extra_params_return_error(r):
    with pytest.raises(redis.exceptions.ResponseError):
        r.expire('foo', 1, nx=True)


def test_expire_should_return_true_for_existing_key(r):
    r.set('foo', 'bar')
    assert r.expire('foo', 1) is True


def test_expire_should_return_false_for_missing_key(r):
    assert r.expire('missing', 1) is False


@pytest.mark.slow
def test_expire_should_expire_key_using_timedelta(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    r.expire('foo', timedelta(seconds=1))
    sleep(1.5)
    assert r.get('foo') is None
    assert r.expire('bar', 1) is False


@pytest.mark.slow
def test_expire_should_expire_immediately_with_millisecond_timedelta(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    r.expire('foo', timedelta(milliseconds=750))
    assert r.get('foo') is None
    assert r.expire('bar', 1) is False


def test_watch_expire(r):
    """EXPIRE should mark a key as changed for WATCH."""
    r.set('foo', 'bar')
    with r.pipeline() as p:
        p.watch('foo')
        r.expire('foo', 10000)
        p.multi()
        p.get('foo')
        with pytest.raises(redis.exceptions.WatchError):
            p.execute()


@pytest.mark.slow
def test_pexpire_should_expire_key(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    r.pexpire('foo', 150)
    sleep(0.2)
    assert r.get('foo') is None
    assert r.pexpire('bar', 1) == 0


def test_pexpire_should_return_truthy_for_existing_key(r):
    r.set('foo', 'bar')
    assert r.pexpire('foo', 1)


def test_pexpire_should_return_falsey_for_missing_key(r):
    assert not r.pexpire('missing', 1)


@pytest.mark.slow
def test_pexpire_should_expire_key_using_timedelta(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    r.pexpire('foo', timedelta(milliseconds=750))
    sleep(0.5)
    assert r.get('foo') == b'bar'
    sleep(0.5)
    assert r.get('foo') is None
    assert r.pexpire('bar', 1) == 0


@pytest.mark.slow
def test_pexpireat_should_expire_key_by_datetime(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    r.pexpireat('foo', datetime.now() + timedelta(milliseconds=150))
    sleep(0.2)
    assert r.get('foo') is None
    assert r.pexpireat('bar', datetime.now()) == 0


@pytest.mark.slow
def test_pexpireat_should_expire_key_by_timestamp(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    r.pexpireat('foo', int(time() * 1000 + 150))
    sleep(0.2)
    assert r.get('foo') is None
    assert r.expire('bar', 1) is False


def test_pexpireat_should_return_true_for_existing_key(r):
    r.set('foo', 'bar')
    assert r.pexpireat('foo', int(time() * 1000 + 150))


def test_pexpireat_should_return_false_for_missing_key(r):
    assert not r.pexpireat('missing', int(time() * 1000 + 150))


def test_pttl_should_return_minus_one_for_non_expiring_key(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    assert r.pttl('foo') == -1


def test_pttl_should_return_minus_two_for_non_existent_key(r):
    assert r.get('foo') is None
    assert r.pttl('foo') == -2


def test_persist(r):
    r.set('foo', 'bar', ex=20)
    assert r.persist('foo') == 1
    assert r.ttl('foo') == -1
    assert r.persist('foo') == 0


def test_watch_persist(r):
    """PERSIST should mark a variable as changed."""
    r.set('foo', 'bar', ex=10000)
    with r.pipeline() as p:
        p.watch('foo')
        r.persist('foo')
        p.multi()
        p.get('foo')
        with pytest.raises(redis.exceptions.WatchError):
            p.execute()


def test_set_existing_key_persists(r):
    r.set('foo', 'bar', ex=20)
    r.set('foo', 'foo')
    assert r.ttl('foo') == -1


def test_get_float_type(r):  # Test for issue #58
    r.set('key', 123)
    assert r.get('key') == b'123'
    r.incr('key')
    assert r.get('key') == b'124'


def test_set_float_value(r):
    x = 1.23456789123456789
    r.set('foo', x)
    assert float(r.get('foo')) == x
