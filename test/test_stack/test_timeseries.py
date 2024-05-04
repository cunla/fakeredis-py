import math
import time
from time import sleep

import pytest
import redis


def test_create(r: redis.Redis):
    assert r.ts().create(1)
    assert r.ts().create(2, retention_msecs=5)
    assert r.ts().create(3, labels={"Redis": "Labs"})
    assert r.ts().create(4, retention_msecs=20, labels={"Time": "Series"})
    info = r.ts().info(4)
    assert 20 == info.get("retention_msecs")
    assert "Series" == info["labels"]["Time"]

    # Test for a chunk size of 128 Bytes
    assert r.ts().create("time-serie-1", chunk_size=128)
    info = r.ts().info("time-serie-1")
    assert 128 == info.get("chunk_size")


def test_create_duplicate_policy(r: redis.Redis):
    # Test for duplicate policy
    for duplicate_policy in ["block", "last", "first", "min", "max"]:
        ts_name = f"time-serie-ooo-{duplicate_policy}"
        assert r.ts().create(ts_name, duplicate_policy=duplicate_policy)
        info = r.ts().info(ts_name)
        assert duplicate_policy == info.get("duplicate_policy")


def test_alter(r: redis.Redis):
    assert r.ts().create(1)
    info = r.ts().info(1)
    assert 0 == info.get("retention_msecs")
    assert r.ts().alter(1, retention_msecs=10)
    assert {} == r.ts().info(1)["labels"]
    info = r.ts().info(1)
    assert 10 == info.get("retention_msecs")

    assert r.ts().alter(1, labels={"Time": "Series"})
    assert "Series" == r.ts().info(1)["labels"]["Time"]
    info = r.ts().info(1)
    assert 10 == info.get("retention_msecs")


def test_alter_diplicate_policy(r: redis.Redis):
    assert r.ts().create(1)
    info = r.ts().info(1)
    assert info.get("duplicate_policy") is None

    assert r.ts().alter(1, duplicate_policy="min")
    info = r.ts().info(1)
    assert "min" == info.get("duplicate_policy")


def test_add(r: redis.Redis):
    assert 1 == r.ts().add(1, 1, 1)
    assert 2 == r.ts().add(2, 2, 3, retention_msecs=10)
    assert 3 == r.ts().add(3, 3, 2, labels={"Redis": "Labs"})
    assert 4 == r.ts().add(4, 4, 2, retention_msecs=10, labels={"Redis": "Labs", "Time": "Series"})

    assert abs(time.time() - float(r.ts().add(5, "*", 1)) / 1000) < 1.0

    info = r.ts().info(4)
    assert 10 == info.get("retention_msecs")
    assert "Labs" == info["labels"]["Redis"]

    # Test for a chunk size of 128 Bytes on TS.ADD
    assert r.ts().add("time-serie-1", 1, 10.0, chunk_size=128)
    info = r.ts().info("time-serie-1")
    assert 128 == info.get("chunk_size")


def test_add_duplicate_policy(r: redis.Redis):
    # Test for duplicate policy BLOCK
    assert 1 == r.ts().add("time-serie-add-ooo-block", 1, 5.0)
    with pytest.raises(Exception):
        r.ts().add("time-serie-add-ooo-block", 1, 5.0, duplicate_policy="block")

    # Test for duplicate policy LAST
    assert 1 == r.ts().add("time-serie-add-ooo-last", 1, 5.0)
    assert 1 == r.ts().add(
        "time-serie-add-ooo-last", 1, 10.0, duplicate_policy="last"
    )
    assert 10.0 == r.ts().get("time-serie-add-ooo-last")[1]

    # Test for duplicate policy FIRST
    assert 1 == r.ts().add("time-serie-add-ooo-first", 1, 5.0)
    assert 1 == r.ts().add(
        "time-serie-add-ooo-first", 1, 10.0, duplicate_policy="first"
    )
    assert 5.0 == r.ts().get("time-serie-add-ooo-first")[1]

    # Test for duplicate policy MAX
    assert 1 == r.ts().add("time-serie-add-ooo-max", 1, 5.0)
    assert 1 == r.ts().add(
        "time-serie-add-ooo-max", 1, 10.0, duplicate_policy="max"
    )
    assert 10.0 == r.ts().get("time-serie-add-ooo-max")[1]

    # Test for duplicate policy MIN
    assert 1 == r.ts().add("time-serie-add-ooo-min", 1, 5.0)
    assert 1 == r.ts().add(
        "time-serie-add-ooo-min", 1, 10.0, duplicate_policy="min"
    )
    assert 5.0 == r.ts().get("time-serie-add-ooo-min")[1]


