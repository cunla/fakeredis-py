import time
from datetime import datetime, timedelta

import pytest
import redis
from redis import exceptions

pytest.importorskip("jsonpath_ng")
try:
    from redis.commands.core import DataPersistOptions
except ImportError:
    pytest.skip()

from test.testtools import raw_command

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.min_server("8.4"),
    ]
)


def redis_server_time(client):
    seconds, milliseconds = client.time()
    timestamp = float(f"{seconds}.{milliseconds}")
    return datetime.fromtimestamp(timestamp)


def test_msetex_no_expiration_with_cluster_client(r: redis.Redis):
    all_test_keys = ["1:{test:1}", "2:{test:1}"]
    for key in all_test_keys:
        r.delete(key)

    # set items from mapping without expiration
    assert r.msetex(mapping={"1:{test:1}": 1, "2:{test:1}": b"four"}) == 1
    assert r.mget("1:{test:1}", "2:{test:1}") == [b"1", b"four"]
    assert r.ttl("1:{test:1}") == -1
    assert r.ttl("2:{test:1}") == -1


def test_msetex_expiration_ex_and_keepttl_with_cluster_client(r: redis.Redis):
    all_test_keys = ["1:{test:1}", "2:{test:1}"]
    for key in all_test_keys:
        r.delete(key)

    # set items from mapping with expiration - testing ex field
    assert (
        r.msetex(
            mapping={"1:{test:1}": 1, "2:{test:1}": "2"},
            ex=10,
        )
        == 1
    )
    ttls = [r.ttl(key) for key in all_test_keys]
    for ttl in ttls:
        assert pytest.approx(ttl) == 10

    assert r.mget(*all_test_keys) == [b"1", b"2"]
    time.sleep(1.1)
    # validate keepttl
    assert r.msetex(mapping={"1:{test:1}": 11}, keepttl=True) == 1
    assert r.ttl("1:{test:1}") < 10


def test_msetex_expiration_px_with_cluster_client(r: redis.Redis):
    all_test_keys = ["1:{test:1}", "2:{test:1}"]
    for key in all_test_keys:
        r.delete(key)

    mapping = {"1:{test:1}": 1, "2:{test:1}": "2"}
    # set key/value pairs provided in mapping
    # with expiration - testing px field
    assert r.msetex(mapping=mapping, px=60000) == 1

    ttls = [r.ttl(key) for key in mapping.keys()]
    for ttl in ttls:
        assert pytest.approx(ttl) == 60
    assert r.mget(*mapping.keys()) == [b"1", b"2"]


def test_msetex_expiration_pxat_and_nx_with_cluster_client(r: redis.Redis):
    all_test_keys = [
        "1:{test:1}",
        "2:{test:1}",
        "3:{test:1}",
        "new:{test:1}",
        "new_2:{test:1}",
    ]
    for key in all_test_keys:
        r.delete(key)

    mapping = {"1:{test:1}": 1, "2:{test:1}": "2", "3:{test:1}": "three"}
    assert r.msetex(mapping=mapping, ex=30) == 1

    # NX is set with existing keys - nothing should be saved or updated
    expire_at = redis_server_time(r) + timedelta(seconds=10)
    assert (
        r.msetex(
            mapping={"1:{test:1}": "new_value", "new:{test:1}": "ok"},
            pxat=expire_at,
            data_persist_option=DataPersistOptions.NX,
        )
        == 0
    )

    ttls = [r.ttl(key) for key in mapping.keys()]
    for ttl in ttls:
        assert 10 < ttl <= 30
    assert r.mget(*mapping.keys(), "new:{test:1}") == [b"1", b"2", b"three", None]

    # NX is set with non existing keys - values should be set
    assert (
        r.msetex(
            mapping={"new:{test:1}": "ok", "new_2:{test:1}": "ok_2"},
            pxat=expire_at,
            data_persist_option=DataPersistOptions.NX,
        )
        == 1
    )
    old_ttls = [r.ttl(key) for key in mapping.keys()]
    new_ttls = [r.ttl(key) for key in ["new:{test:1}", "new_2:{test:1}"]]
    for ttl in old_ttls:
        assert 10 < ttl <= 30
    for ttl in new_ttls:
        assert ttl <= 11
    assert r.mget(*mapping.keys(), "new:{test:1}", "new_2:{test:1}") == [
        b"1",
        b"2",
        b"three",
        b"ok",
        b"ok_2",
    ]


