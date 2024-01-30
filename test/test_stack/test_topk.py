import pytest
import redis


def test_topk_incrby(r: redis.Redis):
    assert r.topk().reserve("topk", 3, 10, 3, 1)
    assert [None, None, None] == r.topk().incrby(
        "topk", ["bar", "baz", "42"], [3, 6, 2]
    )
    assert [None, "bar"] == r.topk().incrby("topk", ["42", "xyzzy"], [8, 4])
    with pytest.deprecated_call():
        assert [3, 6, 10, 4, 0] == r.topk().count(
            "topk", "bar", "baz", "42", "xyzzy", 4
        )
