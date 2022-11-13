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


@testtools.run_test_if_redispy_ver('above', '4.2.0')
def test_sintercard(r):
    r.sadd('foo', 'member1')
    r.sadd('foo', 'member2')
    r.sadd('bar', 'member2')
    r.sadd('bar', 'member3')
    assert r.sintercard(2, ['foo', 'bar']) == 1
    assert r.sintercard(1, ['foo']) == 2


@testtools.run_test_if_redispy_ver('above', '4.2.0')
def test_sintercard_key_doesnt_exist(r):
    r.sadd('foo', 'member1')
    r.sadd('foo', 'member2')
    r.sadd('bar', 'member2')
    r.sadd('bar', 'member3')
    assert r.sintercard(2, ['foo', 'bar']) == 1
    assert r.sintercard(1, ['foo']) == 2
    assert r.sintercard(1, ['foo'], limit=1) == 1
    assert r.sintercard(3, ['foo', 'bar', 'ddd']) == 0


@testtools.run_test_if_redispy_ver('above', '4.2.0')
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


@testtools.run_test_if_redispy_ver('above', '4.2.0')
def test_sintercard_wrong_type(r):
    testtools.zadd(r, 'foo', {'member': 1})
    r.sadd('bar', 'member')
    with pytest.raises(redis.ResponseError):
        r.sintercard(2, ['foo', 'bar'])
    with pytest.raises(redis.ResponseError):
        r.sintercard(2, ['bar', 'foo'])


@testtools.run_test_if_redispy_ver('above', '4.2.0')
def test_sintercard_syntax_error(r):
    testtools.zadd(r, 'foo', {'member': 1})
    r.sadd('bar', 'member')
    with pytest.raises(redis.ResponseError):
        r.sintercard(3, ['foo', 'bar'])
    with pytest.raises(redis.ResponseError):
        r.sintercard(1, ['bar', 'foo'])
    with pytest.raises(redis.ResponseError):
        r.sintercard(1, ['bar', 'foo'], limit='x')