def test_madd(r: redis.Redis):
    r.ts().create("a")
    assert [1, 2, 3] == r.ts().madd([("a", 1, 5), ("a", 2, 10), ("a", 3, 15)])


def test_incrby_decrby(r: redis.Redis):
    for _ in range(100):
        assert r.ts().incrby(1, 1)
        sleep(0.001)
    assert 100 == r.ts().get(1)[1]
    for _ in range(100):
        assert r.ts().decrby(1, 1)
        sleep(0.001)
    assert 0 == r.ts().get(1)[1]

    assert r.ts().incrby(2, 1.5, timestamp=5)
    assert r.ts().get(2) == (5, 1.5)
    assert r.ts().incrby(2, 2.25, timestamp=7)
    assert r.ts().get(2) == (7, 3.75)

    assert r.ts().decrby(2, 1.5, timestamp=15)
    assert r.ts().get(2) == (15, 2.25)

    # Test for a chunk size of 128 Bytes on TS.INCRBY
    assert r.ts().incrby("time-serie-1", 10, chunk_size=128)
    info = r.ts().info("time-serie-1")
    assert 128 == info.get("chunk_size")

    # Test for a chunk size of 128 Bytes on TS.DECRBY
    assert r.ts().decrby("time-serie-2", 10, chunk_size=128)
    info = r.ts().info("time-serie-2")
    assert 128 == info.get("chunk_size")


def test_create_and_delete_rule(r: redis.Redis):
    # test rule creation
    time = 100
    r.ts().create(1)
    r.ts().create(2)
    r.ts().createrule(1, 2, "avg", 100)
    for i in range(50):
        r.ts().add(1, time + i * 2, 1)
        r.ts().add(1, time + i * 2 + 1, 2)
    r.ts().add(1, time * 2, 1.5)
    assert round(r.ts().get(2)[1], 5) == 1.5
    info = r.ts().info(1)
    assert info.rules[0][1] == 100

    # test rule deletion
    r.ts().deleterule(1, 2)
    info = r.ts().info(1)
    assert not info["rules"]


def test_del_range(r: redis.Redis):
    try:
        r.ts().delete("test", 0, 100)
    except Exception as e:
        assert e.__str__() != ""

    for i in range(100):
        r.ts().add(1, i, i % 7)
    assert 22 == r.ts().delete(1, 0, 21)
    assert [] == r.ts().range(1, 0, 21)
    assert r.ts().range(1, 22, 22) == [(22, 1.0)]


def test_range(r: redis.Redis):
    for i in range(100):
        r.ts().add(1, i, i % 7)
    assert 100 == len(r.ts().range(1, 0, 200))
    for i in range(100):
        r.ts().add(1, i + 200, i % 7)
    assert 200 == len(r.ts().range(1, 0, 500))
    # last sample isn't returned
    assert 20 == len(
        r.ts().range(1, 0, 500, aggregation_type="avg", bucket_size_msec=10)
    )
    assert 10 == len(r.ts().range(1, 0, 500, count=10))


def test_range_advanced(r: redis.Redis):
    for i in range(100):
        r.ts().add(1, i, i % 7)
        r.ts().add(1, i + 200, i % 7)

    assert 2 == len(
        r.ts().range(
            1,
            0,
            500,
            filter_by_ts=[i for i in range(10, 20)],
            filter_by_min_value=1,
            filter_by_max_value=2,
        )
    )
    res = r.ts().range(
        1, 0, 10, aggregation_type="count", bucket_size_msec=10, align="+"
    )
    assert res == [(0, 10.0), (10, 1.0)]

    res = r.ts().range(
        1, 0, 10, aggregation_type="count", bucket_size_msec=10, align=5
    )
    assert res == [(0, 5.0), (5, 6.0)]

    res = r.ts().range(1, 0, 10, aggregation_type="twa", bucket_size_msec=10)
    assert res == [(0, 2.55), (10, 3.0)]


