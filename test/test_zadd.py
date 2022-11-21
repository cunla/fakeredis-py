import pytest
import redis
import redis.client
from packaging.version import Version

from test import testtools
from test.testtools import raw_command

REDIS_VERSION = Version(redis.__version__)


def test_zadd(r):
    testtools.zadd(r, 'foo', {'four': 4})
    testtools.zadd(r, 'foo', {'three': 3})
    assert testtools.zadd(r, 'foo', {'two': 2, 'one': 1, 'zero': 0}) == 3
    assert r.zrange('foo', 0, -1) == [b'zero', b'one', b'two', b'three', b'four']
    assert testtools.zadd(r, 'foo', {'zero': 7, 'one': 1, 'five': 5}) == 1
    assert (
            r.zrange('foo', 0, -1)
            == [b'one', b'two', b'three', b'four', b'five', b'zero']
    )


def test_zadd_empty(r):
    # Have to add at least one key/value pair
    with pytest.raises(redis.RedisError):
        testtools.zadd(r, 'foo', {})


@pytest.mark.max_server('6.2.7')
def test_zadd_minus_zero_redis6(r):
    # Changing -0 to +0 is ignored
    testtools.zadd(r, 'foo', {'a': -0.0})
    testtools.zadd(r, 'foo', {'a': 0.0})
    assert raw_command(r, 'zscore', 'foo', 'a') == b'-0'


@pytest.mark.min_server('7')
def test_zadd_minus_zero_redis7(r):
    testtools.zadd(r, 'foo', {'a': -0.0})
    testtools.zadd(r, 'foo', {'a': 0.0})
    assert raw_command(r, 'zscore', 'foo', 'a') == b'0'


def test_zadd_wrong_type(r):
    r.sadd('foo', 'bar')
    with pytest.raises(redis.ResponseError):
        testtools.zadd(r, 'foo', {'two': 2})


def test_zadd_multiple(r):
    testtools.zadd(r, 'foo', {'one': 1, 'two': 2})
    assert r.zrange('foo', 0, 0) == [b'one']
    assert r.zrange('foo', 1, 1) == [b'two']


@testtools.run_test_if_redispy_ver('above', '3')
@pytest.mark.parametrize(
    'param,return_value,state',
    [
        ({'four': 2.0, 'three': 1.0}, 0, [(b'three', 3.0), (b'four', 4.0)]),
        ({'four': 2.0, 'three': 1.0, 'zero': 0.0}, 1, [(b'zero', 0.0), (b'three', 3.0), (b'four', 4.0)]),
        ({'two': 2.0, 'one': 1.0}, 2, [(b'one', 1.0), (b'two', 2.0), (b'three', 3.0), (b'four', 4.0)])
    ]
)
@pytest.mark.parametrize('ch', [False, True])
def test_zadd_with_nx(r, param, return_value, state, ch):
    testtools.zadd(r, 'foo', {'four': 4.0, 'three': 3.0})
    assert testtools.zadd(r, 'foo', param, nx=True, ch=ch) == return_value
    assert r.zrange('foo', 0, -1, withscores=True) == state


@testtools.run_test_if_redispy_ver('above', '4.2.0')
@pytest.mark.parametrize(
    'param,return_value,state',
    [
        ({'four': 2.0, 'three': 1.0}, 0, [(b'three', 3.0), (b'four', 4.0)]),
        ({'four': 5.0, 'three': 1.0, 'zero': 0.0}, 2, [(b'zero', 0.0), (b'three', 3.0), (b'four', 5.0), ]),
        ({'two': 2.0, 'one': 1.0}, 2, [(b'one', 1.0), (b'two', 2.0), (b'three', 3.0), (b'four', 4.0)])
    ]
)
def test_zadd_with_gt_and_ch(r, param, return_value, state):
    testtools.zadd(r, 'foo', {'four': 4.0, 'three': 3.0})
    assert testtools.zadd(r, 'foo', param, gt=True, ch=True) == return_value
    assert r.zrange('foo', 0, -1, withscores=True) == state