def test_msetex_expiration_exat_and_xx_with_cluster_client(r: redis.Redis):
    all_test_keys = ["1:{test:1}", "2:{test:1}", "3:{test:1}", "new:{test:1}"]
    for key in all_test_keys:
        r.delete(key)

    mapping = {"1:{test:1}": 1, "2:{test:1}": "2", "3:{test:1}": "three"}
    assert r.msetex(mapping, ex=30) == 1

    expire_at = redis_server_time(r) + timedelta(seconds=10)
    ## XX is set with unexisting key - nothing should be saved or updated
    assert (
        r.msetex(
            mapping={"1:{test:1}": "new_value", "new:{test:1}": "ok"},
            exat=expire_at,
            data_persist_option=DataPersistOptions.XX,
        )
        == 0
    )
    ttls = [r.ttl(key) for key in mapping.keys()]
    for ttl in ttls:
        assert 10 < ttl <= 30
    assert r.mget(*mapping.keys(), "new:{test:1}") == [b"1", b"2", b"three", None]

    # XX is set with existing keys - values should be updated
    assert (
        r.msetex(
            mapping={"1:{test:1}": "new_value", "2:{test:1}": "new_value_2"},
            exat=expire_at,
            data_persist_option=DataPersistOptions.XX,
        )
        == 1
    )
    ttls = [r.ttl(key) for key in mapping.keys()]
    assert ttls[0] <= 11
    assert ttls[1] <= 11
    assert 10 < ttls[2] <= 30
    assert r.mget("1:{test:1}", "2:{test:1}", "3:{test:1}", "new:{test:1}") == [
        b"new_value",
        b"new_value_2",
        b"three",
        None,
    ]


def test_msetex_no_expiration(r: redis.Redis):
    all_test_keys = ["1", "2"]
    for key in all_test_keys:
        r.delete(key)

    # # set items from mapping without expiration
    assert r.msetex(mapping={"1": 1, "2": b"four"}) == 1
    assert r.mget("1", "2") == [b"1", b"four"]
    assert r.ttl("1") == -1
    assert r.ttl("2") == -1


def test_msetex_expiration_ex_and_keepttl(r: redis.Redis):
    all_test_keys = ["1", "2"]
    for key in all_test_keys:
        r.delete(key)

    # set items from mapping with expiration - testing ex field
    assert (
        r.msetex(
            mapping={"1": 1, "2": "2"},
            ex=10,
        )
        == 1
    )
    ttls = [r.ttl(key) for key in all_test_keys]
    for ttl in ttls:
        assert pytest.approx(ttl) == 10

    assert r.mget(*all_test_keys) == [b"1", b"2"]
    time.sleep(1.1)
    # validate keepttl
    assert r.msetex(mapping={"1": 11}, keepttl=True) == 1
    assert r.ttl("1") < 10


def test_msetex_expiration_px(r: redis.Redis):
    all_test_keys = ["1", "2"]
    for key in all_test_keys:
        r.delete(key)

    mapping = {"1": 1, "2": "2"}
    # set key/value pairs provided in mapping
    # with expiration - testing px field
    assert r.msetex(mapping=mapping, px=60000) == 1

    ttls = [r.ttl(key) for key in mapping.keys()]
    for ttl in ttls:
        assert pytest.approx(ttl) == 60
    assert r.mget(*mapping.keys()) == [b"1", b"2"]