def test_range_latest(r: redis.Redis):
    timeseries = r.ts()
    timeseries.create("t1")
    timeseries.create("t2")
    timeseries.createrule("t1", "t2", aggregation_type="sum", bucket_size_msec=10)
    timeseries.add("t1", 1, 1)
    timeseries.add("t1", 2, 3)
    timeseries.add("t1", 11, 7)
    timeseries.add("t1", 13, 1)
    assert timeseries.range("t1", 0, 20) == [(1, 1.0), (2, 3.0), (11, 7.0), (13, 1.0)]
    assert timeseries.range("t2", 0, 10) == [(0, 4.0)]

    res = timeseries.range("t2", 0, 10, latest=True)
    assert res == [(0, 4.0)]
    assert timeseries.range("t2", 0, 9) == [(0, 4.0)]


def test_range_bucket_timestamp(r: redis.Redis):
    timeseries = r.ts()
    timeseries.create("t1")
    timeseries.add("t1", 15, 1)
    timeseries.add("t1", 17, 4)
    timeseries.add("t1", 51, 3)
    timeseries.add("t1", 73, 5)
    timeseries.add("t1", 75, 3)
    assert timeseries.range(
        "t1", 0, 100, align=0, aggregation_type="max", bucket_size_msec=10
    ) == [(10, 4.0), (50, 3.0), (70, 5.0)]
    assert timeseries.range(
        "t1",
        0,
        100,
        align=0,
        aggregation_type="max",
        bucket_size_msec=10,
        bucket_timestamp="+",
    ) == [(20, 4.0), (60, 3.0), (80, 5.0)]


def test_range_empty(r: redis.Redis):
    timeseries = r.ts()
    timeseries.create("t1")
    timeseries.add("t1", 15, 1)
    timeseries.add("t1", 17, 4)
    timeseries.add("t1", 51, 3)
    timeseries.add("t1", 73, 5)
    timeseries.add("t1", 75, 3)
    assert timeseries.range(
        "t1", 0, 100, align=0, aggregation_type="max", bucket_size_msec=10
    ) == [(10, 4.0), (50, 3.0), (70, 5.0)]

    res = timeseries.range(
        "t1", 0, 100, align=0, aggregation_type="max", bucket_size_msec=10, empty=True
    )
    for i in range(len(res)):
        if math.isnan(res[i][1]):
            res[i] = (res[i][0], None)
    resp2_expected = [
        (10, 4.0),
        (20, None),
        (30, None),
        (40, None),
        (50, 3.0),
        (60, None),
        (70, 5.0),
    ]
    resp3_expected = [
        [10, 4.0],
        (20, None),
        (30, None),
        (40, None),
        [50, 3.0],
        (60, None),
        [70, 5.0],
    ]
    assert res == resp2_expected


def test_rev_range(r: redis.Redis):
    for i in range(100):
        r.ts().add(1, i, i % 7)
    assert 100 == len(r.ts().range(1, 0, 200))
    for i in range(100):
        r.ts().add(1, i + 200, i % 7)
    assert 200 == len(r.ts().range(1, 0, 500))
    # first sample isn't returned
    assert 20 == len(
        r.ts().revrange(1, 0, 500, aggregation_type="avg", bucket_size_msec=10)
    )
    assert 10 == len(r.ts().revrange(1, 0, 500, count=10))
    assert 2 == len(
        r.ts().revrange(
            1,
            0,
            500,
            filter_by_ts=[i for i in range(10, 20)],
            filter_by_min_value=1,
            filter_by_max_value=2,
        )
    )
    assert r.ts().revrange(
        1, 0, 10, aggregation_type="count", bucket_size_msec=10, align="+"
    ) == [(10, 1.0), (0, 10.0)]

    assert r.ts().revrange(
        1, 0, 10, aggregation_type="count", bucket_size_msec=10, align=1
    ) == [(1, 10.0), (0, 1.0)]
    assert r.ts().revrange(1, 0, 10, aggregation_type="twa", bucket_size_msec=10) == [(10, 3.0), (0, 2.55)]


@pytest.mark.onlynoncluster
def test_revrange_latest(r: redis.Redis):
    timeseries = r.ts()
    timeseries.create("t1")
    timeseries.create("t2")
    timeseries.createrule("t1", "t2", aggregation_type="sum", bucket_size_msec=10)
    timeseries.add("t1", 1, 1)
    timeseries.add("t1", 2, 3)
    timeseries.add("t1", 11, 7)
    timeseries.add("t1", 13, 1)

    assert timeseries.revrange("t2", 0, 10) == [(0, 4.0)]
    assert timeseries.revrange("t2", 0, 10, latest=True) == [(0, 4.0)]
    assert timeseries.revrange("t2", 0, 9, latest=True) == [(0, 4.0)]


