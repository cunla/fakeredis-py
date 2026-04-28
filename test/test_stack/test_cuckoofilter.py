import pytest
import redis
import valkey

from test.testtools import get_protocol_version

cuckoofilters_tests = pytest.importorskip("probables")

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("dragonfly"),
    ]
)


@pytest.mark.supported_redis_versions(min_ver="7")
def test_cf_type(r: redis.Redis):
    assert r.cf().create("cuckoo", 1000)
    assert r.type("cuckoo") == b"MBbloomCF"


@pytest.mark.supported_redis_versions(min_ver="7")
def test_cf_add_and_insert(r: redis.Redis):
    assert r.cf().create("cuckoo", 1000)
    assert r.cf().add("cuckoo", "filter")
    assert not r.cf().addnx("cuckoo", "filter")
    assert 1 == r.cf().addnx("cuckoo", "newItem")
    assert [1] == r.cf().insert("captest", ["foo"])
    assert [1] == r.cf().insert("captest", ["foo"], capacity=1000)
    assert [1] == r.cf().insertnx("captest", ["bar"])
    assert [1] == r.cf().insertnx("captest", ["food"], nocreate="1")
    assert [0, 0, 1] == r.cf().insertnx("captest", ["foo", "bar", "baz"])
    assert [0] == r.cf().insertnx("captest", ["bar"], capacity=1000)
    assert [1] == r.cf().insert("empty1", ["foo"], capacity=1000)
    assert [1] == r.cf().insertnx("empty2", ["bar"], capacity=1000)
    info = r.cf().info("captest")
    if get_protocol_version(r) == 2:
        assert info.get("insertedNum") == 5
        assert info.get("deletedNum") == 0
        assert info.get("filterNum") == 1
    else:
        assert info.get(b"Number of items inserted") == 5
        assert info.get(b"Number of items deleted") == 0
        assert info.get(b"Number of filters") == 1


def test_cf_exists_and_del(r: redis.Redis):
    assert r.cf().create("cuckoo", 1000)
    assert r.cf().add("cuckoo", "filter")
    assert r.cf().exists("cuckoo", "filter")
    assert not r.cf().exists("cuckoo", "notexist")
    assert [1, 0] == r.cf().mexists("cuckoo", "filter", "notexist")
    assert 1 == r.cf().count("cuckoo", "filter")
    assert 0 == r.cf().count("cuckoo", "notexist")
    assert r.cf().delete("cuckoo", "filter")
    assert 0 == r.cf().count("cuckoo", "filter")


def test_cf_count_non_existing(r: redis.Redis):
    assert r.cf().count("cuckoo", "non_existing") == 0
    assert r.cf().create("cuckoo", 1000)
    assert r.cf().add("cuckoo", "item1")
    assert r.cf().insert("cuckoo", ["item1", "item1", "item2"]) == [1, 1, 1]
    assert r.cf().count("cuckoo", "item1") == 3


def test_cf_add_autocreates_filter(r: redis.Redis):
    """CF.ADD on a non-existent key auto-creates the filter."""
    assert r.cf().add("newkey", "item") == 1
    assert r.cf().exists("newkey", "item") == 1


def test_cf_del_nonexistent_key(r: redis.Redis):
    """CF.DEL raises NOT_FOUND when the key does not exist."""
    with pytest.raises(Exception, match="[Nn]ot [Ff]ound") as ctx:
        r.cf().delete("nokey", "item")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_cf_info_nonexistent_key(r: redis.Redis):
    """CF.INFO raises an error when the key does not exist."""
    with pytest.raises(Exception) as ctx:
        r.cf().info("nokey")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_cf_reserve_key_exists(r: redis.Redis):
    """CF.RESERVE raises an error when the key already exists."""
    r.cf().create("cuckoo", 1000)
    with pytest.raises(Exception, match="item exists") as ctx:
        r.cf().create("cuckoo", 2000)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_cf_insert_errors(r: redis.Redis):
    """CF.INSERT and CF.INSERTNX raise errors for missing ITEMS keyword or nocreate."""
    with pytest.raises(Exception) as ctx:
        r.execute_command("CF.INSERT", "cuckoo", "foo")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.execute_command("CF.INSERTNX", "cuckoo", "foo")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception, match="[Nn]ot [Ff]ound") as ctx:
        r.execute_command("CF.INSERT", "nokey", "NOCREATE", "ITEMS", "foo")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception, match="[Nn]ot [Ff]ound") as ctx:
        r.execute_command("CF.INSERTNX", "nokey", "NOCREATE", "ITEMS", "foo")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_cf_scandump_nonexistent(r: redis.Redis):
    """CF.SCANDUMP on a non-existent key raises NOT_FOUND."""
    with pytest.raises(Exception, match="[Nn]ot [Ff]ound") as ctx:
        r.execute_command("CF.SCANDUMP", "nokey", 0)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_cf_scandump_and_loadchunk(r: redis.Redis):
    """CF.SCANDUMP and CF.LOADCHUNK round-trip a cuckoo filter."""
    r.cf().create("src", 1000)
    r.cf().add("src", "item1")
    r.cf().add("src", "item2")

    # dump all chunks
    chunks = []
    cursor = 0
    while True:
        chunk = r.execute_command("CF.SCANDUMP", "src", cursor)
        if chunk[0] == 0:
            break
        cursor = chunk[0]
        chunks.append(chunk)

    assert len(chunks) > 0

    # load into new key and verify
    for chunk in chunks:
        r.execute_command("CF.LOADCHUNK", "dst", chunk[0], chunk[1])
    assert r.cf().exists("dst", "item1") == 1
    assert r.cf().exists("dst", "item2") == 1