def test_msetex_expiration_pxat_and_nx(r: redis.Redis):
    all_test_keys = ["1", "2", "3", "new", "new_2"]
    for key in all_test_keys:
        r.delete(key)

    mapping = {"1": 1, "2": "2", "3": "three"}
    assert r.msetex(mapping=mapping, ex=30) == 1

    # NX is set with existing keys - nothing should be saved or updated
    expire_at = redis_server_time(r) + timedelta(seconds=20)
    assert (
        r.msetex(
            mapping={"1": "new_value", "new": "ok"},
            pxat=expire_at,
            data_persist_option=DataPersistOptions.NX,
        )
        == 0
    )
    ttls = [r.ttl(key) for key in mapping.keys()]
    for ttl in ttls:
        assert 10 < ttl <= 30
    assert r.mget(*mapping.keys(), "new") == [b"1", b"2", b"three", None]

    # NX is set with non existing keys - values should be set
    assert (
        r.msetex(
            mapping={"new": "ok", "new_2": "ok_2"},
            pxat=expire_at,
            data_persist_option=DataPersistOptions.NX,
        )
        == 1
    )
    old_ttls = [r.ttl(key) for key in mapping.keys()]
    new_ttls = [r.ttl(key) for key in ["new", "new_2"]]
    for ttl in old_ttls:
        assert 10 < ttl <= 30
    for ttl in new_ttls:
        assert ttl <= 21
    assert r.mget(*mapping.keys(), "new", "new_2") == [
        b"1",
        b"2",
        b"three",
        b"ok",
        b"ok_2",
    ]


def test_msetex_expiration_exat_and_xx(r: redis.Redis):
    all_test_keys = ["1", "2", "3", "new"]
    for key in all_test_keys:
        r.delete(key)

    mapping = {"1": 1, "2": "2", "3": "three"}
    assert r.msetex(mapping, ex=30) == 1

    expire_at = redis_server_time(r) + timedelta(seconds=10)
    ## XX is set with unexisting key - nothing should be saved or updated
    assert (
        r.msetex(
            mapping={"1": "new_value", "new": "ok"},
            exat=expire_at,
            data_persist_option=DataPersistOptions.XX,
        )
        == 0
    )
    ttls = [r.ttl(key) for key in mapping.keys()]
    for ttl in ttls:
        assert 10 < ttl <= 30
    assert r.mget(*mapping.keys(), "new") == [b"1", b"2", b"three", None]

    # XX is set with existing keys - values should be updated
    assert (
        r.msetex(
            mapping={"1": "new_value", "2": "new_value_2"},
            exat=expire_at,
            data_persist_option=DataPersistOptions.XX,
        )
        == 1
    )
    ttls = [r.ttl(key) for key in mapping.keys()]
    assert ttls[0] <= 11
    assert ttls[1] <= 11
    assert 10 < ttls[2] <= 30
    assert r.mget("1", "2", "3", "new") == [
        b"new_value",
        b"new_value_2",
        b"three",
        None,
    ]


def test_msetex_invalid_ex_and_keepttl(r: redis.Redis):
    with pytest.raises(exceptions.ResponseError) as excinfo:
        raw_command(r, "MSETEX", 2, "1", 1, "2", 2, "EX", 10, "KEEPTTL")
    assert str(excinfo.value) == "syntax error"


def test_msetex_invalid_ex(r: redis.Redis):
    with pytest.raises(exceptions.ResponseError) as excinfo:
        raw_command(r, "MSETEX", 2, "1", 1, "2", 2, "EX", -1)
    assert str(excinfo.value) == "invalid expire time in 'msetex' command"


def test_msetex_invalid_nx_and_xx(r: redis.Redis):
    with pytest.raises(exceptions.ResponseError) as excinfo:
        raw_command(r, "MSETEX", 2, "1", 1, "2", 2, "EX", 10, "XX", "NX")
    assert str(excinfo.value) == "syntax error"


def test_msetex_invalid_wrong_number_of_keys(r: redis.Redis):
    with pytest.raises(exceptions.ResponseError) as excinfo:
        raw_command(r, "MSETEX", 1, "1", 1, "2", 2, "EX", 10, "XX", "NX")
    assert str(excinfo.value) == "syntax error"


def test_msetex_invalid_negative_number_of_keys(r: redis.Redis):
    with pytest.raises(exceptions.ResponseError) as excinfo:
        raw_command(r, "MSETEX", -1, "1", 1, "2", 2, "EX", 10, "XX", "NX")
    assert str(excinfo.value) == "invalid numkeys value"


def test_msetex_invalid_less_keys(r: redis.Redis):
    with pytest.raises(exceptions.ResponseError) as excinfo:
        raw_command(r, "MSETEX", 5, "1", 1, "2", 2)
    assert str(excinfo.value) == "wrong number of key-value pairs"
