from datetime import timedelta
from time import sleep

import pytest
import pytest_asyncio
import redis

import testtools

pytestmark = [
    testtools.run_test_if_redis_ver('below', '3'),
]


@pytest_asyncio.fixture
def r(request, create_redis):
    rconn = create_redis(db=0)
    connected = request.node.get_closest_marker('disconnected') is None
    if connected:
        rconn.flushall()
    yield rconn
    if connected:
        rconn.flushall()
    if hasattr(r, 'close'):
        rconn.close()  # Older versions of redis-py don't have this method


def test_zadd_uses_str(r):
    r.testtools.zadd('foo', 12345, (1, 2, 3))
    assert r.zrange('foo', 0, 0) == [b'(1, 2, 3)']


def test_zadd_errors(r):
    # The args are backwards, it should be 2, "two", so we
    # expect an exception to be raised.
    with pytest.raises(redis.ResponseError):
        r.testtools.zadd('foo', 'two', 2)
    with pytest.raises(redis.ResponseError):
        r.testtools.zadd('foo', two='two')
    # It's expected an equal number of values and scores
    with pytest.raises(redis.RedisError):
        r.testtools.zadd('foo', 'two')


def test_mset_accepts_kwargs(r):
    assert r.mset(foo='one', bar='two') is True
    assert r.mset(foo='one', baz='three') is True
    assert r.mget('foo', 'bar', 'baz') == [b'one', b'two', b'three']


def test_mget_none(r):
    r.set('foo', 'one')
    r.set('bar', 'two')
    assert r.mget('foo', 'bar', None) == [b'one', b'two', None]


def test_set_None_value(r):
    assert r.set('foo', None) is True
    assert r.get('foo') == b'None'


def test_rpush_then_lrange_with_nested_list1(r):
    assert r.rpush('foo', [12345, 6789]) == 1
    assert r.rpush('foo', [54321, 9876]) == 2
    assert r.lrange('foo', 0, -1) == [b'[12345, 6789]', b'[54321, 9876]']


def test_rpush_then_lrange_with_nested_list2(r):
    assert r.rpush('foo', [12345, 'banana']) == 1
    assert r.rpush('foo', [54321, 'elephant']) == 2
    assert r.lrange('foo', 0, -1), [b'[12345, \'banana\']', b'[54321, \'elephant\']']


def test_rpush_then_lrange_with_nested_list3(r):
    assert r.rpush('foo', [12345, []]) == 1
    assert r.rpush('foo', [54321, []]) == 2
    assert r.lrange('foo', 0, -1) == [b'[12345, []]', b'[54321, []]']


def test_hgetall_with_tuples(r):
    assert r.hset('foo', (1, 2), (1, 2, 3)) == 1
    assert r.hgetall('foo') == {b'(1, 2)': b'(1, 2, 3)'}


def test_hmset_convert_values(r):
    r.hmset('foo', {'k1': True, 'k2': 1})
    assert r.hgetall('foo') == {b'k1': b'True', b'k2': b'1'}


def test_hmset_does_not_mutate_input_params(r):
    original = {'key': [123, 456]}
    r.hmset('foo', original)
    assert original == {'key': [123, 456]}


