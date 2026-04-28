import pytest
import redis
import valkey
from redis.commands.bf import BFInfo

from test import testtools
from fakeredis import _msgs as msgs

bloom_tests = pytest.importorskip("probables")

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("dragonfly"),
    ]
)


def intlist(obj):
    return [int(v) for v in obj]


def test_bf_type(r: redis.Redis):
    assert r.bf().create("bloom", 0.01, 1000)
    assert r.type("bloom") == b"MBbloom--"


def test_create_bf(r: redis.Redis):
    assert r.bf().create("bloom", 0.01, 1000)
    assert r.bf().create("bloom_e", 0.01, 1000, expansion=1)
    assert r.bf().create("bloom_ns", 0.01, 1000, noScale=True)


def test_create_cf(r: redis.Redis):
    assert r.cf().create("cuckoo", 1000)
    assert r.cf().create("cuckoo_e", 1000, expansion=1)
    assert r.cf().create("cuckoo_bs", 1000, bucket_size=4)
    assert r.cf().create("cuckoo_mi", 1000, max_iterations=10)
    assert r.cms().initbydim("cmsDim", 100, 5)
    assert r.cms().initbyprob("cmsProb", 0.01, 0.01)
    assert r.topk().reserve("topk", 5, 100, 5, 0.9)


def test_bf_reserve(r: redis.Redis):
    assert r.bf().reserve("bloom", 0.01, 1000)
    assert r.bf().reserve("bloom_ns", 0.01, 1000, noScale=True)
    with pytest.raises(Exception, match=msgs.NONSCALING_FILTERS_CANNOT_EXPAND_MSG) as ctx:
        assert r.bf().reserve("bloom_e", 0.01, 1000, expansion=1, noScale=True)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception, match=msgs.ITEM_EXISTS_MSG) as ctx:
        assert r.bf().reserve("bloom", 0.01, 1000)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_bf_add(r: redis.Redis):
    assert r.bf().add("key", "value") == 1
    assert r.bf().add("key", "value") == 0

    r.set("key1", "value")
    with pytest.raises(Exception) as ctx:
        r.bf().add("key1", "v")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    assert r.bf().create("bloom", 0.01, 1000)
    assert 1 == r.bf().add("bloom", "foo")
    assert 0 == r.bf().add("bloom", "foo")
    assert [0] == intlist(r.bf().madd("bloom", "foo"))
    assert [0, 1] == r.bf().madd("bloom", "foo", "bar")
    assert [0, 0, 1] == r.bf().madd("bloom", "foo", "bar", "baz")
    assert 1 == r.bf().exists("bloom", "foo")
    assert 0 == r.bf().exists("bloom", "noexist")
    assert [1, 0] == intlist(r.bf().mexists("bloom", "foo", "noexist"))


def test_bf_madd(r: redis.Redis):
    assert r.bf().madd("key", "v1", "v2", "v2") == [1, 1, 0]
    assert r.bf().madd("key", "v1", "v2", "v4") == [0, 0, 1]

    r.set("key1", "value")
    with pytest.raises(Exception) as ctx:
        r.bf().add("key1", "v")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_bf_card(r: redis.Redis):
    assert r.bf().madd("key", "v1", "v2", "v3") == [1, 1, 1]
    assert r.bf().card("key") == 3
    assert r.bf().card("key-new") == 0

    r.set("key1", "value")
    with pytest.raises(Exception) as ctx:
        r.bf().card("key1")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    # return 0 if the key does not exist
    assert r.bf().card("not_exist") == 0

    # Store a filter
    assert r.bf().add("bf1", "item_foo") == 1
    assert r.bf().card("bf1") == 1

    # Error when key is of a type other than Bloom filter.
    with pytest.raises(Exception) as ctx:
        r.set("setKey", "value")
        r.bf().card("setKey")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_bf_exists(r: redis.Redis):
    assert r.bf().madd("key", "v1", "v2", "v3") == [1, 1, 1]
    assert r.bf().exists("key", "v1") == 1
    assert r.bf().exists("key", "v5") == 0
    assert r.bf().exists("key-new", "v5") == 0

    r.set("key1", "value")
    with pytest.raises(Exception) as ctx:
        r.bf().add("key1", "v")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_bf_mexists(r: redis.Redis):
    assert r.bf().madd("key", "v1", "v2", "v3") == [1, 1, 1]
    assert r.bf().mexists("key", "v1") == [
        1,
    ]
    assert r.bf().mexists("key", "v1", "v5") == [1, 0]
    assert r.bf().mexists("key-new", "v5") == [
        0,
    ]

    r.set("key1", "value")
    with pytest.raises(Exception) as ctx:
        r.bf().add("key1", "v")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.supported_redis_versions(min_ver="7")
