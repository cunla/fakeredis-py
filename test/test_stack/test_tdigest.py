import math
from math import inf

import pytest
import redis
import valkey

from test.testtools import get_protocol_version

topk_tests = pytest.importorskip("probables")

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("dragonfly"),
    ]
)


@pytest.mark.supported_redis_versions(min_ver="7")
def test_tdigest_type(r: redis.Redis):
    assert r.tdigest().create("tDigest", 10)
    assert r.type("tDigest") == b"TDIS-TYPE"


@pytest.mark.supported_redis_versions(min_ver="7")
def test_tdigest_reset(r: redis.Redis):
    assert r.tdigest().create("tDigest", 10)
    # reset on empty histogram
    assert r.tdigest().reset("tDigest")
    # insert data-points into sketch
    assert r.tdigest().add("tDigest", list(range(10)))

    assert r.tdigest().reset("tDigest")
    # assert we have 0 unmerged
    info = r.tdigest().info("tDigest")
    assert 0 == info.get("unmerged_weight" if get_protocol_version(r) == 2 else b"Unmerged weight")


@pytest.mark.supported_redis_versions(min_ver="7")
def test_tdigest_merge(r: redis.Redis):
    assert r.tdigest().create("to-tDigest", 10)
    assert r.tdigest().create("from-tDigest", 10)
    # insert data-points into sketch
    assert r.tdigest().add("from-tDigest", [1.0] * 10)
    assert r.tdigest().add("to-tDigest", [2.0] * 10)
    # merge from-tdigest into to-tdigest
    assert r.tdigest().merge("to-tDigest", 1, "from-tDigest")
    # we should now have 110 weight on to-histogram
    info = r.tdigest().info("to-tDigest")
    if get_protocol_version(r) == 2:
        assert 20 == float(info["merged_weight"]) + float(info["unmerged_weight"])
    else:
        assert 20 == float(info[b"Merged weight"]) + float(info[b"Unmerged weight"])
    # test override
    assert r.tdigest().create("from-override", 10)
    assert r.tdigest().create("from-override-2", 10)
    assert r.tdigest().add("from-override", [3.0] * 10)
    assert r.tdigest().add("from-override-2", [4.0] * 10)
    assert r.tdigest().merge("to-tDigest", 2, "from-override", "from-override-2", override=True)

    assert r.tdigest().min("to-tDigest") == 3.0
    assert r.tdigest().max("to-tDigest") == 4.0


def test_tdigest_min_and_max(r: redis.Redis):
    assert r.tdigest().create("tDigest", 100)
    # insert data-points into sketch
    assert r.tdigest().add("tDigest", [1, 2, 3])
    # min/max
    assert 3 == r.tdigest().max("tDigest")
    assert 1 == r.tdigest().min("tDigest")


def test_tdigest_quantile(r: redis.Redis):
    assert r.tdigest().create("tDigest", 500)
    # insert data-points into sketch
    assert r.tdigest().add("tDigest", [x * 0.01 for x in range(1, 10000)])
    # assert min/max have the same result as quantile 0 and 1
    res = r.tdigest().quantile("tDigest", 1.0)
    assert r.tdigest().max("tDigest") == res[0]
    res = r.tdigest().quantile("tDigest", 0.0)
    assert r.tdigest().min("tDigest") == res[0]

    assert 1.0 == round(r.tdigest().quantile("tDigest", 0.01)[0], 2)
    assert 99.0 == round(r.tdigest().quantile("tDigest", 0.99)[0], 2)

    # test multiple quantiles
    assert r.tdigest().create("t-digest", 100)
    assert r.tdigest().add("t-digest", [1, 2, 3, 4, 5])
    assert [3.0, 5.0] == r.tdigest().quantile("t-digest", 0.5, 0.8)


def test_tdigest_cdf(r: redis.Redis):
    assert r.tdigest().create("tDigest", 100)
    # insert data-points into sketch
    assert r.tdigest().add("tDigest", list(range(1, 10)))
    assert 0.1 == round(r.tdigest().cdf("tDigest", 1.0)[0], 1)
    assert 0.9 == round(r.tdigest().cdf("tDigest", 9.0)[0], 1)
    res = r.tdigest().cdf("tDigest", 1.0, 9.0)
    assert [0.1, 0.9] == [round(x, 1) for x in res]


