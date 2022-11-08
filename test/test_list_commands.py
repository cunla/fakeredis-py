import threading
from time import sleep

import pytest
import redis
import redis.client
import redis.client

from testtools import raw_command


def test_lpush_then_lrange_all(r):
    assert r.lpush('foo', 'bar') == 1
    assert r.lpush('foo', 'baz') == 2
    assert r.lpush('foo', 'bam', 'buzz') == 4
    assert r.lrange('foo', 0, -1) == [b'buzz', b'bam', b'baz', b'bar']


def test_lpush_then_lrange_portion(r):
    r.lpush('foo', 'one')
    r.lpush('foo', 'two')
    r.lpush('foo', 'three')
    r.lpush('foo', 'four')
    assert r.lrange('foo', 0, 2) == [b'four', b'three', b'two']
    assert r.lrange('foo', 0, 3) == [b'four', b'three', b'two', b'one']


def test_lrange_negative_indices(r):
    r.rpush('foo', 'a', 'b', 'c')
    assert r.lrange('foo', -1, -2) == []
    assert r.lrange('foo', -2, -1) == [b'b', b'c']


def test_lpush_key_does_not_exist(r):
    assert r.lrange('foo', 0, -1) == []


def test_lpush_with_nonstr_key(r):
    r.lpush(1, 'one')
    r.lpush(1, 'two')
    r.lpush(1, 'three')
    assert r.lrange(1, 0, 2) == [b'three', b'two', b'one']
    assert r.lrange('1', 0, 2) == [b'three', b'two', b'one']


def test_lpush_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.lpush('foo', 'element')


def test_llen(r):
    r.lpush('foo', 'one')
    r.lpush('foo', 'two')
    r.lpush('foo', 'three')
    assert r.llen('foo') == 3


def test_llen_no_exist(r):
    assert r.llen('foo') == 0


def test_llen_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.llen('foo')


def test_lrem_positive_count(r):
    r.lpush('foo', 'same')
    r.lpush('foo', 'same')
    r.lpush('foo', 'different')
    r.lrem('foo', 2, 'same')
    assert r.lrange('foo', 0, -1) == [b'different']


def test_lrem_negative_count(r):
    r.lpush('foo', 'removeme')
    r.lpush('foo', 'three')
    r.lpush('foo', 'two')
    r.lpush('foo', 'one')
    r.lpush('foo', 'removeme')
    r.lrem('foo', -1, 'removeme')
    # Should remove it from the end of the list,
    # leaving the 'removeme' from the front of the list alone.
    assert r.lrange('foo', 0, -1) == [b'removeme', b'one', b'two', b'three']


def test_lrem_zero_count(r):
    r.lpush('foo', 'one')
    r.lpush('foo', 'one')
    r.lpush('foo', 'one')
    r.lrem('foo', 0, 'one')
    assert r.lrange('foo', 0, -1) == []


def test_lrem_default_value(r):
    r.lpush('foo', 'one')
    r.lpush('foo', 'one')
    r.lpush('foo', 'one')
    r.lrem('foo', 0, 'one')
    assert r.lrange('foo', 0, -1) == []


def test_lrem_does_not_exist(r):
    r.lpush('foo', 'one')
    r.lrem('foo', 0, 'one')
    # These should be noops.
    r.lrem('foo', -2, 'one')
    r.lrem('foo', 2, 'one')


def test_lrem_return_value(r):
    r.lpush('foo', 'one')
    count = r.lrem('foo', 0, 'one')
    assert count == 1
    assert r.lrem('foo', 0, 'one') == 0


def test_lrem_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.lrem('foo', 0, 'element')


def test_rpush(r):
    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    r.rpush('foo', 'three')
    r.rpush('foo', 'four', 'five')
    assert r.lrange('foo', 0, -1) == [b'one', b'two', b'three', b'four', b'five']


def test_rpush_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.rpush('foo', 'element')


def test_lpop(r):
    assert r.rpush('foo', 'one') == 1
    assert r.rpush('foo', 'two') == 2
    assert r.rpush('foo', 'three') == 3
    assert r.lpop('foo') == b'one'
    assert r.lpop('foo') == b'two'
    assert r.lpop('foo') == b'three'


def test_lpop_empty_list(r):
    r.rpush('foo', 'one')
    r.lpop('foo')
    assert r.lpop('foo') is None
    # Verify what happens if we try to pop from a key
    # we've never seen before.
    assert r.lpop('noexists') is None


def test_lpop_zero_elem(r):
    r.rpush(b'\x00', b'')
    assert r.lpop(b'\x00', 0) == []


def test_lpop_zero_non_existing_list(r):
    assert r.lpop(b'', 0) is None


def test_lpop_zero_wrong_type(r):
    r.set(b'', b'')
    with pytest.raises(redis.ResponseError):
        r.lpop(b'', 0)


def test_lpop_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.lpop('foo')


@pytest.mark.min_server('6.2')
def test_lpop_count(r):
    assert r.rpush('foo', 'one') == 1
    assert r.rpush('foo', 'two') == 2
    assert r.rpush('foo', 'three') == 3
    assert raw_command(r, 'lpop', 'foo', 2) == [b'one', b'two']
    # See https://github.com/redis/redis/issues/9680
    raw = raw_command(r, 'rpop', 'foo', 0)
    assert raw is None or raw == []  # https://github.com/redis/redis/pull/10095


