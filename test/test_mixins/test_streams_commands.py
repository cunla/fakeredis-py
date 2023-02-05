import pytest

import redis

from fakeredis._stream import XStream


def test_xstream(r):
    stream = XStream()
    stream.add([0, 0, 1, 1, 2, 2, 3, 3], '0-1')
    stream.add([1, 1, 2, 2, 3, 3, 4, 4], '1-2')
    stream.add([2, 2, 3, 3, 4, 4], '1-3')
    stream.add([3, 3, 4, 4], '2-1')
    stream.add([3, 3, 4, 4], '2-2')
    stream.add([3, 3, 4, 4], '3-1')
    assert len(stream) == 6
    i = iter(stream)
    assert next(i) == [b'0-1', [[0, 0, 1, 1, 2, 2, 3, 3]]]
    assert next(i) == [b'1-2', [[1, 1, 2, 2, 3, 3, 4, 4]]]
    assert next(i) == [b'1-3', [[2, 2, 3, 3, 4, 4]]]
    assert next(i) == [b'2-1', [[3, 3, 4, 4]]]
    assert next(i) == [b'2-2', [[3, 3, 4, 4]]]

    assert stream.find_index('1-2') == 1
    assert stream.find_index('0-1') == 0
    assert stream.find_index('2-1') == 3
    assert stream.find_index('1-4') == 3

    lst = stream.irange((0, 2), (3, 0))
    assert len(lst) == 4


@pytest.mark.max_server('6.2.8')
def test_xadd(r: redis.Redis):
    stream = "stream"
    m1 = r.xadd(stream, {"some": "other"})
    ts1, seq1 = m1.decode().split('-')
    seq1 = int(seq1)
    m2 = r.xadd(stream, {'add': 'more'}, id=f'{ts1}-{seq1 + 1}')
    ts2, seq2 = m2.decode().split('-')
    assert ts1 == ts2
    assert int(seq2) == int(seq1) + 1

    stream = "stream2"
    m1 = r.xadd(stream, {"some": "other"})
    ts1, seq1 = m1.decode().split('-')
    ts1 = int(ts1) - 1
    with pytest.raises(redis.ResponseError):
        r.xadd(stream, {'add': 'more'}, id=f'{ts1}-*')
    with pytest.raises(redis.ResponseError):
        r.xadd(stream, {'add': 'more'}, id=f'{ts1}-1')


@pytest.mark.min_server('7')
def test_xadd_redis7(r: redis.Redis):
    stream = "stream"
    m1 = r.xadd(stream, {"some": "other"})
    ts1, seq1 = m1.decode().split('-')
    m2 = r.xadd(stream, {'add': 'more'}, id=f'{ts1}-*')
    ts2, seq2 = m2.decode().split('-')
    assert ts1 == ts2
    assert int(seq2) == int(seq1) + 1

    stream = "stream2"
    m1 = r.xadd(stream, {"some": "other"})
    ts1, seq1 = m1.decode().split('-')
    ts1 = int(ts1) - 1
    with pytest.raises(redis.ResponseError):
        r.xadd(stream, {'add': 'more'}, id=f'{ts1}-*')
    with pytest.raises(redis.ResponseError):
        r.xadd(stream, {'add': 'more'}, id=f'{ts1}-1')


def test_xadd_nomkstream(r: redis.Redis):
    r.xadd('stream2', {"some": "other"}, nomkstream=True)
    assert r.xlen('stream2') == 0
    # nomkstream option
    stream = "stream"
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"some": "other"}, nomkstream=False)
    assert r.xlen(stream) == 2
    r.xadd(stream, {"some": "other"}, nomkstream=True)
    assert r.xlen(stream) == 3


def test_xrevrange(r: redis.Redis):
    stream = "stream"
    m1 = r.xadd(stream, {"foo": "bar"})
    m2 = r.xadd(stream, {"foo": "bar"})
    m3 = r.xadd(stream, {"foo": "bar"})
    m4 = r.xadd(stream, {"foo": "bar"})

    def get_ids(results):
        return [result[0] for result in results]

    results = r.xrevrange(stream, max=m4)
    assert get_ids(results) == [m4, m3, m2, m1]

    results = r.xrevrange(stream, max=m3, min=m2)
    assert get_ids(results) == [m3, m2]

    results = r.xrevrange(stream, min=m3)
    assert get_ids(results) == [m4, m3]

    results = r.xrevrange(stream, min=m2, count=1)
    assert get_ids(results) == [m4]


def test_xrange(r: redis.Redis):
    stream = "stream"
    m1 = r.xadd(stream, {"foo": "bar"})
    m2 = r.xadd(stream, {"foo": "bar"})
    m3 = r.xadd(stream, {"foo": "bar"})
    m4 = r.xadd(stream, {"foo": "bar"})

    def get_ids(results):
        return [result[0] for result in results]

    results = r.xrange(stream, min=m1)
    assert get_ids(results) == [m1, m2, m3, m4]

    results = r.xrange(stream, min=m2, max=m3)
    assert get_ids(results) == [m2, m3]

    results = r.xrange(stream, max=m3)
    assert get_ids(results) == [m1, m2, m3]

    results = r.xrange(stream, max=m2, count=1)
    assert get_ids(results) == [m1]


@pytest.mark.xfail
def test_xadd_minlen_and_limit(r: redis.Redis):
    stream = "stream"

    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})

    # Future self: No limits without approximate, according to the api
    with pytest.raises(redis.ResponseError):
        assert r.xadd(stream, {"foo": "bar"}, maxlen=3, approximate=False, limit=2)

    # limit can not be provided without maxlen or minid
    with pytest.raises(redis.ResponseError):
        assert r.xadd(stream, {"foo": "bar"}, limit=2)

    # maxlen with a limit
    assert r.xadd(stream, {"foo": "bar"}, maxlen=3, approximate=True, limit=2)
    r.delete(stream)

    # maxlen and minid can not be provided together
    with pytest.raises(redis.DataError):
        assert r.xadd(stream, {"foo": "bar"}, maxlen=3, minid="sometestvalue")

    # minid with a limit
    m1 = r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    assert r.xadd(stream, {"foo": "bar"}, approximate=True, minid=m1, limit=3)

    # pure minid
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    m4 = r.xadd(stream, {"foo": "bar"})
    assert r.xadd(stream, {"foo": "bar"}, approximate=False, minid=m4)

    # minid approximate
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    m3 = r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"foo": "bar"})
    assert r.xadd(stream, {"foo": "bar"}, approximate=True, minid=m3)