def test_tdigest_trimmed_mean(r: redis.Redis):
    assert r.tdigest().create("tDigest", 100)
    # insert data-points into sketch
    assert r.tdigest().add("tDigest", list(range(1, 10)))
    assert 5 == r.tdigest().trimmed_mean("tDigest", 0.1, 0.9)
    assert 4.5 == r.tdigest().trimmed_mean("tDigest", 0.4, 0.5)


def test_tdigest_rank(r: redis.Redis):
    assert r.tdigest().create("t-digest", 500)
    assert r.tdigest().add("t-digest", list(range(0, 20)))
    assert -1 == r.tdigest().rank("t-digest", -1)[0]
    assert 0 == r.tdigest().rank("t-digest", 0)[0]
    assert 10 == r.tdigest().rank("t-digest", 10)[0]
    assert [-1, 20, 9] == r.tdigest().rank("t-digest", -20, 20, 9)


def test_tdigest_revrank(r: redis.Redis):
    assert r.tdigest().create("t-digest", 500)
    assert r.tdigest().add("t-digest", list(range(0, 20)))
    assert -1 == r.tdigest().revrank("t-digest", 20)[0]
    assert 19 == r.tdigest().revrank("t-digest", 0)[0]
    assert [-1, 19, 9] == r.tdigest().revrank("t-digest", 21, 0, 10)


def test_tdigest_byrank(r: redis.Redis):
    assert r.tdigest().create("t-digest", 500)
    assert r.tdigest().add("t-digest", list(range(1, 11)))
    assert 1 == r.tdigest().byrank("t-digest", 0)[0]
    assert 10 == r.tdigest().byrank("t-digest", 9)[0]
    assert r.tdigest().byrank("t-digest", 100)[0] == inf
    with pytest.raises(Exception) as ctx:
        r.tdigest().byrank("t-digest", -1)[0]

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_tdigest_byrevrank(r: redis.Redis):
    assert r.tdigest().create("t-digest", 500)
    assert r.tdigest().add("t-digest", list(range(1, 11)))
    assert 10 == r.tdigest().byrevrank("t-digest", 0)[0]
    assert 1 == r.tdigest().byrevrank("t-digest", 9)[0]
    assert r.tdigest().byrevrank("t-digest", 100)[0] == -inf
    with pytest.raises(Exception) as ctx:
        r.tdigest().byrevrank("t-digest", -1)[0]

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_tdigest_quantile_nan(r: redis.Redis):
    r.tdigest().create("foo")
    r.tdigest().add("foo", [123])
    res = r.tdigest().quantile("foo", 0.9)
    assert isinstance(res, list)
    assert len(res) == 1
    assert math.isnan(float(res[0])), f"Expected NaN, got {res[0]}"

    res = r.tdigest().quantile("foo", 0)[0]
    assert math.isnan(float(res)), f"Expected NaN, got {res}"

    res = r.tdigest().quantile("foo", 1)[0]
    assert math.isnan(float(res)), f"Expected NaN, got {res}"


@pytest.mark.supported_redis_versions(min_ver="7")
def test_tdigest_create_default_compression(r: redis.Redis):
    """TDIGEST.CREATE without compression uses default of 100."""
    r.tdigest().create("td")
    info = r.tdigest().info("td")
    if get_protocol_version(r) == 2:
        assert info.get("compression") == 100
    else:
        assert info.get(b"Compression") == 100


