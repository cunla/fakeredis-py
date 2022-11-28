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


