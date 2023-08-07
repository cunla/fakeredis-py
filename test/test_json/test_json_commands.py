"""Tests for `fakeredis-py`'s emulation of Redis's JSON command subset."""

from __future__ import annotations

from typing import (Any, Dict, List, Tuple, )

import pytest
import redis
from redis.commands.json.path import Path

json_tests = pytest.importorskip("jsonpath_ng")

SAMPLE_DATA = {
    "a": ["foo"],
    "nested1": {"a": ["hello", None, "world"]},
    "nested2": {"a": 31},
}


@pytest.fixture(scope="function")
def json_data() -> Dict[str, Any]:
    """A module-scoped "blob" of JSON-encodable data."""
    return {
        "L1": {
            "a": {
                "A1_B1": 10,
                "A1_B2": False,
                "A1_B3": {
                    "A1_B3_C1": None,
                    "A1_B3_C2": [
                        "A1_B3_C2_D1_1",
                        "A1_B3_C2_D1_2",
                        -19.5,
                        "A1_B3_C2_D1_4",
                        "A1_B3_C2_D1_5",
                        {"A1_B3_C2_D1_6_E1": True},
                    ],
                    "A1_B3_C3": [1],
                },
                "A1_B4": {"A1_B4_C1": "foo"},
            }
        },
        "L2": {
            "a": {
                "A2_B1": 20,
                "A2_B2": False,
                "A2_B3": {
                    "A2_B3_C1": None,
                    "A2_B3_C2": [
                        "A2_B3_C2_D1_1",
                        "A2_B3_C2_D1_2",
                        -37.5,
                        "A2_B3_C2_D1_4",
                        "A2_B3_C2_D1_5",
                        {"A2_B3_C2_D1_6_E1": False},
                    ],
                    "A2_B3_C3": [2],
                },
                "A2_B4": {"A2_B4_C1": "bar"},
            }
        },
    }


@pytest.mark.xfail
def test_debug(r: redis.Redis):
    r.json().set("str", Path.root_path(), "foo")
    assert 24 == r.json().debug("MEMORY", "str", Path.root_path())
    assert 24 == r.json().debug("MEMORY", "str")

    # technically help is valid
    assert isinstance(r.json().debug("HELP"), list)


@pytest.mark.xfail
def test_resp(r: redis.Redis):
    obj = {"foo": "bar", "baz": 1, "qaz": True, }
    r.json().set("obj", Path.root_path(), obj, )

    assert "bar" == r.json().resp("obj", Path("foo"), )
    assert 1 == r.json().resp("obj", Path("baz"), )
    assert r.json().resp(
        "obj",
        Path("qaz"),
    )
    assert isinstance(r.json().resp("obj"), list)


def load_types_data(nested_key_name: str) -> Tuple[Dict[str, Any], List[bytes]]:
    """Generate a structure with sample of all types
    """
    type_samples = {
        "object": {},
        "array": [],
        "string": "str",
        "integer": 42,
        "number": 1.2,
        "boolean": False,
        "null": None,
    }
    jdata = {}

    for (k, v) in type_samples.items():
        jdata[f"nested_{k}"] = {nested_key_name: v}

    return jdata, [k.encode() for k in type_samples.keys()]


@pytest.mark.xfail
def test_debug_dollar(r: redis.Redis):
    jdata, jtypes = load_types_data("a")

    r.json().set("doc1", "$", jdata)

    # Test multi
    assert r.json().debug("MEMORY", "doc1", "$..a") == [72, 24, 24, 16, 16, 1, 0]

    # Test single
    assert r.json().debug("MEMORY", "doc1", "$.nested2.a") == [24]

    # Test legacy
    assert r.json().debug("MEMORY", "doc1", "..a") == 72

    # Test missing path (defaults to root)
    assert r.json().debug("MEMORY", "doc1") == 72

    # Test missing key
    assert r.json().debug("MEMORY", "non_existing_doc", "$..a") == []


@pytest.mark.xfail
def test_resp_dollar(r: redis.Redis, json_data: Dict[str, Any]):
    r.json().set("doc1", "$", json_data)

    # Test multi
    res = r.json().resp("doc1", "$..a")

    assert res == [
        [
            "{",
            "A1_B1",
            10,
            "A1_B2",
            "false",
            "A1_B3",
            [
                "{",
                "A1_B3_C1",
                None,
                "A1_B3_C2",
                [
                    "[",
                    "A1_B3_C2_D1_1",
                    "A1_B3_C2_D1_2",
                    "-19.5",
                    "A1_B3_C2_D1_4",
                    "A1_B3_C2_D1_5",
                    ["{", "A1_B3_C2_D1_6_E1", "true"],
                ],
                "A1_B3_C3",
                ["[", 1],
            ],
            "A1_B4",
            ["{", "A1_B4_C1", "foo"],
        ],
        [
            "{",
            "A2_B1",
            20,
            "A2_B2",
            "false",
            "A2_B3",
            [
                "{",
                "A2_B3_C1",
                None,
                "A2_B3_C2",
                [
                    "[",
                    "A2_B3_C2_D1_1",
                    "A2_B3_C2_D1_2",
                    "-37.5",
                    "A2_B3_C2_D1_4",
                    "A2_B3_C2_D1_5",
                    ["{", "A2_B3_C2_D1_6_E1", "false"],
                ],
                "A2_B3_C3",
                ["[", 2],
            ],
            "A2_B4",
            ["{", "A2_B4_C1", "bar"],
        ],
    ]

    # Test single
    res_single = r.json().resp("doc1", "$.L1.a")
    assert res_single == [
        [
            "{",
            "A1_B1",
            10,
            "A1_B2",
            "false",
            "A1_B3",
            [
                "{",
                "A1_B3_C1",
                None,
                "A1_B3_C2",
                [
                    "[",
                    "A1_B3_C2_D1_1",
                    "A1_B3_C2_D1_2",
                    "-19.5",
                    "A1_B3_C2_D1_4",
                    "A1_B3_C2_D1_5",
                    ["{", "A1_B3_C2_D1_6_E1", "true"],
                ],
                "A1_B3_C3",
                ["[", 1],
            ],
            "A1_B4",
            ["{", "A1_B4_C1", "foo"],
        ]
    ]

    # Test missing path
    r.json().resp("doc1", "$.nowhere")

    # Test missing key
    # with pytest.raises(exceptions.ResponseError):
    r.json().resp("non_existing_doc", "$..a")
