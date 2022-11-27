"""
Tests for `fakeredis-py`'s emulation of Redis's JSON.GET command subset.
"""

from __future__ import annotations

import pytest
import redis
from redis.commands.json.path import Path

json_tests = pytest.importorskip("jsonpath_ng")


def test_jsonget(r: redis.Redis):
    data = {'x': "bar", 'y': {'x': 33}}
    r.json().set("foo", Path.root_path(), data)
    assert r.json().get("foo") == data
    assert r.json().get("foo", Path("$..x")) == ['bar', 33]

    data2 = {'x': "bar"}
    r.json().set("foo2", Path.root_path(), data2, )
    assert r.json().get("foo2") == data2
    assert r.json().get("foo2", Path("$.a"), Path("$.x")) == {'$.a': [], '$.x': ['bar']}

    assert r.json().get("non-existing-key") is None


def test_json_setgetdeleteforget(r: redis.Redis) -> None:
    data = {'x': "bar"}
    assert r.json().set("foo", Path.root_path(), data) == 1
    assert r.json().get("foo") == data
    assert r.json().get("baz") is None
    assert r.json().delete("foo") == 1
    assert r.json().forget("foo") == 0  # second delete
    assert r.exists("foo") == 0


def test_json_set_existential_modifiers_should_succeed(r: redis.Redis) -> None:
    obj = {"foo": "bar"}
    assert r.json().set("obj", Path.root_path(), obj)

    # Test that flags prevent updates when conditions are unmet
    assert r.json().set("obj", Path("foo"), "baz", nx=True, ) is None
    assert r.json().get("obj") == obj

    assert r.json().set("obj", Path("qaz"), "baz", xx=True, ) is None
    assert r.json().get("obj") == obj

    # Test that flags allow updates when conditions are met
    assert r.json().set("obj", Path("foo"), "baz", xx=True) == 1
    assert r.json().set("obj", Path("foo2"), "qaz", nx=True) == 1
    assert r.json().get("obj") == {"foo": "baz", "foo2": "qaz"}

    # Test that flags are mutually exclusive
    with pytest.raises(Exception):
        r.json().set("obj", Path("foo"), "baz", nx=True, xx=True)


def test_json_set_non_dict_value(r: redis.Redis):
    r.json().set("str", Path.root_path(), 'str_val', )
    assert r.json().get('str') == 'str_val'

    r.json().set("bool", Path.root_path(), True)
    assert r.json().get('bool') == True

    r.json().set("bool", Path.root_path(), False)
    assert r.json().get('bool') == False