def test_bf_insert(r: redis.Redis):
    assert r.bf().create("key", 0.01, 1000)
    assert r.bf().insert("key", ["foo"]) == [1]
    assert r.bf().insert("key", ["foo", "bar"]) == [0, 1]
    assert r.bf().insert("captest", ["foo"], capacity=10) == [1]
    assert r.bf().insert("errtest", ["foo"], error=0.01) == [1]
    assert r.bf().exists("key", "foo") == 1
    assert r.bf().exists("key", "noexist") == 0
    assert r.bf().mexists("key", "foo", "noexist") == [1, 0]
    with pytest.raises(Exception, match=msgs.NOT_FOUND_MSG) as ctx:
        r.bf().insert("nocreate", [1, 2, 3], noCreate=True)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    # with pytest.raises(redis.exceptions.ResponseError, match=msgs.NONSCALING_FILTERS_CANNOT_EXPAND_MSG):
    #     r.bf().insert("nocreate", [1, 2, 3], expansion=2, noScale=True)
    assert r.bf().create("bloom", 0.01, 1000)
    assert [1] == intlist(r.bf().insert("bloom", ["foo"]))
    assert [0, 1] == intlist(r.bf().insert("bloom", ["foo", "bar"]))
    assert 1 == r.bf().exists("bloom", "foo")
    assert 0 == r.bf().exists("bloom", "noexist")
    assert [1, 0] == intlist(r.bf().mexists("bloom", "foo", "noexist"))
    info = r.bf().info("bloom")
    if testtools.get_protocol_version(r) == 2:
        assert 2 == info.get("insertedNum")
        assert 1000 == info.get("capacity")
        assert 1 == info.get("filterNum")
    else:
        assert 2 == info.get(b"Number of items inserted")
        assert 1000 == info.get(b"Capacity")
        assert 1 == info.get(b"Number of filters")


def test_bf_scandump_and_loadchunk(r: redis.Redis):
    r.bf().create("myBloom", "0.0001", "1000")

    # Test is probabilistic and might fail. It is OK to change variables if
    # certain to not break anything

    res = 0
    for x in range(1000):
        r.bf().add("myBloom", x)
        assert r.bf().exists("myBloom", x)
        rv = r.bf().exists("myBloom", f"nonexist_{x}")
        res += rv == x
    assert res < 5

    cmds = []
    first = 0
    while first is not None:
        cur = r.bf().scandump("myBloom", first)
        if cur[0] == 0:
            first = None
        else:
            first = cur[0]
            cmds.append(cur)

    # Remove the filter
    r.bf().client.delete("myBloom")

    # Now, load all the commands:
    for cmd in cmds:
        r.bf().loadchunk("myBloom1", *cmd)

    for x in range(1000):
        assert r.bf().exists("myBloom1", x), f"{x} not in filter"


@pytest.mark.resp2_only
def test_bf_info_resp2(r: redis.Redis):
    # Store a filter
    r.bf().create("nonscaling", "0.0001", "1000", noScale=True)
    info: BFInfo = r.bf().info("nonscaling")
    assert info.expansionRate is None

    expansion = 4
    r.bf().create("expanding", "0.0001", "1000", expansion=expansion)
    info = r.bf().info("expanding")
    assert info.expansionRate == 4
    assert info.capacity == 1000
    assert info.insertedNum == 0