@testtools.run_test_if_redispy_ver('above', '4.2.0')
@pytest.mark.parametrize(
    'param,return_value,state',
    [
        ({'four': 2.0, 'three': 1.0}, 0, [(b'three', 3.0), (b'four', 4.0)]),
        ({'four': 5.0, 'three': 1.0, 'zero': 0.0}, 1, [(b'zero', 0.0), (b'three', 3.0), (b'four', 5.0)]),
        ({'two': 2.0, 'one': 1.0}, 2, [(b'one', 1.0), (b'two', 2.0), (b'three', 3.0), (b'four', 4.0)])
    ]
)
def test_zadd_with_gt(r, param, return_value, state):
    testtools.zadd(r, 'foo', {'four': 4.0, 'three': 3.0})
    assert testtools.zadd(r, 'foo', param, gt=True) == return_value
    assert r.zrange('foo', 0, -1, withscores=True) == state


@testtools.run_test_if_redispy_ver('above', '3')
@pytest.mark.parametrize(
    'param,return_value,state',
    [
        ({'four': 4.0, 'three': 1.0}, 1, [(b'three', 1.0), (b'four', 4.0)]),
        ({'four': 4.0, 'three': 1.0, 'zero': 0.0}, 2, [(b'zero', 0.0), (b'three', 1.0), (b'four', 4.0)]),
        ({'two': 2.0, 'one': 1.0}, 2, [(b'one', 1.0), (b'two', 2.0), (b'three', 3.0), (b'four', 4.0)])
    ]
)
def test_zadd_with_ch(r, param, return_value, state):
    testtools.zadd(r, 'foo', {'four': 4.0, 'three': 3.0})
    assert testtools.zadd(r, 'foo', param, ch=True) == return_value
    assert r.zrange('foo', 0, -1, withscores=True) == state


@testtools.run_test_if_redispy_ver('above', '3')
@pytest.mark.parametrize(
    'param,changed,state',
    [
        ({'four': 2.0, 'three': 1.0}, 2, [(b'three', 1.0), (b'four', 2.0)]),
        ({'four': 4.0, 'three': 3.0, 'zero': 0.0}, 0, [(b'three', 3.0), (b'four', 4.0)]),
        ({'two': 2.0, 'one': 1.0}, 0, [(b'three', 3.0), (b'four', 4.0)])
    ]
)
@pytest.mark.parametrize('ch', [False, True])
def test_zadd_with_xx(r, param, changed, state, ch):
    testtools.zadd(r, 'foo', {'four': 4.0, 'three': 3.0})
    assert testtools.zadd(r, 'foo', param, xx=True, ch=ch) == (changed if ch else 0)
    assert r.zrange('foo', 0, -1, withscores=True) == state


@testtools.run_test_if_redispy_ver('above', '3')
@pytest.mark.parametrize('ch', [False, True])
def test_zadd_with_nx_and_xx(r, ch):
    testtools.zadd(r, 'foo', {'four': 4.0, 'three': 3.0})
    with pytest.raises(redis.DataError):
        testtools.zadd(r, 'foo', {'four': -4.0, 'three': -3.0}, nx=True, xx=True, ch=ch)


@pytest.mark.skipif(REDIS_VERSION < Version('3.1'), reason="Test is only applicable to redis-py 3.1+")
@pytest.mark.parametrize('ch', [False, True])
def test_zadd_incr(r, ch):
    testtools.zadd(r, 'foo', {'four': 4.0, 'three': 3.0})
    assert testtools.zadd(r, 'foo', {'four': 1.0}, incr=True, ch=ch) == 5.0
    assert testtools.zadd(r, 'foo', {'three': 1.0}, incr=True, nx=True, ch=ch) is None
    assert r.zscore('foo', 'three') == 3.0
    assert testtools.zadd(r, 'foo', {'bar': 1.0}, incr=True, xx=True, ch=ch) is None
    assert testtools.zadd(r, 'foo', {'three': 1.0}, incr=True, xx=True, ch=ch) == 4.0