@pytest.mark.min_server('6.2')
def test_lpop_count_negative(r):
    with pytest.raises(redis.ResponseError):
        raw_command(r, 'lpop', 'foo', -1)


def test_lset(r):
    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    r.rpush('foo', 'three')
    r.lset('foo', 0, 'four')
    r.lset('foo', -2, 'five')
    assert r.lrange('foo', 0, -1) == [b'four', b'five', b'three']


def test_lset_index_out_of_range(r):
    r.rpush('foo', 'one')
    with pytest.raises(redis.ResponseError):
        r.lset('foo', 3, 'three')


def test_lset_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.lset('foo', 0, 'element')


def test_rpushx(r):
    r.rpush('foo', 'one')
    r.rpushx('foo', 'two')
    r.rpushx('bar', 'three')
    assert r.lrange('foo', 0, -1) == [b'one', b'two']
    assert r.lrange('bar', 0, -1) == []


def test_rpushx_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.rpushx('foo', 'element')


def test_ltrim(r):
    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    r.rpush('foo', 'three')
    r.rpush('foo', 'four')

    assert r.ltrim('foo', 1, 3)
    assert r.lrange('foo', 0, -1) == [b'two', b'three', b'four']
    assert r.ltrim('foo', 1, -1)
    assert r.lrange('foo', 0, -1) == [b'three', b'four']


def test_ltrim_with_non_existent_key(r):
    assert r.ltrim('foo', 0, -1)


def test_ltrim_expiry(r):
    r.rpush('foo', 'one', 'two', 'three')
    r.expire('foo', 10)
    r.ltrim('foo', 1, 2)
    assert r.ttl('foo') > 0


def test_ltrim_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.ltrim('foo', 1, -1)


def test_lindex(r):
    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    assert r.lindex('foo', 0) == b'one'
    assert r.lindex('foo', 4) is None
    assert r.lindex('bar', 4) is None


def test_lindex_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.lindex('foo', 0)


def test_lpushx(r):
    r.lpush('foo', 'two')
    r.lpushx('foo', 'one')
    r.lpushx('bar', 'one')
    assert r.lrange('foo', 0, -1) == [b'one', b'two']
    assert r.lrange('bar', 0, -1) == []


def test_lpushx_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.lpushx('foo', 'element')


def test_rpop(r):
    assert r.rpop('foo') is None
    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    assert r.rpop('foo') == b'two'
    assert r.rpop('foo') == b'one'
    assert r.rpop('foo') is None


def test_rpop_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.rpop('foo')


@pytest.mark.min_server('6.2')
def test_rpop_count(r):
    assert r.rpush('foo', 'one') == 1
    assert r.rpush('foo', 'two') == 2
    assert r.rpush('foo', 'three') == 3
    assert raw_command(r, 'rpop', 'foo', 2) == [b'three', b'two']
    # See https://github.com/redis/redis/issues/9680
    raw = raw_command(r, 'rpop', 'foo', 0)
    assert raw is None or raw == []  # https://github.com/redis/redis/pull/10095


@pytest.mark.min_server('6.2')
def test_rpop_count_negative(r):
    with pytest.raises(redis.ResponseError):
        raw_command(r, 'rpop', 'foo', -1)


def test_linsert_before(r):
    r.rpush('foo', 'hello')
    r.rpush('foo', 'world')
    assert r.linsert('foo', 'before', 'world', 'there') == 3
    assert r.lrange('foo', 0, -1) == [b'hello', b'there', b'world']


def test_linsert_after(r):
    r.rpush('foo', 'hello')
    r.rpush('foo', 'world')
    assert r.linsert('foo', 'after', 'hello', 'there') == 3
    assert r.lrange('foo', 0, -1) == [b'hello', b'there', b'world']


def test_linsert_no_pivot(r):
    r.rpush('foo', 'hello')
    r.rpush('foo', 'world')
    assert r.linsert('foo', 'after', 'goodbye', 'bar') == -1
    assert r.lrange('foo', 0, -1) == [b'hello', b'world']


def test_linsert_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.linsert('foo', 'after', 'bar', 'element')


def test_rpoplpush(r):
    assert r.rpoplpush('foo', 'bar') is None
    assert r.lpop('bar') is None
    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    r.rpush('bar', 'one')

    assert r.rpoplpush('foo', 'bar') == b'two'
    assert r.lrange('foo', 0, -1) == [b'one']
    assert r.lrange('bar', 0, -1) == [b'two', b'one']

    # Catch instances where we store bytes and strings inconsistently
    # and thus bar = ['two', b'one']
    assert r.lrem('bar', -1, 'two') == 1


def test_rpoplpush_to_nonexistent_destination(r):
    r.rpush('foo', 'one')
    assert r.rpoplpush('foo', 'bar') == b'one'
    assert r.rpop('bar') == b'one'


