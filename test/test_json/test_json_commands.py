"""Tests for `fakeredis-py`'s emulation of Redis's JSON command subset."""

from __future__ import annotations

import pytest
import redis
from redis import exceptions
from redis.commands.json.path import Path
from typing import (Any, Dict, List, Tuple, )

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
def test_numincrby(r: redis.Redis) -> None:
    r.json().set("num", Path.root_path(), 1)

    assert 2 == r.json().numincrby("num", Path.root_path(), 1)
    assert 2.5 == r.json().numincrby("num", Path.root_path(), 0.5)
    assert 1.25 == r.json().numincrby("num", Path.root_path(), -1.25)


@pytest.mark.xfail
def test_nummultby(r: redis.Redis) -> None:
    r.json().set("num", Path.root_path(), 1)

    with pytest.deprecated_call():
        assert 2 == r.json().nummultby("num", Path.root_path(), 2)
        assert 5 == r.json().nummultby("num", Path.root_path(), 2.5)
        assert 2.5 == r.json().nummultby("num", Path.root_path(), 0.5)


@pytest.mark.xfail
def test_debug(r: redis.Redis) -> None:
    r.json().set("str", Path.root_path(), "foo")
    assert 24 == r.json().debug("MEMORY", "str", Path.root_path())
    assert 24 == r.json().debug("MEMORY", "str")

    # technically help is valid
    assert isinstance(r.json().debug("HELP"), list)


@pytest.mark.xfail
def test_arrtrim(r: redis.Redis) -> None:
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 1, 2, 3, 4],
    )

    assert 3 == r.json().arrtrim(
        "arr",
        Path.root_path(),
        1,
        3,
    )
    assert [1, 2, 3] == r.json().get("arr")

    # <0 test, should be 0 equivalent
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 1, 2, 3, 4],
    )
    assert 0 == r.json().arrtrim(
        "arr",
        Path.root_path(),
        -1,
        3,
    )

    # testing stop > end
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 1, 2, 3, 4],
    )
    assert 2 == r.json().arrtrim(
        "arr",
        Path.root_path(),
        3,
        99,
    )

    # start > array size and stop
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 1, 2, 3, 4],
    )
    assert 0 == r.json().arrtrim(
        "arr",
        Path.root_path(),
        9,
        1,
    )

    # all larger
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 1, 2, 3, 4],
    )
    assert 0 == r.json().arrtrim(
        "arr",
        Path.root_path(),
        9,
        11,
    )


@pytest.mark.xfail
def test_resp(r: redis.Redis) -> None:
    obj = {
        "foo": "bar",
        "baz": 1,
        "qaz": True,
    }
    r.json().set(
        "obj",
        Path.root_path(),
        obj,
    )

    assert "bar" == r.json().resp(
        "obj",
        Path("foo"),
    )
    assert 1 == r.json().resp(
        "obj",
        Path("baz"),
    )
    assert r.json().resp(
        "obj",
        Path("qaz"),
    )
    assert isinstance(r.json().resp("obj"), list)


@pytest.mark.xfail
def test_numby_commands_dollar(r: redis.Redis) -> None:
    # Test NUMINCRBY
    r.json().set("doc1", "$", {"a": "b", "b": [{"a": 2}, {"a": 5.0}, {"a": "c"}]})
    # Test multi
    assert r.json().numincrby("doc1", "$..a", 2) == [None, 4, 7.0, None]

    assert r.json().numincrby("doc1", "$..a", 2.5) == [None, 6.5, 9.5, None]
    # Test single
    assert r.json().numincrby("doc1", "$.b[1].a", 2) == [11.5]

    assert r.json().numincrby("doc1", "$.b[2].a", 2) == [None]
    assert r.json().numincrby("doc1", "$.b[1].a", 3.5) == [15.0]

    # Test NUMMULTBY
    r.json().set("doc1", "$", {"a": "b", "b": [{"a": 2}, {"a": 5.0}, {"a": "c"}]})

    # test list
    with pytest.deprecated_call():
        assert r.json().nummultby("doc1", "$..a", 2) == [None, 4, 10, None]
        assert r.json().nummultby("doc1", "$..a", 2.5) == [None, 10.0, 25.0, None]

    # Test single
    with pytest.deprecated_call():
        assert r.json().nummultby("doc1", "$.b[1].a", 2) == [50.0]
        assert r.json().nummultby("doc1", "$.b[2].a", 2) == [None]
        assert r.json().nummultby("doc1", "$.b[1].a", 3) == [150.0]

    # test missing keys
    with pytest.raises(exceptions.ResponseError):
        r.json().numincrby("non_existing_doc", "$..a", 2)
        r.json().nummultby("non_existing_doc", "$..a", 2)

    # Test legacy NUMINCRBY
    r.json().set("doc1", "$", {"a": "b", "b": [{"a": 2}, {"a": 5.0}, {"a": "c"}]})
    assert r.json().numincrby("doc1", ".b[0].a", 3) == 5

    # Test legacy NUMMULTBY
    r.json().set("doc1", "$", {"a": "b", "b": [{"a": 2}, {"a": 5.0}, {"a": "c"}]})

    with pytest.deprecated_call():
        assert r.json().nummultby("doc1", ".b[0].a", 3) == 6


