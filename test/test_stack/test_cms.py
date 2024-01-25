import pytest
import redis

json_tests = pytest.importorskip("probables")


def test_cms_create(r: redis.Redis):
    assert r.cms().initbydim("cmsDim", 100, 5)
    assert r.cms().initbyprob("cmsProb", 0.01, 0.01)

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


def test_cms_incrby(r: redis.Redis):
    assert r.cms().initbydim("cmsDim", 100, 5)
    assert r.cms().initbyprob("cmsProb", 0.01, 0.01)

    assert r.cms().incrby("cmsDim", ["foo"], [3]) == [3]
    assert r.cms().incrby("cmsDim", ["foo", "bar"], [4, 1]) == [7, 1]
    assert r.cms().query("cmsDim", "foo") == [7]
    assert r.cms().query("cmsDim", "foo", "bar") == [7, 1]
    assert r.cms().query("cmsDim", "noexist") == [0]

    with pytest.raises(redis.exceptions.ResponseError):
        r.cms().query("cmsDim")

    with pytest.raises(redis.exceptions.ResponseError):
        r.cms().query("noexist", "foo")


def test_cms_merge(r: redis.Redis):
    assert r.cms().initbydim("cmsDim", 100, 5)
    assert r.cms().initbydim("cms2", 100, 5)

    assert r.cms().incrby("cmsDim", ["foo"], [3]) == [3]
    assert r.cms().incrby("cms2", ["foo", "bar"], [4, 1]) == [4, 1]
    assert r.cms().merge("cmsDim", 1, ["cms2"])
    assert r.cms().query("cmsDim", "foo", "bar") == [7, 1]


def test_cms_merge(r: redis.Redis):
    assert r.cms().initbydim("A", 1000, 5)
    assert r.cms().initbydim("B", 1000, 5)
    assert r.cms().initbydim("C", 1000, 5)

    assert r.cms().incrby("A", ["foo", "bar", "baz"], [5, 3, 9])
    assert r.cms().incrby("B", ["foo", "bar", "baz"], [2, 3, 1])
    assert r.cms().query("A", "foo", "bar", "baz") == [5, 3, 9]
    assert r.cms().query("B", "foo", "bar", "baz") == [2, 3, 1]
    assert r.cms().merge("C", 2, ["A", "B"])
    assert r.cms().query("C", "foo", "bar", "baz") == [7, 6, 10]

    assert r.cms().merge("C", 2, ["A", "B"], ["1", "2"])
    assert r.cms().query("C", "foo", "bar", "baz") == [9, 9, 11]

    assert r.cms().merge("C", 2, ["A", "B"], ["2", "3"])
    assert r.cms().query("C", "foo", "bar", "baz") == [16, 15, 21]