def test_rpoplpush_expiry(r):
    r.rpush('foo', 'one')
    r.rpush('bar', 'two')
    r.expire('bar', 10)
    r.rpoplpush('foo', 'bar')
    assert r.ttl('bar') > 0


def test_rpoplpush_one_to_self(r):
    r.rpush('list', 'element')
    assert r.brpoplpush('list', 'list') == b'element'
    assert r.lrange('list', 0, -1) == [b'element']


def test_rpoplpush_wrong_type(r):
    r.set('foo', 'bar')
    r.rpush('list', 'element')
    with pytest.raises(redis.ResponseError):
        r.rpoplpush('foo', 'list')
    assert r.get('foo') == b'bar'
    assert r.lrange('list', 0, -1) == [b'element']
    with pytest.raises(redis.ResponseError):
        r.rpoplpush('list', 'foo')
    assert r.get('foo') == b'bar'
    assert r.lrange('list', 0, -1) == [b'element']


def test_blpop_single_list(r):
    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    r.rpush('foo', 'three')
    assert r.blpop(['foo'], timeout=1) == (b'foo', b'one')


def test_blpop_test_multiple_lists(r):
    r.rpush('baz', 'zero')
    assert r.blpop(['foo', 'baz'], timeout=1) == (b'baz', b'zero')
    assert not r.exists('baz')

    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    # bar has nothing, so the returned value should come
    # from foo.
    assert r.blpop(['bar', 'foo'], timeout=1) == (b'foo', b'one')
    r.rpush('bar', 'three')
    # bar now has something, so the returned value should come
    # from bar.
    assert r.blpop(['bar', 'foo'], timeout=1) == (b'bar', b'three')
    assert r.blpop(['bar', 'foo'], timeout=1) == (b'foo', b'two')


def test_blpop_allow_single_key(r):
    # blpop converts single key arguments to a one element list.
    r.rpush('foo', 'one')
    assert r.blpop('foo', timeout=1) == (b'foo', b'one')


@pytest.mark.slow
def test_blpop_block(r):
    def push_thread():
        sleep(0.5)
        r.rpush('foo', 'value1')
        sleep(0.5)
        # Will wake the condition variable
        r.set('bar', 'go back to sleep some more')
        r.rpush('foo', 'value2')

    thread = threading.Thread(target=push_thread)
    thread.start()
    try:
        assert r.blpop('foo') == (b'foo', b'value1')
        assert r.blpop('foo', timeout=5) == (b'foo', b'value2')
    finally:
        thread.join()


def test_blpop_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.blpop('foo', timeout=1)


def test_blpop_transaction(r):
    p = r.pipeline()
    p.multi()
    p.blpop('missing', timeout=1000)
    result = p.execute()
    # Blocking commands behave like non-blocking versions in transactions
    assert result == [None]


def test_brpop_test_multiple_lists(r):
    r.rpush('baz', 'zero')
    assert r.brpop(['foo', 'baz'], timeout=1) == (b'baz', b'zero')
    assert not r.exists('baz')

    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    assert r.brpop(['bar', 'foo'], timeout=1) == (b'foo', b'two')


def test_brpop_single_key(r):
    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    assert r.brpop('foo', timeout=1) == (b'foo', b'two')


@pytest.mark.slow
def test_brpop_block(r):
    def push_thread():
        sleep(0.5)
        r.rpush('foo', 'value1')
        sleep(0.5)
        # Will wake the condition variable
        r.set('bar', 'go back to sleep some more')
        r.rpush('foo', 'value2')

    thread = threading.Thread(target=push_thread)
    thread.start()
    try:
        assert r.brpop('foo') == (b'foo', b'value1')
        assert r.brpop('foo', timeout=5) == (b'foo', b'value2')
    finally:
        thread.join()


def test_brpop_wrong_type(r):
    r.set('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        r.brpop('foo', timeout=1)


def test_brpoplpush_multi_keys(r):
    assert r.lpop('bar') is None
    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    assert r.brpoplpush('foo', 'bar', timeout=1) == b'two'
    assert r.lrange('bar', 0, -1) == [b'two']

    # Catch instances where we store bytes and strings inconsistently
    # and thus bar = ['two']
    assert r.lrem('bar', -1, 'two') == 1


def test_brpoplpush_wrong_type(r):
    r.set('foo', 'bar')
    r.rpush('list', 'element')
    with pytest.raises(redis.ResponseError):
        r.brpoplpush('foo', 'list')
    assert r.get('foo') == b'bar'
    assert r.lrange('list', 0, -1) == [b'element']
    with pytest.raises(redis.ResponseError):
        r.brpoplpush('list', 'foo')
    assert r.get('foo') == b'bar'
    assert r.lrange('list', 0, -1) == [b'element']


@pytest.mark.slow
def test_blocking_operations_when_empty(r):
    assert r.blpop(['foo'], timeout=1) is None
    assert r.blpop(['bar', 'foo'], timeout=1) is None
    assert r.brpop('foo', timeout=1) is None
    assert r.brpoplpush('foo', 'bar', timeout=1) is None


def test_empty_list(r):
    r.rpush('foo', 'bar')
    r.rpop('foo')
    assert not r.exists('foo')