def test_tdigest_create_already_exists(r: redis.Redis):
    """TDIGEST.CREATE raises an error when the key already exists."""
    r.tdigest().create("td", 100)
    with pytest.raises(Exception) as ctx:
        r.tdigest().create("td", 100)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_tdigest_commands_on_nonexistent_key(r: redis.Redis):
    """TDIGEST commands raise key-not-exist errors on missing keys."""
    with pytest.raises(Exception) as ctx:
        r.tdigest().reset("nokey")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().add("nokey", [1.0])
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().max("nokey")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().min("nokey")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().rank("nokey", 1.0)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().revrank("nokey", 1.0)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().quantile("nokey", 0.5)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().cdf("nokey", 1.0)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().trimmed_mean("nokey", 0.1, 0.9)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().byrank("nokey", 0)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().byrevrank("nokey", 0)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_tdigest_commands_on_empty_digest(r: redis.Redis):
    """TDIGEST commands on an empty digest return NaN or -2."""
    r.tdigest().create("td", 100)
    assert math.isnan(float(r.tdigest().max("td")))
    assert math.isnan(float(r.tdigest().min("td")))
    assert r.tdigest().rank("td", 1.0) == [-2]
    assert r.tdigest().revrank("td", 1.0) == [-2]
    assert math.isnan(float(r.tdigest().byrank("td", 0)[0]))
    assert math.isnan(float(r.tdigest().byrevrank("td", 0)[0]))
    assert math.isnan(float(r.tdigest().trimmed_mean("td", 0.1, 0.9)))


def test_tdigest_quantile_bad_value(r: redis.Redis):
    """TDIGEST.QUANTILE raises an error for quantile values outside [0, 1]."""
    r.tdigest().create("td", 100)
    r.tdigest().add("td", [1.0, 2.0, 3.0])
    with pytest.raises(Exception) as ctx:
        r.tdigest().quantile("td", -0.1)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.tdigest().quantile("td", 1.1)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_tdigest_trimmed_mean_bad_bounds(r: redis.Redis):
    """TDIGEST.TRIMMED_MEAN raises an error for invalid bounds."""
    r.tdigest().create("td", 100)
    r.tdigest().add("td", list(range(10)))
    with pytest.raises(Exception) as ctx:
        r.tdigest().trimmed_mean("td", 0.9, 0.1)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_tdigest_trimmed_mean_adjacent_bounds(r: redis.Redis):
    """TDIGEST.TRIMMED_MEAN with right == left + 1 takes the average of two values."""
    r.tdigest().create("td", 100)
    r.tdigest().add("td", [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    result = r.tdigest().trimmed_mean("td", 0.4, 0.5)
    assert isinstance(result, float)


def test_tdigest_merge_wrong_numkeys(r: redis.Redis):
    """TDIGEST.MERGE raises an error when numkeys > actual source count."""
    r.tdigest().create("src", 100)
    r.tdigest().add("src", [1.0, 2.0])
    r.tdigest().create("dst", 100)
    with pytest.raises(Exception) as ctx:
        r.execute_command("TDIGEST.MERGE", "dst", "3", "src")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_tdigest_merge_missing_source(r: redis.Redis):
    """TDIGEST.MERGE raises an error when a source key does not exist."""
    r.tdigest().create("src", 100)
    r.tdigest().create("dst", 100)
    with pytest.raises(Exception) as ctx:
        r.tdigest().merge("dst", 2, "src", "nonexistent")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_tdigest_merge_override_into_nonexistent_dest(r: redis.Redis):
    """TDIGEST.MERGE with OVERRIDE creates the destination if it doesn't exist."""
    r.tdigest().create("src", 100)
    r.tdigest().add("src", [1.0, 2.0, 3.0])
    r.tdigest().merge("newdest", 1, "src", override=True)
    assert r.tdigest().min("newdest") == 1.0


def test_tdigest_merge_into_nonexistent_dest(r: redis.Redis):
    """TDIGEST.MERGE into non-existent dest creates the destination automatically."""
    r.tdigest().create("src", 100)
    r.tdigest().add("src", [1.0, 2.0, 3.0])
    r.tdigest().merge("newdest2", 1, "src")
    assert r.tdigest().min("newdest2") == 1.0


def test_tdigest_cdf_boundary_values(r: redis.Redis):
    """TDIGEST.CDF returns 0.0 for values below min and 1.0 for values above max."""
    r.tdigest().create("td", 100)
    r.tdigest().add("td", [5.0, 10.0, 15.0])
    res = r.tdigest().cdf("td", 1.0, 20.0)
    assert res[0] == pytest.approx(0.0)
    assert res[1] == pytest.approx(1.0)