@pytest.mark.xfail
def test_strlen_dollar(r: redis.Redis) -> None:
    # Test multi
    r.json().set("doc1", "$", {"a": "foo", "nested1": {"a": "hello"}, "nested2": {"a": 31}})
    assert r.json().strlen("doc1", "$..a") == [3, 5, None]

    res2 = r.json().strappend("doc1", "bar", "$..a")
    res1 = r.json().strlen("doc1", "$..a")
    assert res1 == res2

    # Test single
    assert r.json().strlen("doc1", "$.nested1.a") == [8]
    assert r.json().strlen("doc1", "$.nested2.a") == [None]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().strlen("non_existing_doc", "$..a")


@pytest.mark.xfail
def test_arrtrim_dollar(r: redis.Redis) -> None:
    r.json().set("doc1", "$", SAMPLE_DATA)
    # Test multi
    assert r.json().arrtrim("doc1", "$..a", "1", -1) == [0, 2, None]
    assert r.json().get("doc1", "$") == [
        {"a": [], "nested1": {"a": [None, "world"]}, "nested2": {"a": 31}}
    ]

    assert r.json().arrtrim("doc1", "$..a", "1", "1") == [0, 1, None]
    assert r.json().get("doc1", "$") == [
        {"a": [], "nested1": {"a": ["world"]}, "nested2": {"a": 31}}
    ]
    # Test single
    assert r.json().arrtrim("doc1", "$.nested1.a", 1, 0) == [0]
    assert r.json().get("doc1", "$") == [{"a": [], "nested1": {"a": []}, "nested2": {"a": 31}}]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().arrtrim("non_existing_doc", "..a", "0", 1)

    # Test legacy
    r.json().set("doc1", "$", SAMPLE_DATA)

    # Test multi (all paths are updated, but return result of last path)
    assert r.json().arrtrim("doc1", "..a", "1", "-1") == 2

    # Test single
    assert r.json().arrtrim("doc1", ".nested1.a", "1", "1") == 1
    assert r.json().get("doc1", "$") == [
        {"a": [], "nested1": {"a": ["world"]}, "nested2": {"a": 31}}
    ]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().arrtrim("non_existing_doc", "..a", 1, 1)


def load_types_data(nested_key_name: str) -> Tuple[Dict[str, Any], List[str]]:
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
def test_type_dollar(r: redis.Redis) -> None:
    jdata, jtypes = load_types_data("a")
    r.json().set("doc1", "$", jdata)
    # Test multi
    assert r.json().type("doc1", "$..a") == jtypes

    # Test single
    assert r.json().type("doc1", f"$.nested_{jtypes[1].decode()}.a") == [jtypes[1]]

    # Test missing key
    assert r.json().type("non_existing_doc", "..a") is None


@pytest.mark.xfail
def test_debug_dollar(r: redis.Redis) -> None:
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
def test_resp_dollar(r: redis.Redis, json_data: Dict[str, Any]) -> None:
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
    resSingle = r.json().resp("doc1", "$.L1.a")
    assert resSingle == [
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
