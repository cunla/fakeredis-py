import pytest

import redis


@pytest.mark.xfail
def test_xadd_nomkstream(r: redis.Redis):
    # nomkstream option
    stream = "stream"
    r.xadd(stream, {"foo": "bar"})
    r.xadd(stream, {"some": "other"}, nomkstream=False)
    assert r.xlen(stream) == 2
    r.xadd(stream, {"some": "other"}, nomkstream=True)
    assert r.xlen(stream) == 3


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


@pytest.mark.xfail
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
