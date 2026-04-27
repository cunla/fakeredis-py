import pytest
import redis
import valkey

from test import testtools
from test.testtools import get_protocol_version

json_tests = pytest.importorskip("probables")
pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("dragonfly"),
    ]
)


def test_cms_type(r: redis.Redis):
    assert r.cms().initbydim("cmsDim", 100, 5)
    assert r.type("cmsDim") == b"CMSk-TYPE"


def test_cms_create(r: redis.Redis):
    assert r.cms().initbydim("cmsDim", 100, 5)
    assert r.cms().initbyprob("cmsProb", 0.01, 0.01)

    with pytest.raises(Exception) as ctx:
        r.cms().initbydim("cmsDim", 1, 5)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.cms().initbydim("cmsDim2", 0, 5)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.cms().initbydim("cmsDim2", 3, 0)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.cms().initbyprob("cmsProb", 0.01, 0.1)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.cms().initbyprob("cmsProb2", 2, 0.01)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.cms().initbyprob("cmsProb2", 0.01, 0)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_cms_incrby(r: redis.Redis):
    assert r.cms().initbydim("cmsDim", 100, 5)
    assert r.cms().initbyprob("cmsProb", 0.01, 0.01)

    assert r.cms().incrby("cmsDim", ["foo"], [3]) == [3]
    assert r.cms().incrby("cmsDim", ["foo", "bar"], [4, 1]) == [7, 1]
    assert r.cms().query("cmsDim", "foo") == [7]
    assert r.cms().query("cmsDim", "foo", "bar") == [7, 1]
    assert r.cms().query("cmsDim", "noexist") == [0]

    with pytest.raises(Exception) as ctx:
        r.cms().query("cmsDim")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.cms().query("noexist", "foo")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "CMS.INCRBY", "cmsDim", "foo", 1, "bar")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception, match="CMS: key does not exist") as ctx:
        r.cms().incrby("noexist", ["foo", "bar"], [3, 4])

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception, match="CMS: Cannot parse number") as ctx:
        r.cms().incrby("cmsDim", ["foo", "bar"], [3, "four"])

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_cms_merge(r: redis.Redis):
    assert r.cms().initbydim("cmsDim", 100, 5)
    assert r.cms().initbydim("cms2", 100, 5)

    assert r.cms().incrby("cmsDim", ["foo"], [3]) == [3]
    assert r.cms().incrby("cms2", ["foo", "bar"], [4, 1]) == [4, 1]
    assert r.cms().merge("cmsDim", 1, ["cms2"])
    assert r.cms().query("cmsDim", "foo", "bar") == [4, 1]

    with pytest.raises(Exception, match="CMS: key does not exist") as ctx:
        r.cms().merge("noexist", 1, ["cms2"])

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception, match="CMS: Number of keys must be positive") as ctx:
        r.cms().merge("cms2", 0, ["cmsDim"])

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception, match="wrong number of arguments for '.*' command") as ctx:
        r.cms().merge("cms2", 1, [])

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception, match="CMS: wrong number of keys/weights") as ctx:
        r.cms().merge("cmsDim", 1, ["cms2", "cms1"], [4, 3])

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception, match="CMS: key does not exist") as ctx:
        r.cms().merge("cmsDim", 2, ["cms2", "noexist"], [4, 3])

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.min_redis_version("7")
def test_cms_info(r: redis.Redis):
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
    info = r.cms().info("A")
    if get_protocol_version(r) == 2:
        assert info.width == 1000
        assert info.depth == 5
        assert info.count == 17
    else:
        assert info[b"width"] == 1000
        assert info[b"depth"] == 5
        assert info[b"count"] == 17
    with pytest.raises(Exception, match="CMS: key does not exist") as ctx:
        r.cms().info("noexist")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.xfail(reason="Bug in pyprobables")
def test_cms_merge_fail(r: redis.Redis):
    assert r.cms().initbydim("A", 1000, 5)
    assert r.cms().initbydim("B", 1000, 5)
    assert r.cms().initbydim("C", 1000, 5)

    assert r.cms().incrby("A", ["foo", "bar", "baz"], [5, 3, 9])
    assert r.cms().incrby("B", ["foo", "bar", "baz"], [2, 3, 1])
    assert r.cms().query("A", "foo", "bar", "baz") == [5, 3, 9]
    assert r.cms().query("B", "foo", "bar", "baz") == [2, 3, 1]
    assert r.cms().merge("C", 2, ["A", "B"])
    assert r.cms().query("C", "foo", "bar", "baz") == [7, 6, 10]

    assert r.cms().merge("C", 2, ["A", "B"], ["2", "3"])
    info = r.cms().info("C")
    assert info.width == 1000
    assert info.depth == 5
    assert info.count == 52
