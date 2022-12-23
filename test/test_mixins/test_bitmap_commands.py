import pytest
import redis
import redis.client

from test.testtools import raw_command


def test_getbit(r):
    r.setbit('foo', 3, 1)
    assert r.getbit('foo', 0) == 0
    assert r.getbit('foo', 1) == 0
    assert r.getbit('foo', 2) == 0
    assert r.getbit('foo', 3) == 1
    assert r.getbit('foo', 4) == 0
    assert r.getbit('foo', 100) == 0


def test_getbit_wrong_type(r):
    r.rpush('foo', b'x')
    with pytest.raises(redis.ResponseError):
        r.getbit('foo', 1)


def test_multiple_bits_set(r):
    r.setbit('foo', 1, 1)
    r.setbit('foo', 3, 1)
    r.setbit('foo', 5, 1)

    assert r.getbit('foo', 0) == 0
    assert r.getbit('foo', 1) == 1
    assert r.getbit('foo', 2) == 0
    assert r.getbit('foo', 3) == 1
    assert r.getbit('foo', 4) == 0
    assert r.getbit('foo', 5) == 1
    assert r.getbit('foo', 6) == 0


def test_unset_bits(r):
    r.setbit('foo', 1, 1)
    r.setbit('foo', 2, 0)
    r.setbit('foo', 3, 1)
    assert r.getbit('foo', 1) == 1
    r.setbit('foo', 1, 0)
    assert r.getbit('foo', 1) == 0
    r.setbit('foo', 3, 0)
    assert r.getbit('foo', 3) == 0


def test_get_set_bits(r):
    # set bit 5
    assert not r.setbit('a', 5, True)
    assert r.getbit('a', 5)
    # unset bit 4
    assert not r.setbit('a', 4, False)
    assert not r.getbit('a', 4)
    # set bit 4
    assert not r.setbit('a', 4, True)
    assert r.getbit('a', 4)
    # set bit 5 again
    assert r.setbit('a', 5, True)
    assert r.getbit('a', 5)


def test_setbits_and_getkeys(r):
    # The bit operations and the get commands
    # should play nicely with each other.
    r.setbit('foo', 1, 1)
    assert r.get('foo') == b'@'
    r.setbit('foo', 2, 1)
    assert r.get('foo') == b'`'
    r.setbit('foo', 3, 1)
    assert r.get('foo') == b'p'
    r.setbit('foo', 9, 1)
    assert r.get('foo') == b'p@'
    r.setbit('foo', 54, 1)
    assert r.get('foo') == b'p@\x00\x00\x00\x00\x02'


def test_setbit_wrong_type(r):
    r.rpush('foo', b'x')
    with pytest.raises(redis.ResponseError):
        r.setbit('foo', 0, 1)


def test_setbit_expiry(r):
    r.set('foo', b'0x00', ex=10)
    r.setbit('foo', 1, 1)
    assert r.ttl('foo') > 0


def test_bitcount(r):
    r.delete('foo')
    assert r.bitcount('foo') == 0
    r.setbit('foo', 1, 1)
    assert r.bitcount('foo') == 1
    r.setbit('foo', 8, 1)
    assert r.bitcount('foo') == 2
    assert r.bitcount('foo', 1, 1) == 1
    r.setbit('foo', 57, 1)
    assert r.bitcount('foo') == 3
    r.set('foo', ' ')
    assert r.bitcount('foo') == 1
    r.set('key', 'foobar')
    with pytest.raises(redis.ResponseError):
        raw_command(r, 'bitcount', 'key', '1', '2', 'dsd')
    assert r.bitcount('key') == 26
    assert r.bitcount('key', start=0, end=0) == 4
    assert r.bitcount('key', start=1, end=1) == 6


@pytest.mark.max_server('6')
def test_bitcount_mode_redis6(r):
    r.set('key', 'foobar')
    with pytest.raises(redis.ResponseError):
        r.bitcount('key', start=1, end=1, mode='byte')
    with pytest.raises(redis.ResponseError):
        r.bitcount('key', start=1, end=1, mode='bit')


@pytest.mark.min_server('7')
def test_bitcount_mode(r):
    r.set('key', 'foobar')
    assert r.bitcount('key', start=1, end=1, mode='byte') == 6
    assert r.bitcount('key', start=5, end=30, mode='bit') == 17


def test_bitcount_wrong_type(r):
    r.rpush('foo', b'x')
    with pytest.raises(redis.ResponseError):
        r.bitcount('foo')


def test_bitop(r):
    r.set('key1', 'foobar')
    r.set('key2', 'abcdef')

    assert r.bitop('and', 'dest', 'key1', 'key2') == 6
    assert r.get('dest') == b'`bc`ab'

    assert r.bitop('not', 'dest1', 'key1') == 6
    assert r.get('dest1') == b'\x99\x90\x90\x9d\x9e\x8d'

    assert r.bitop('or', 'dest-or', 'key1', 'key2') == 6
    assert r.get('dest-or') == b'goofev'

    assert r.bitop('xor', 'dest-xor', 'key1', 'key2') == 6
    assert r.get('dest-xor') == b'\x07\r\x0c\x06\x04\x14'

    with pytest.raises(redis.ResponseError):
        r.bitop('not', 'dest', 'key1', 'key2')
    with pytest.raises(redis.ResponseError):
        r.bitop('badop', 'dest', 'key1', 'key2')