def test_revrange_bucket_timestamp(r: redis.Redis):
    timeseries = r.ts()
    timeseries.create("t1")
    timeseries.add("t1", 15, 1)
    timeseries.add("t1", 17, 4)
    timeseries.add("t1", 51, 3)
    timeseries.add("t1", 73, 5)
    timeseries.add("t1", 75, 3)
    assert timeseries.revrange(
        "t1", 0, 100, align=0, aggregation_type="max", bucket_size_msec=10
    ) == [(70, 5.0), (50, 3.0), (10, 4.0)]
    assert timeseries.range(
        "t1",
        0,
        100,
        align=0,
        aggregation_type="max",
        bucket_size_msec=10,
        bucket_timestamp="+",
    ) == [(20, 4.0), (60, 3.0), (80, 5.0)]


def test_revrange_empty(r: redis.Redis):
    timeseries = r.ts()
    timeseries.create("t1")
    timeseries.add("t1", 15, 1)
    timeseries.add("t1", 17, 4)
    timeseries.add("t1", 51, 3)
    timeseries.add("t1", 73, 5)
    timeseries.add("t1", 75, 3)
    assert timeseries.revrange(
            "t1", 0, 100, align=0, aggregation_type="max", bucket_size_msec=10
        ) ==  [(70, 5.0), (50, 3.0), (10, 4.0)]
    res = timeseries.revrange(
        "t1", 0, 100, align=0, aggregation_type="max", bucket_size_msec=10, empty=True
    )
    for i in range(len(res)):
        if math.isnan(res[i][1]):
            res[i] = (res[i][0], None)
    assert res == [
        (70, 5.0),
        (60, None),
        (50, 3.0),
        (40, None),
        (30, None),
        (20, None),
        (10, 4.0),
    ]