@pytest.mark.parametrize(
    'create_redis',
    [
        pytest.param('FakeRedis', marks=pytest.mark.fake),
        pytest.param('Redis', marks=pytest.mark.real)
    ],
    indirect=True
)
class TestNonStrict:
    def test_setex(self, r):
        assert r.setex('foo', 'bar', 100) is True
        assert r.get('foo') == b'bar'

    def test_setex_using_timedelta(self, r):
        assert r.setex('foo', 'bar', timedelta(seconds=100)) is True
        assert r.get('foo') == b'bar'

    def test_lrem_positive_count(self, r):
        r.lpush('foo', 'same')
        r.lpush('foo', 'same')
        r.lpush('foo', 'different')
        r.lrem('foo', 'same', 2)
        assert r.lrange('foo', 0, -1) == [b'different']

    def test_lrem_negative_count(self, r):
        r.lpush('foo', 'removeme')
        r.lpush('foo', 'three')
        r.lpush('foo', 'two')
        r.lpush('foo', 'one')
        r.lpush('foo', 'removeme')
        r.lrem('foo', 'removeme', -1)
        # Should remove it from the end of the list,
        # leaving the 'removeme' from the front of the list alone.
        assert r.lrange('foo', 0, -1) == [b'removeme', b'one', b'two', b'three']

    def test_lrem_zero_count(self, r):
        r.lpush('foo', 'one')
        r.lpush('foo', 'one')
        r.lpush('foo', 'one')
        r.lrem('foo', 'one')
        assert r.lrange('foo', 0, -1) == []

    def test_lrem_default_value(self, r):
        r.lpush('foo', 'one')
        r.lpush('foo', 'one')
        r.lpush('foo', 'one')
        r.lrem('foo', 'one')
        assert r.lrange('foo', 0, -1) == []

    def test_lrem_does_not_exist(self, r):
        r.lpush('foo', 'one')
        r.lrem('foo', 'one')
        # These should be noops.
        r.lrem('foo', 'one', -2)
        r.lrem('foo', 'one', 2)

    def test_lrem_return_value(self, r):
        r.lpush('foo', 'one')
        count = r.lrem('foo', 'one', 0)
        assert count == 1
        assert r.lrem('foo', 'one') == 0

    def test_zadd_deprecated(self, r):
        result = r.testtools.zadd('foo', 'one', 1)
        assert result == 1
        assert r.zrange('foo', 0, -1) == [b'one']

    def test_zadd_missing_required_params(self, r):
        with pytest.raises(redis.RedisError):
            # Missing the 'score' param.
            r.testtools.zadd('foo', 'one')
        with pytest.raises(redis.RedisError):
            # Missing the 'value' param.
            r.testtools.zadd('foo', None, score=1)
        with pytest.raises(redis.RedisError):
            r.testtools.zadd('foo')

    def test_zadd_with_single_keypair(self, r):
        result = r.testtools.zadd('foo', bar=1)
        assert result == 1
        assert r.zrange('foo', 0, -1) == [b'bar']

    def test_zadd_with_multiple_keypairs(self, r):
        result = r.testtools.zadd('foo', bar=1, baz=9)
        assert result == 2
        assert r.zrange('foo', 0, -1) == [b'bar', b'baz']

    def test_zadd_with_name_is_non_string(self, r):
        result = r.testtools.zadd('foo', 1, 9)
        assert result == 1
        assert r.zrange('foo', 0, -1) == [b'1']

    def test_ttl_should_return_none_for_non_expiring_key(self, r):
        r.set('foo', 'bar')
        assert r.get('foo') == b'bar'
        assert r.ttl('foo') is None

    def test_ttl_should_return_value_for_expiring_key(self, r):
        r.set('foo', 'bar')
        r.expire('foo', 1)
        assert r.ttl('foo') == 1
        r.expire('foo', 2)
        assert r.ttl('foo') == 2
        # See https://github.com/antirez/redis/blob/unstable/src/db.c#L632
        ttl = 1000000000
        r.expire('foo', ttl)
        assert r.ttl('foo') == ttl

    def test_pttl_should_return_none_for_non_expiring_key(self, r):
        r.set('foo', 'bar')
        assert r.get('foo') == b'bar'
        assert r.pttl('foo') is None

    def test_pttl_should_return_value_for_expiring_key(self, r):
        d = 100
        r.set('foo', 'bar')
        r.expire('foo', 1)
        assert 1000 - d <= r.pttl('foo') <= 1000
        r.expire('foo', 2)
        assert 2000 - d <= r.pttl('foo') <= 2000
        ttl = 1000000000
        # See https://github.com/antirez/redis/blob/unstable/src/db.c#L632
        r.expire('foo', ttl)
        assert ttl * 1000 - d <= r.pttl('foo') <= ttl * 1000

    def test_expire_should_not_handle_floating_point_values(self, r):
        r.set('foo', 'bar')
        with pytest.raises(redis.ResponseError, match='value is not an integer or out of range'):
            r.expire('something_new', 1.2)
            r.pexpire('something_new', 1000.2)
            r.expire('some_unused_key', 1.2)
            r.pexpire('some_unused_key', 1000.2)

    @testtools.run_test_if_lupa
    def test_lock(self, r):
        lock = r.lock('foo')
        assert lock.acquire()
        assert r.exists('foo')
        lock.release()
        assert not r.exists('foo')
        with r.lock('bar'):
            assert r.exists('bar')
        assert not r.exists('bar')

    def test_unlock_without_lock(self, r):
        lock = r.lock('foo')
        with pytest.raises(redis.exceptions.LockError):
            lock.release()

    @pytest.mark.slow
    @testtools.run_test_if_lupa
    def test_unlock_expired(self, r):
        lock = r.lock('foo', timeout=0.01, sleep=0.001)
        assert lock.acquire()
        sleep(0.1)
        with pytest.raises(redis.exceptions.LockError):
            lock.release()

    @pytest.mark.slow
    @testtools.run_test_if_lupa
    def test_lock_blocking_timeout(self, r):
        lock = r.lock('foo')
        assert lock.acquire()
        lock2 = r.lock('foo')
        assert not lock2.acquire(blocking_timeout=1)

    @testtools.run_test_if_lupa
    def test_lock_nonblocking(self, r):
        lock = r.lock('foo')
        assert lock.acquire()
        lock2 = r.lock('foo')
        assert not lock2.acquire(blocking=False)

    @testtools.run_test_if_lupa
    def test_lock_twice(self, r):
        lock = r.lock('foo')
        assert lock.acquire(blocking=False)
        assert not lock.acquire(blocking=False)

    @testtools.run_test_if_lupa
    def test_acquiring_lock_different_lock_release(self, r):
        lock1 = r.lock('foo')
        lock2 = r.lock('foo')
        assert lock1.acquire(blocking=False)
        assert not lock2.acquire(blocking=False)

        # Test only releasing lock1 actually releases the lock
        with pytest.raises(redis.exceptions.LockError):
            lock2.release()
        assert not lock2.acquire(blocking=False)
        lock1.release()
        # Locking with lock2 now has the lock
        assert lock2.acquire(blocking=False)
        assert not lock1.acquire(blocking=False)

    @testtools.run_test_if_lupa
    def test_lock_extend(self, r):
        lock = r.lock('foo', timeout=2)
        lock.acquire()
        lock.extend(3)
        ttl = int(r.pttl('foo'))
        assert 4000 < ttl <= 5000

    @testtools.run_test_if_lupa
    def test_lock_extend_exceptions(self, r):
        lock1 = r.lock('foo', timeout=2)
        with pytest.raises(redis.exceptions.LockError):
            lock1.extend(3)
        lock2 = r.lock('foo')
        lock2.acquire()
        with pytest.raises(redis.exceptions.LockError):
            lock2.extend(3)  # Cannot extend a lock with no timeout

    @pytest.mark.slow
    @testtools.run_test_if_lupa
    def test_lock_extend_expired(self, r):
        lock = r.lock('foo', timeout=0.01, sleep=0.001)
        lock.acquire()
        sleep(0.1)
        with pytest.raises(redis.exceptions.LockError):
            lock.extend(3)
