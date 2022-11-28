import json

import pytest
import redis
from redis.commands.json.path import Path

from test.testtools import raw_command


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