# @pytest.mark.onlynoncluster
# def test_mrange(r: redis.Redis):
#     r.ts().create(1, labels={"Test": "This", "team": "ny"})
#     r.ts().create(2, labels={"Test": "This", "Taste": "That", "team": "sf"})
#     for i in range(100):
#         r.ts().add(1, i, i % 7)
#         r.ts().add(2, i, i % 11)
#
#     res = r.ts().mrange(0, 200, filters=["Test=This"])
#     assert 2 == len(res)
#     if is_resp2_connection(r):
#         assert 100 == len(res[0]["1"][1])
#
#         res = r.ts().mrange(0, 200, filters=["Test=This"], count=10)
#         assert 10 == len(res[0]["1"][1])
#
#         for i in range(100):
#             r.ts().add(1, i + 200, i % 7)
#         res = r.ts().mrange(
#             0, 500, filters=["Test=This"], aggregation_type="avg", bucket_size_msec=10
#         )
#         assert 2 == len(res)
#         assert 20 == len(res[0]["1"][1])
#
#         # test withlabels
#         assert {} == res[0]["1"][0]
#         res = r.ts().mrange(0, 200, filters=["Test=This"], with_labels=True)
#         assert {"Test": "This", "team": "ny"} == res[0]["1"][0]
#     else:
#         assert 100 == len(res["1"][2])
#
#         res = r.ts().mrange(0, 200, filters=["Test=This"], count=10)
#         assert 10 == len(res["1"][2])
#
#         for i in range(100):
#             r.ts().add(1, i + 200, i % 7)
#         res = r.ts().mrange(
#             0, 500, filters=["Test=This"], aggregation_type="avg", bucket_size_msec=10
#         )
#         assert 2 == len(res)
#         assert 20 == len(res["1"][2])
#
#         # test withlabels
#         assert {} == res["1"][0]
#         res = r.ts().mrange(0, 200, filters=["Test=This"], with_labels=True)
#         assert {"Test": "This", "team": "ny"} == res["1"][0]
#
#
# @pytest.mark.onlynoncluster
# def test_multi_range_advanced(r: redis.Redis):
#     r.ts().create(1, labels={"Test": "This", "team": "ny"})
#     r.ts().create(2, labels={"Test": "This", "Taste": "That", "team": "sf"})
#     for i in range(100):
#         r.ts().add(1, i, i % 7)
#         r.ts().add(2, i, i % 11)
#
#     # test with selected labels
#     res = r.ts().mrange(0, 200, filters=["Test=This"], select_labels=["team"])
#     if is_resp2_connection(r):
#         assert {"team": "ny"} == res[0]["1"][0]
#         assert {"team": "sf"} == res[1]["2"][0]
#
#         # test with filterby
#         res = r.ts().mrange(
#             0,
#             200,
#             filters=["Test=This"],
#             filter_by_ts=[i for i in range(10, 20)],
#             filter_by_min_value=1,
#             filter_by_max_value=2,
#         )
#         assert [(15, 1.0), (16, 2.0)] == res[0]["1"][1]
#
#         # test groupby
#         res = r.ts().mrange(
#             0, 3, filters=["Test=This"], groupby="Test", reduce="sum"
#         )
#         assert [(0, 0.0), (1, 2.0), (2, 4.0), (3, 6.0)] == res[0]["Test=This"][1]
#         res = r.ts().mrange(
#             0, 3, filters=["Test=This"], groupby="Test", reduce="max"
#         )
#         assert [(0, 0.0), (1, 1.0), (2, 2.0), (3, 3.0)] == res[0]["Test=This"][1]
#         res = r.ts().mrange(
#             0, 3, filters=["Test=This"], groupby="team", reduce="min"
#         )
#         assert 2 == len(res)
#         assert [(0, 0.0), (1, 1.0), (2, 2.0), (3, 3.0)] == res[0]["team=ny"][1]
#         assert [(0, 0.0), (1, 1.0), (2, 2.0), (3, 3.0)] == res[1]["team=sf"][1]
#
#         # test align
#         res = r.ts().mrange(
#             0,
#             10,
#             filters=["team=ny"],
#             aggregation_type="count",
#             bucket_size_msec=10,
#             align="-",
#         )
#         assert [(0, 10.0), (10, 1.0)] == res[0]["1"][1]
#         res = r.ts().mrange(
#             0,
#             10,
#             filters=["team=ny"],
#             aggregation_type="count",
#             bucket_size_msec=10,
#             align=5,
#         )
#         assert [(0, 5.0), (5, 6.0)] == res[0]["1"][1]
#
#     else:
#         assert {"team": "ny"} == res["1"][0]
#     assert {"team": "sf"} == res["2"][0]
#
#     # test with filterby
#     res = r.ts().mrange(
#         0,
#         200,
#         filters=["Test=This"],
#         filter_by_ts=[i for i in range(10, 20)],
#         filter_by_min_value=1,
#         filter_by_max_value=2,
#     )
#     assert [[15, 1.0], [16, 2.0]] == res["1"][2]
#
#     # test groupby
#     res = r.ts().mrange(
#         0, 3, filters=["Test=This"], groupby="Test", reduce="sum"
#     )
#     assert [[0, 0.0], [1, 2.0], [2, 4.0], [3, 6.0]] == res["Test=This"][3]
#     res = r.ts().mrange(
#         0, 3, filters=["Test=This"], groupby="Test", reduce="max"
#     )
#     assert [[0, 0.0], [1, 1.0], [2, 2.0], [3, 3.0]] == res["Test=This"][3]
#     res = r.ts().mrange(
#         0, 3, filters=["Test=This"], groupby="team", reduce="min"
#     )
#     assert 2 == len(res)
#     assert [[0, 0.0], [1, 1.0], [2, 2.0], [3, 3.0]] == res["team=ny"][3]
#     assert [[0, 0.0], [1, 1.0], [2, 2.0], [3, 3.0]] == res["team=sf"][3]
#
#     # test align
#     res = r.ts().mrange(
#         0,
#         10,
#         filters=["team=ny"],
#         aggregation_type="count",
#         bucket_size_msec=10,
#         align="-",
#     )
#     assert [[0, 10.0], [10, 1.0]] == res["1"][2]
#     res = r.ts().mrange(
#         0,
#         10,
#         filters=["team=ny"],
#         aggregation_type="count",
#         bucket_size_msec=10,
#         align=5,
#     )
#     assert [[0, 5.0], [5, 6.0]] == res["1"][2]
#
#
# @pytest.mark.onlynoncluster
# def test_mrange_latest(r: redis.Redis):
#     timeseries = r.ts()
#     timeseries.create("t1")
#     timeseries.create("t2", labels={"is_compaction": "true"})
#     timeseries.create("t3")
#     timeseries.create("t4", labels={"is_compaction": "true"})
#     timeseries.createrule("t1", "t2", aggregation_type="sum", bucket_size_msec=10)
#     timeseries.createrule("t3", "t4", aggregation_type="sum", bucket_size_msec=10)
#     timeseries.add("t1", 1, 1)
#     timeseries.add("t1", 2, 3)
#     timeseries.add("t1", 11, 7)
#     timeseries.add("t1", 13, 1)
#     timeseries.add("t3", 1, 1)
#     timeseries.add("t3", 2, 3)
#     timeseries.add("t3", 11, 7)
#     timeseries.add("t3", 13, 1)
#     assert_resp_response(
#         r,
#         r.ts().mrange(0, 10, filters=["is_compaction=true"], latest=True),
#         [{"t2": [{}, [(0, 4.0), (10, 8.0)]]}, {"t4": [{}, [(0, 4.0), (10, 8.0)]]}],
#         {
#             "t2": [{}, {"aggregators": []}, [[0, 4.0], [10, 8.0]]],
#             "t4": [{}, {"aggregators": []}, [[0, 4.0], [10, 8.0]]],
#         },
#     )
#
#
# @pytest.mark.onlynoncluster
# @skip_ifmodversion_lt("99.99.99", "timeseries")
# def test_multi_reverse_range(r: redis.Redis):
#     r.ts().create(1, labels={"Test": "This", "team": "ny"})
#     r.ts().create(2, labels={"Test": "This", "Taste": "That", "team": "sf"})
#     for i in range(100):
#         r.ts().add(1, i, i % 7)
#         r.ts().add(2, i, i % 11)
#
#     res = r.ts().mrange(0, 200, filters=["Test=This"])
#     assert 2 == len(res)
#     if is_resp2_connection(r):
#         assert 100 == len(res[0]["1"][1])
#
#     else:
#         assert 100 == len(res["1"][2])
#
#     res = r.ts().mrange(0, 200, filters=["Test=This"], count=10)
#     if is_resp2_connection(r):
#         assert 10 == len(res[0]["1"][1])
#     else:
#         assert 10 == len(res["1"][2])
#
#     for i in range(100):
#         r.ts().add(1, i + 200, i % 7)
#     res = r.ts().mrevrange(
#         0, 500, filters=["Test=This"], aggregation_type="avg", bucket_size_msec=10
#     )
#     assert 2 == len(res)
#     if is_resp2_connection(r):
#         assert 20 == len(res[0]["1"][1])
#         assert {} == res[0]["1"][0]
#     else:
#         assert 20 == len(res["1"][2])
#         assert {} == res["1"][0]
#
#     # test withlabels
#     res = r.ts().mrevrange(0, 200, filters=["Test=This"], with_labels=True)
#     if is_resp2_connection(r):
#         assert {"Test": "This", "team": "ny"} == res[0]["1"][0]
#     else:
#         assert {"Test": "This", "team": "ny"} == res["1"][0]
#
#     # test with selected labels
#     res = r.ts().mrevrange(0, 200, filters=["Test=This"], select_labels=["team"])
#     if is_resp2_connection(r):
#         assert {"team": "ny"} == res[0]["1"][0]
#         assert {"team": "sf"} == res[1]["2"][0]
#     else:
#         assert {"team": "ny"} == res["1"][0]
#         assert {"team": "sf"} == res["2"][0]
#
#     # test filterby
#     res = r.ts().mrevrange(
#         0,
#         200,
#         filters=["Test=This"],
#         filter_by_ts=[i for i in range(10, 20)],
#         filter_by_min_value=1,
#         filter_by_max_value=2,
#     )
#     if is_resp2_connection(r):
#         assert [(16, 2.0), (15, 1.0)] == res[0]["1"][1]
#     else:
#         assert [[16, 2.0], [15, 1.0]] == res["1"][2]
#
#     # test groupby
#     res = r.ts().mrevrange(
#         0, 3, filters=["Test=This"], groupby="Test", reduce="sum"
#     )
#     if is_resp2_connection(r):
#         assert [(3, 6.0), (2, 4.0), (1, 2.0), (0, 0.0)] == res[0]["Test=This"][1]
#     else:
#         assert [[3, 6.0], [2, 4.0], [1, 2.0], [0, 0.0]] == res["Test=This"][3]
#     res = r.ts().mrevrange(
#         0, 3, filters=["Test=This"], groupby="Test", reduce="max"
#     )
#     if is_resp2_connection(r):
#         assert [(3, 3.0), (2, 2.0), (1, 1.0), (0, 0.0)] == res[0]["Test=This"][1]
#     else:
#         assert [[3, 3.0], [2, 2.0], [1, 1.0], [0, 0.0]] == res["Test=This"][3]
#     res = r.ts().mrevrange(
#         0, 3, filters=["Test=This"], groupby="team", reduce="min"
#     )
#     assert 2 == len(res)
#     if is_resp2_connection(r):
#         assert [(3, 3.0), (2, 2.0), (1, 1.0), (0, 0.0)] == res[0]["team=ny"][1]
#         assert [(3, 3.0), (2, 2.0), (1, 1.0), (0, 0.0)] == res[1]["team=sf"][1]
#     else:
#         assert [[3, 3.0], [2, 2.0], [1, 1.0], [0, 0.0]] == res["team=ny"][3]
#         assert [[3, 3.0], [2, 2.0], [1, 1.0], [0, 0.0]] == res["team=sf"][3]
#
#     # test align
#     res = r.ts().mrevrange(
#         0,
#         10,
#         filters=["team=ny"],
#         aggregation_type="count",
#         bucket_size_msec=10,
#         align="-",
#     )
#     if is_resp2_connection(r):
#         assert [(10, 1.0), (0, 10.0)] == res[0]["1"][1]
#     else:
#         assert [[10, 1.0], [0, 10.0]] == res["1"][2]
#     res = r.ts().mrevrange(
#         0,
#         10,
#         filters=["team=ny"],
#         aggregation_type="count",
#         bucket_size_msec=10,
#         align=1,
#     )
#     if is_resp2_connection(r):
#         assert [(1, 10.0), (0, 1.0)] == res[0]["1"][1]
#     else:
#         assert [[1, 10.0], [0, 1.0]] == res["1"][2]
#
#
# @pytest.mark.onlynoncluster
# def test_mrevrange_latest(r: redis.Redis):
#     timeseries = r.ts()
#     timeseries.create("t1")
#     timeseries.create("t2", labels={"is_compaction": "true"})
#     timeseries.create("t3")
#     timeseries.create("t4", labels={"is_compaction": "true"})
#     timeseries.createrule("t1", "t2", aggregation_type="sum", bucket_size_msec=10)
#     timeseries.createrule("t3", "t4", aggregation_type="sum", bucket_size_msec=10)
#     timeseries.add("t1", 1, 1)
#     timeseries.add("t1", 2, 3)
#     timeseries.add("t1", 11, 7)
#     timeseries.add("t1", 13, 1)
#     timeseries.add("t3", 1, 1)
#     timeseries.add("t3", 2, 3)
#     timeseries.add("t3", 11, 7)
#     timeseries.add("t3", 13, 1)
#     assert_resp_response(
#         r,
#         r.ts().mrevrange(0, 10, filters=["is_compaction=true"], latest=True),
#         [{"t2": [{}, [(10, 8.0), (0, 4.0)]]}, {"t4": [{}, [(10, 8.0), (0, 4.0)]]}],
#         {
#             "t2": [{}, {"aggregators": []}, [[10, 8.0], [0, 4.0]]],
#             "t4": [{}, {"aggregators": []}, [[10, 8.0], [0, 4.0]]],
#         },
#     )
#
#
# def test_get(r: redis.Redis):
#     name = "test"
#     r.ts().create(name)
#     assert not r.ts().get(name)
#     r.ts().add(name, 2, 3)
#     assert 2 == r.ts().get(name)[0]
#     r.ts().add(name, 3, 4)
#     assert 4 == r.ts().get(name)[1]
#
#
# @pytest.mark.onlynoncluster
# @skip_ifmodversion_lt("1.8.0", "timeseries")
# def test_get_latest(r: redis.Redis):
#     timeseries = r.ts()
#     timeseries.create("t1")
#     timeseries.create("t2")
#     timeseries.createrule("t1", "t2", aggregation_type="sum", bucket_size_msec=10)
#     timeseries.add("t1", 1, 1)
#     timeseries.add("t1", 2, 3)
#     timeseries.add("t1", 11, 7)
#     timeseries.add("t1", 13, 1)
#     assert_resp_response(r, timeseries.get("t2"), (0, 4.0), [0, 4.0])
#     assert_resp_response(
#         r, timeseries.get("t2", latest=True), (10, 8.0), [10, 8.0]
#     )
#
#
# @pytest.mark.onlynoncluster
# def test_mget(r: redis.Redis):
#     r.ts().create(1, labels={"Test": "This"})
#     r.ts().create(2, labels={"Test": "This", "Taste": "That"})
#     act_res = r.ts().mget(["Test=This"])
#     exp_res = [{"1": [{}, None, None]}, {"2": [{}, None, None]}]
#     exp_res_resp3 = {"1": [{}, []], "2": [{}, []]}
#     assert_resp_response(r, act_res, exp_res, exp_res_resp3)
#     r.ts().add(1, "*", 15)
#     r.ts().add(2, "*", 25)
#     res = r.ts().mget(["Test=This"])
#     if is_resp2_connection(r):
#         assert 15 == res[0]["1"][2]
#         assert 25 == res[1]["2"][2]
#
#     else:
#         assert 15 == res["1"][1][1]
#         assert 25 == res["2"][1][1]
#     res = r.ts().mget(["Taste=That"])
#     if is_resp2_connection(r):
#         assert 25 == res[0]["2"][2]
#     else:
#         assert 25 == res["2"][1][1]
#
#     # test with_labels
#     if is_resp2_connection(r):
#         assert {} == res[0]["2"][0]
#     else:
#         assert {} == res["2"][0]
#     res = r.ts().mget(["Taste=That"], with_labels=True)
#     if is_resp2_connection(r):
#         assert {"Taste": "That", "Test": "This"} == res[0]["2"][0]
#     else:
#         assert {"Taste": "That", "Test": "This"} == res["2"][0]
#
#
# @pytest.mark.onlynoncluster
# def test_mget_latest(r: redis.Redis):
#     timeseries = r.ts()
#     timeseries.create("t1")
#     timeseries.create("t2", labels={"is_compaction": "true"})
#     timeseries.createrule("t1", "t2", aggregation_type="sum", bucket_size_msec=10)
#     timeseries.add("t1", 1, 1)
#     timeseries.add("t1", 2, 3)
#     timeseries.add("t1", 11, 7)
#     timeseries.add("t1", 13, 1)
#     res = timeseries.mget(filters=["is_compaction=true"])
#     assert_resp_response(r, res, [{"t2": [{}, 0, 4.0]}], {"t2": [{}, [0, 4.0]]})
#     res = timeseries.mget(filters=["is_compaction=true"], latest=True)
#     assert_resp_response(r, res, [{"t2": [{}, 10, 8.0]}], {"t2": [{}, [10, 8.0]]})
#
#
# def test_info(r: redis.Redis):
#     r.ts().create(1, retention_msecs=5, labels={"currentLabel": "currentData"})
#     info = r.ts().info(1)
#     assert_resp_response(
#         r, 5, info.get("retention_msecs"), info.get("retentionTime")
#     )
#     assert info["labels"]["currentLabel"] == "currentData"
#
#
# @skip_ifmodversion_lt("1.4.0", "timeseries")
# def testInfoDuplicatePolicy(r: redis.Redis):
#     r.ts().create(1, retention_msecs=5, labels={"currentLabel": "currentData"})
#     info = r.ts().info(1)
#     assert_resp_response(
#         r, None, info.get("duplicate_policy"), info.get("duplicatePolicy")
#     )
#
#     r.ts().create("time-serie-2", duplicate_policy="min")
#     info = r.ts().info("time-serie-2")
#     assert_resp_response(
#         r, "min", info.get("duplicate_policy"), info.get("duplicatePolicy")
#     )
#
#
# @pytest.mark.onlynoncluster
# def test_query_index(r: redis.Redis):
#     r.ts().create(1, labels={"Test": "This"})
#     r.ts().create(2, labels={"Test": "This", "Taste": "That"})
#     assert 2 == len(r.ts().queryindex(["Test=This"]))
#     assert 1 == len(r.ts().queryindex(["Taste=That"]))
#     assert_resp_response(r, r.ts().queryindex(["Taste=That"]), [2], {"2"})
#
#
# def test_pipeline(r: redis.Redis):
#     pipeline = r.ts().pipeline()
#     pipeline.create("with_pipeline")
#     for i in range(100):
#         pipeline.add("with_pipeline", i, 1.1 * i)
#     pipeline.execute()
#
#     info = r.ts().info("with_pipeline")
#
#     assert_resp_response(
#         r, 99, info.get("last_timestamp"), info.get("lastTimestamp")
#     )
#     assert_resp_response(
#         r, 100, info.get("total_samples"), info.get("totalSamples")
#     )
#     assert r.ts().get("with_pipeline")[1] == 99 * 1.1
#
#
# def test_uncompressed(r: redis.Redis):
#     r.ts().create("compressed")
#     r.ts().create("uncompressed", uncompressed=True)
#     compressed_info = r.ts().info("compressed")
#     uncompressed_info = r.ts().info("uncompressed")
#
#     assert compressed_info["memoryUsage"] != uncompressed_info["memoryUsage"]