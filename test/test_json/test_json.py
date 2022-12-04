"""
Tests for `fakeredis-py`'s emulation of Redis's JSON.GET command subset.
"""

from __future__ import annotations

import json

import pytest
import redis
from redis.commands.json.path import Path

from test.testtools import raw_command

json_tests = pytest.importorskip("jsonpath_ng")


def test_jsonget(r: redis.Redis):
    data = {'x': "bar", 'y': {'x': 33}}
    r.json().set("foo", Path.root_path(), data)
    assert r.json().get("foo") == data
    assert r.json().get("foo", Path("$..x")) == ['bar', 33]

    data2 = {'x': "bar"}
    r.json().set("foo2", Path.root_path(), data2, )
    assert r.json().get("foo2") == data2
    assert r.json().get("foo2", "$") == [data2, ]
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


def test_json_set_non_dict_value(r: redis.Redis):
    r.json().set("str", Path.root_path(), 'str_val', )
    assert r.json().get('str') == 'str_val'

    r.json().set("bool", Path.root_path(), True)
    assert r.json().get('bool') == True

    r.json().set("bool", Path.root_path(), False)
    assert r.json().get('bool') == False


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

    # Test with raw
    obj = {"foo": "bar"}
    raw_command(r, 'json.set', 'obj', '$', json.dumps(obj))
    assert r.json().get('obj') == obj


def test_json_set_flags_should_be_mutually_exclusive(r: redis.Redis):
    with pytest.raises(Exception):
        r.json().set("obj", Path("foo"), "baz", nx=True, xx=True)
    with pytest.raises(redis.ResponseError):
        raw_command(r, 'json.set', 'obj', '$', json.dumps({"foo": "bar"}), 'NX', 'XX')


def test_json_unknown_param(r: redis.Redis):
    with pytest.raises(redis.ResponseError):
        raw_command(r, 'json.set', 'obj', '$', json.dumps({"foo": "bar"}), 'unknown')


def test_mget(r: redis.Redis):
    # Test mget with multi paths
    r.json().set("doc1", "$", {"a": 1, "b": 2, "nested": {"a": 3}, "c": None, "nested2": {"a": None}})
    r.json().set("doc2", "$", {"a": 4, "b": 5, "nested": {"a": 6}, "c": None, "nested2": {"a": [None]}})
    # Compare also to single JSON.GET
    assert r.json().get("doc1", Path("$..a")) == [1, 3, None]
    assert r.json().get("doc2", "$..a") == [4, 6, [None]]

    # Test mget with single path
    assert r.json().mget(["doc1"], "$..a") == [[1, 3, None]]

    # Test mget with multi path
    assert r.json().mget(["doc1", "doc2"], "$..a") == [[1, 3, None], [4, 6, [None]]]

    # Test missing key
    assert r.json().mget(["doc1", "missing_doc"], "$..a") == [[1, 3, None], None]

    assert r.json().mget(["missing_doc1", "missing_doc2"], "$..a") == [None, None]


def test_mget_should_succeed(r: redis.Redis) -> None:
    r.json().set("1", Path.root_path(), 1)
    r.json().set("2", Path.root_path(), 2)

    assert r.json().mget(["1"], Path.root_path()) == [1]

    assert r.json().mget([1, 2], Path.root_path()) == [1, 2]


def test_clear(r: redis.Redis) -> None:
    r.json().set("arr", Path.root_path(), [0, 1, 2, 3, 4], )

    assert 1 == r.json().clear("arr", Path.root_path(), )
    assert [] == r.json().get("arr")


def test_clear_dollar(r: redis.Redis) -> None:
    data = {
        "nested1": {"a": {"foo": 10, "bar": 20}},
        "a": ["foo"],
        "nested2": {"a": "claro"},
        "nested3": {"a": {"baz": 50}}
    }
    r.json().set("doc1", "$", data)
    # Test multi
    assert r.json().clear("doc1", "$..a") == 3

    assert r.json().get("doc1", "$") == [
        {"nested1": {"a": {}}, "a": [], "nested2": {"a": "claro"}, "nested3": {"a": {}}}
    ]

    # Test single
    r.json().set("doc1", "$", data)
    assert r.json().clear("doc1", "$.nested1.a") == 1
    assert r.json().get("doc1", "$") == [
        {
            "nested1": {"a": {}},
            "a": ["foo"],
            "nested2": {"a": "claro"},
            "nested3": {"a": {"baz": 50}},
        }
    ]

    # Test missing path (defaults to root)
    assert r.json().clear("doc1") == 1
    assert r.json().get("doc1", "$") == [{}]


def test_clear_no_doc(r: redis.Redis) -> None:
    # Test missing key
    with pytest.raises(redis.ResponseError):
        r.json().clear("non_existing_doc", "$..a")
