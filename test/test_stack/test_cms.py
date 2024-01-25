import pytest
import redis

json_tests = pytest.importorskip("probables")


def test_cms_create(r: redis.Redis):
    assert r.cms().initbydim("cmsDim", 100, 5)
    assert r.cms().initbyprob("cmsProb", 0.01, 0.01)

    assert r.cms().incrby("cmsDim", ["foo"], [3]) == [3]
    assert r.cms().incrby("cmsDim", ["foo", "bar"], [4, 1]) == [7, 1]
    assert r.cms().query("cmsDim", "foo") == [7]
    assert r.cms().query("cmsDim", "foo", "bar") == [7, 1]
    assert r.cms().query("cmsDim", "noexist") == [0]

    with pytest.raises(redis.exceptions.ResponseError):
        r.cms().initbydim("cmsDim", 1, 5)

    with pytest.raises(redis.exceptions.ResponseError):
        r.cms().initbydim("cmsDim2", 0, 5)

    with pytest.raises(redis.exceptions.ResponseError):
        r.cms().initbydim("cmsDim2", 3, 0)

    with pytest.raises(redis.exceptions.ResponseError):
        r.cms().initbyprob("cmsProb", 0.01, 0.1)

    with pytest.raises(redis.exceptions.ResponseError):
        r.cms().initbyprob("cmsProb2", 2, 0.01)

    with pytest.raises(redis.exceptions.ResponseError):
        r.cms().initbyprob("cmsProb2", 0.01, 0)

    with pytest.raises(redis.exceptions.ResponseError):
        r.cms().query("cmsDim")

    with pytest.raises(redis.exceptions.ResponseError):
        r.cms().query("noexist", "foo")
