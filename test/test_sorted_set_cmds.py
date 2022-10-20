import redis.client
from packaging.version import Version

import testtools

REDIS_VERSION = Version(redis.__version__)
pytestmark = [
    testtools.run_test_if_redispy_ver('above', '3'),
]


def test_zpopmin(r):
    testtools.zadd(r, 'foo', {'one': 1})
    testtools.zadd(r, 'foo', {'two': 2})
    testtools.zadd(r, 'foo', {'three': 3})
    assert r.zpopmin('foo', count=2) == [(b'one', 1.0), (b'two', 2.0)]
    assert r.zpopmin('foo', count=2) == [(b'three', 3.0)]


def test_zpopmin_too_many(r):
    testtools.zadd(r, 'foo', {'one': 1})
    testtools.zadd(r, 'foo', {'two': 2})
    testtools.zadd(r, 'foo', {'three': 3})
    assert r.zpopmin('foo', count=5) == [(b'one', 1.0), (b'two', 2.0), (b'three', 3.0)]


def test_zpopmax(r):
    testtools.zadd(r, 'foo', {'one': 1})
    testtools.zadd(r, 'foo', {'two': 2})
    testtools.zadd(r, 'foo', {'three': 3})
    assert r.zpopmax('foo', count=2) == [(b'three', 3.0), (b'two', 2.0)]
    assert r.zpopmax('foo', count=2) == [(b'one', 1.0)]


def test_zpopmax_too_many(r):
    testtools.zadd(r, 'foo', {'one': 1})
    testtools.zadd(r, 'foo', {'two': 2})
    testtools.zadd(r, 'foo', {'three': 3})
    assert r.zpopmax('foo', count=5) == [(b'three', 3.0), (b'two', 2.0), (b'one', 1.0), ]


def test_bzpopmin(r):
    testtools.zadd(r, 'foo', {'one': 1, 'two': 2, 'three': 3})
    testtools.zadd(r, 'bar', {'a': 1.5, 'b': 2, 'c': 3})
    assert r.bzpopmin(['foo', 'bar'], 0) == (b'foo', b'one', 1.0)
    assert r.bzpopmin(['foo', 'bar'], 0) == (b'foo', b'two', 2.0)
    assert r.bzpopmin(['foo', 'bar'], 0) == (b'foo', b'three', 3.0)
    assert r.bzpopmin(['foo', 'bar'], 0) == (b'bar', b'a', 1.5)


def test_bzpopmax(r):
    testtools.zadd(r, 'foo', {'one': 1, 'two': 2, 'three': 3})
    testtools.zadd(r, 'bar', {'a': 1.5, 'b': 2.5, 'c': 3.5})
    assert r.bzpopmax(['foo', 'bar'], 0) == (b'foo', b'three', 3.0)
    assert r.bzpopmax(['foo', 'bar'], 0) == (b'foo', b'two', 2.0)
    assert r.bzpopmax(['foo', 'bar'], 0) == (b'foo', b'one', 1.0)
    assert r.bzpopmax(['foo', 'bar'], 0) == (b'bar', b'c', 3.5)
