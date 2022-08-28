import pytest
import redis

import testtools

pytestmark = [
    testtools.run_test_if_redis_ver('above', '4'),
]
fake_only = pytest.mark.parametrize(
    'create_redis',
    [pytest.param('FakeStrictRedis', marks=pytest.mark.fake)],
    indirect=True
)


@testtools.run_test_if_redis_ver('above', '4.2.0')
@testtools.run_test_if_no_aioredis
def test_fakeredis_aioredis_uses_redis_asyncio():
    import fakeredis.aioredis as aioredis

    assert not hasattr(aioredis, "__version__")


@testtools.run_test_if_redis_ver('above', '4.1.2')
def test_lmove_to_nonexistent_destination(r):
    r.rpush('foo', 'one')
    assert r.lmove('foo', 'bar', 'RIGHT', 'LEFT') == b'one'
    assert r.rpop('bar') == b'one'


def test_zrange_with_byscore(r):
    testtools.zadd(r, 'foo', {'zero': 0})
    testtools.zadd(r, 'foo', {'two': 2})
    testtools.zadd(r, 'foo', {'two_a_also': 2})
    testtools.zadd(r, 'foo', {'two_b_also': 2})
    testtools.zadd(r, 'foo', {'four': 4})
    assert r.zrange('foo', 1, 3, byscore=True) == [b'two', b'two_a_also', b'two_b_also']
    assert r.zrange('foo', 2, 3, byscore=True) == [b'two', b'two_a_also', b'two_b_also']
    assert (
            r.zrange('foo', 0, 4, byscore=True)
            == [b'zero', b'two', b'two_a_also', b'two_b_also', b'four']
    )
    assert r.zrange('foo', '-inf', 1, byscore=True) == [b'zero']
    assert (
            r.zrange('foo', 2, '+inf', byscore=True)
            == [b'two', b'two_a_also', b'two_b_also', b'four']
    )
    assert (
            r.zrange('foo', '-inf', '+inf', byscore=True)
            == [b'zero', b'two', b'two_a_also', b'two_b_also', b'four']
    )


def test_lmove_expiry(r):
    r.rpush('foo', 'one')
    r.rpush('bar', 'two')
    r.expire('bar', 10)
    r.lmove('foo', 'bar', 'RIGHT', 'LEFT')
    assert r.ttl('bar') > 0


def test_lmove_wrong_type(r):
    r.set('foo', 'bar')
    r.rpush('list', 'element')
    with pytest.raises(redis.ResponseError):
        r.lmove('foo', 'list', 'RIGHT', 'LEFT')
    assert r.get('foo') == b'bar'
    assert r.lrange('list', 0, -1) == [b'element']
    with pytest.raises(redis.ResponseError):
        r.lmove('list', 'foo', 'RIGHT', 'LEFT')
    assert r.get('foo') == b'bar'
    assert r.lrange('list', 0, -1) == [b'element']


@testtools.run_test_if_redis_ver('above', '4.1.2')
def test_lmove(r):
    assert r.lmove('foo', 'bar', 'RIGHT', 'LEFT') is None
    assert r.lpop('bar') is None
    r.rpush('foo', 'one')
    r.rpush('foo', 'two')
    r.rpush('bar', 'one')

    # RPOPLPUSH
    assert r.lmove('foo', 'bar', 'RIGHT', 'LEFT') == b'two'
    assert r.lrange('foo', 0, -1) == [b'one']
    assert r.lrange('bar', 0, -1) == [b'two', b'one']
    # LPOPRPUSH
    assert r.lmove('bar', 'bar', 'LEFT', 'RIGHT') == b'two'
    assert r.lrange('bar', 0, -1) == [b'one', b'two']
    # RPOPRPUSH
    r.rpush('foo', 'three')
    assert r.lmove('foo', 'bar', 'RIGHT', 'RIGHT') == b'three'
    assert r.lrange('foo', 0, -1) == [b'one']
    assert r.lrange('bar', 0, -1) == [b'one', b'two', b'three']
    # LPOPLPUSH
    assert r.lmove('bar', 'foo', 'LEFT', 'LEFT') == b'one'
    assert r.lrange('foo', 0, -1) == [b'one', b'one']
    assert r.lrange('bar', 0, -1) == [b'two', b'three']

    # Catch instances where we store bytes and strings inconsistently
    # and thus bar = ['two', b'one']
    assert r.lrem('bar', -1, 'two') == 1


def test_smismember(r):
    assert r.smismember('foo', ['member1', 'member2', 'member3']) == [0, 0, 0]
    r.sadd('foo', 'member1', 'member2', 'member3')
    assert r.smismember('foo', ['member1', 'member2', 'member3']) == [1, 1, 1]
    assert r.smismember('foo', ['member1', 'member2', 'member3', 'member4']) == [1, 1, 1, 0]
    assert r.smismember('foo', ['member4', 'member2', 'member3']) == [0, 1, 1]
    # should also work if provided values as arguments
    assert r.smismember('foo', 'member4', 'member2', 'member3') == [0, 1, 1]


def test_smismember_wrong_type(r):
    # verify that command fails when the key itself is not a SET
    testtools.zadd(r, 'foo', {'member': 1})
    with pytest.raises(redis.ResponseError):
        r.smismember('foo', 'member')

    # verify that command fails if the input parameter is of wrong type
    r.sadd('foo2', 'member1', 'member2', 'member3')
    with pytest.raises(redis.DataError, match='Invalid input of type'):
        r.smismember('foo2', [["member1", "member2"]])


@pytest.mark.disconnected
@fake_only
class TestFakeStrictRedisConnectionErrors:

    def test_lmove(self, r):
        with pytest.raises(redis.ConnectionError):
            r.lmove(1, 2, 'LEFT', 'RIGHT')
