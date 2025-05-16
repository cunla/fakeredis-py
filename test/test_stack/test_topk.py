import pytest
import redis

from test.testtools import resp_conversion, get_protocol_version

topk_tests = pytest.importorskip("probables")


@pytest.mark.unsupported_server_types("dragonfly", "valkey")
def test_topk_incrby(r: redis.Redis):
    assert r.topk().reserve("topk", 3, 10, 3, 1)
    assert [None, None, None] == r.topk().incrby("topk", ["bar", "baz", "42"], [3, 6, 4])
    assert resp_conversion(r, [None, b"bar"], [None, "bar"]) == r.topk().incrby("topk", ["42", "xyzzy"], [8, 4])
    with pytest.deprecated_call():
        assert [3, 6, 12, 4, 0] == r.topk().count("topk", "bar", "baz", "42", "xyzzy", 4)


@pytest.mark.min_server("7")
@pytest.mark.unsupported_server_types("dragonfly", "valkey")
def test_topk(r: redis.Redis):
    # test list with empty buckets
    assert r.topk().reserve("topk", 3, 50, 4, 0.9)
    ret = r.topk().add("topk", "A", "B", "C", "D", "D", "E", "A", "A", "B", "C", "G", "D", "B", "D", "A", "E", "E", 1)
    assert len(ret) == 18

    with pytest.deprecated_call():
        assert r.topk().count("topk", "A", "B", "C", "D", "E", "F", "G") == [4, 3, 2, 4, 3, 0, 1]
    ret = r.topk().query("topk", "A", "B", "C", "D", "E", "F", "G")
    assert (ret == [1, 0, 0, 1, 1, 0, 0]) or (ret == [1, 1, 0, 1, 0, 0, 0])
    # test full list
    assert r.topk().reserve("topklist", 3, 50, 3, 0.9)
    assert r.topk().add("topklist", "A", "B", "D", "E", "A", "A", "B", "C", "G", "D", "B", "A", "B", "E", "E")
    with pytest.deprecated_call():
        assert r.topk().count("topklist", "A", "B", "C", "D", "E", "F", "G") == [4, 4, 1, 2, 3, 0, 1]
    assert r.topk().list("topklist") == resp_conversion(r, [b"A", b"B", b"E"], ["A", "B", "E"])
    assert r.topk().list("topklist", withcount=True) == resp_conversion(
        r, [b"A", 4, b"B", 4, b"E", 3], ["A", 4, "B", 4, "E", 3]
    )
    info = r.topk().info("topklist")
    if get_protocol_version(r) == 2:
        assert 3 == info["k"]
        assert 50 == info["width"]
        assert 3 == info["depth"]
        assert 0.9 == round(float(info["decay"]), 1)
    else:
        assert 3 == info[b"k"]
        assert 50 == info[b"width"]
        assert 3 == info[b"depth"]
        assert 0.9 == round(float(info[b"decay"]), 1)
