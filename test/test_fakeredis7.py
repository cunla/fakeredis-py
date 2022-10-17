import os
from time import sleep
from xmlrpc.client import ResponseError

import pytest
import redis
import redis.client
from packaging.version import Version
from redis.exceptions import ResponseError

import testtools
from testtools import raw_command

REDIS_VERSION = Version(redis.__version__)
pytestmark = [
    pytest.mark.min_server('7'),
]
fake_only = pytest.mark.parametrize(
    'create_redis',
    [pytest.param('FakeStrictRedis', marks=pytest.mark.fake)],
    indirect=True
)


def test_script_exists(r):
    # test response for no arguments by bypassing the py-redis command
    # as it requires at least one argument
    with pytest.raises(redis.ResponseError):
        raw_command(r, "SCRIPT EXISTS")

    # use single character characters for non-existing scripts, as those
    # will never be equal to an actual sha1 hash digest
    assert r.script_exists("a") == [0]
    assert r.script_exists("a", "b", "c", "d", "e", "f") == [0, 0, 0, 0, 0, 0]

    sha1_one = r.script_load("return 'a'")
    assert r.script_exists(sha1_one) == [1]
    assert r.script_exists(sha1_one, "a") == [1, 0]
    assert r.script_exists("a", "b", "c", sha1_one, "e") == [0, 0, 0, 1, 0]

    sha1_two = r.script_load("return 'b'")
    assert r.script_exists(sha1_one, sha1_two) == [1, 1]
    assert r.script_exists("a", sha1_one, "c", sha1_two, "e", "f") == [0, 1, 0, 1, 0, 0]


def test_set_get_nx(r):
    # Note: this will most likely fail on a 7.0 server, based on the docs for SET
    assert raw_command(r, 'set', 'foo', 'bar', 'NX', 'GET') is None


def test_zadd_minus_zero(r):
    testtools.zadd(r, 'foo', {'a': -0.0})
    testtools.zadd(r, 'foo', {'a': 0.0})
    assert raw_command(r, 'zscore', 'foo', 'a') == b'0'


@pytest.mark.slow
def test_expire_should_expire_key(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    r.expire('foo', 1)
    sleep(1.5)
    assert r.get('foo') is None
    assert r.expire('bar', 1) is False


@testtools.run_test_if_redispy_ver('above', '4.2.0')
def test_expire_should_throw_error(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    with pytest.raises(ResponseError):
        r.expire('foo', 1, nx=True, xx=True)
    with pytest.raises(ResponseError):
        r.expire('foo', 1, nx=True, gt=True)
    with pytest.raises(ResponseError):
        r.expire('foo', 1, nx=True, lt=True)
    with pytest.raises(ResponseError):
        r.expire('foo', 1, gt=True, lt=True)


@testtools.run_test_if_redispy_ver('above', '4.2.0')
def test_expire_should_not_expire__when_no_expire_is_set(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    assert r.expire('foo', 1, xx=True) == 0


@testtools.run_test_if_redispy_ver('above', '4.2.0')
def test_expire_should_not_expire__when_expire_is_set(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    assert r.expire('foo', 1, nx=True) == 1
    assert r.expire('foo', 2, nx=True) == 0


@testtools.run_test_if_redispy_ver('above', '4.2.0')
def test_expire_should_expire__when_expire_is_greater(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    assert r.expire('foo', 100) == 1
    assert r.get('foo') == b'bar'
    assert r.expire('foo', 200, gt=True) == 1


@testtools.run_test_if_redispy_ver('above', '4.2.0')
def test_expire_should_expire__when_expire_is_lessthan(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    assert r.expire('foo', 20) == 1
    assert r.expire('foo', 10, lt=True) == 1


def test_sintercard(r):
    r.sadd('foo', 'member1')
    r.sadd('foo', 'member2')
    r.sadd('bar', 'member2')
    r.sadd('bar', 'member3')
    assert r.sintercard(2, ['foo', 'bar']) == 1
    assert r.sintercard(1, ['foo']) == 2


def test_sintercard_key_doesnt_exist(r):
    r.sadd('foo', 'member1')
    r.sadd('foo', 'member2')
    r.sadd('bar', 'member2')
    r.sadd('bar', 'member3')
    assert r.sintercard(2, ['foo', 'bar']) == 1
    assert r.sintercard(1, ['foo']) == 2
    assert r.sintercard(1, ['foo'], limit=1) == 1
    assert r.sintercard(3, ['foo', 'bar', 'ddd']) == 0


def test_sintercard_bytes_keys(r):
    foo = os.urandom(10)
    bar = os.urandom(10)
    r.sadd(foo, 'member1')
    r.sadd(foo, 'member2')
    r.sadd(bar, 'member2')
    r.sadd(bar, 'member3')
    assert r.sintercard(2, [foo, bar]) == 1
    assert r.sintercard(1, [foo]) == 2
    assert r.sintercard(1, [foo], limit=1) == 1


def test_sintercard_wrong_type(r):
    testtools.zadd(r, 'foo', {'member': 1})
    r.sadd('bar', 'member')
    with pytest.raises(redis.ResponseError):
        r.sintercard(2, ['foo', 'bar'])
    with pytest.raises(redis.ResponseError):
        r.sintercard(2, ['bar', 'foo'])


def test_sintercard_syntax_error(r):
    testtools.zadd(r, 'foo', {'member': 1})
    r.sadd('bar', 'member')
    with pytest.raises(redis.ResponseError):
        r.sintercard(3, ['foo', 'bar'])
    with pytest.raises(redis.ResponseError):
        r.sintercard(1, ['bar', 'foo'])
    with pytest.raises(redis.ResponseError):
        r.sintercard(1, ['bar', 'foo'], limit='x')