@pytest.mark.supported_redis_versions(min_ver="7")
@pytest.mark.resp3_only
def test_bf_info_resp3(r: redis.Redis):
    # Store a filter
    r.bf().create("nonscaling", "0.0001", "1000", noScale=True)
    info = r.bf().info("nonscaling")
    assert info[b"Expansion rate"] is None

    expansion = 4
    r.bf().create("expanding", "0.0001", "1000", expansion=expansion)
    info = r.bf().info("expanding")
    assert info[b"Expansion rate"] == 4
    assert info[b"Capacity"] == 1000
    assert info[b"Number of items inserted"] == 0


@pytest.mark.resp3_only
@pytest.mark.supported_redis_versions(min_ver="7")
def test_bf_info_field_queries(r: redis.Redis):
    """BF.INFO with a specific field name returns only that value"""
    r.bf().create("bloom", 0.01, 1000)
    r.bf().add("bloom", "item1")
    assert testtools.raw_command(r, "BF.INFO", "bloom", "CAPACITY") == {b"Capacity": 1000}
    res = testtools.raw_command(r, "BF.INFO", "bloom", "SIZE")
    assert isinstance(res, dict)
    assert b"Size" in res
    assert testtools.raw_command(r, "BF.INFO", "bloom", "FILTERS") == {b"Number of filters": 1}
    assert testtools.raw_command(r, "BF.INFO", "bloom", "ITEMS") == {b"Number of items inserted": 1}
    with pytest.raises(Exception) as ctx:
        testtools.raw_command(r, "BF.INFO", "bloom", "BADFIELD")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.supported_redis_versions(min_ver="7")
def test_bf_info_nonscaling_expansion_field(r: redis.Redis):
    """BF.INFO EXPANSION on a non-scaling filter returns None"""
    r.bf().create("ns", 0.01, 1000, noScale=True)
    res = testtools.raw_command(r, "BF.INFO", "ns", "EXPANSION")
    expected_result = [None] if testtools.get_protocol_version(r) == 2 else {b"Expansion rate": None}
    assert res == expected_result


def test_bf_info_errors(r: redis.Redis):
    """BF.INFO raises errors for non-existent keys and too many arguments."""
    with pytest.raises(Exception) as ctx:
        r.bf().info("nokey")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    r.bf().create("bloom", 0.01, 1000)
    with pytest.raises(Exception) as ctx:
        r.execute_command("BF.INFO", "bloom", "CAPACITY", "EXTRA")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_bf_scandump_nonexistent(r: redis.Redis):
    """BF.SCANDUMP on a non-existent key raises NOT_FOUND."""
    with pytest.raises(Exception, match="not found") as ctx:
        r.execute_command("BF.SCANDUMP", "nokey", 0)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_bf_insert_missing_items_keyword(r: redis.Redis):
    """BF.INSERT without the ITEMS keyword raises an error."""
    with pytest.raises(Exception) as ctx:
        r.execute_command("BF.INSERT", "bloom", "foo")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_cf_scandump_and_loadchunk(r: redis.Redis):
    r.cf().create("myCuckoo", 1000)

    for x in range(100):
        r.cf().add("myCuckoo", x)
        assert r.cf().exists("myCuckoo", x)

    cmds = []
    first = 0
    while first is not None:
        cur = r.cf().scandump("myCuckoo", first)
        if cur[0] == 0:
            first = None
        else:
            first = cur[0]
            cmds.append(cur)

    r.cf().client.delete("myCuckoo")

    for cmd in cmds:
        r.cf().loadchunk("myCuckoo2", *cmd)

    for x in range(100):
        assert r.cf().exists("myCuckoo2", x), f"{x} not in filter"
