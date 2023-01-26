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
def test_arrappend(r: redis.Redis) -> None:
    r.json().set(
        "arr",
        Path.root_path(),
        [1],
    )

    assert 2 == r.json().arrappend(
        "arr",
        Path.root_path(),
        2,
    )
    assert 4 == r.json().arrappend(
        "arr",
        Path.root_path(),
        3,
        4,
    )
    assert 7 == r.json().arrappend(
        "arr",
        Path.root_path(),
        *[5, 6, 7],
    )


@pytest.mark.xfail
def test_arrindex(r: redis.Redis) -> None:
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 1, 2, 3, 4],
    )

    assert 1 == r.json().arrindex(
        "arr",
        Path.root_path(),
        1,
    )
    assert -1 == r.json().arrindex(
        "arr",
        Path.root_path(),
        1,
        2,
    )


@pytest.mark.xfail
def test_arrinsert(r: redis.Redis) -> None:
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 4],
    )

    assert 5 - -r.json().arrinsert(
        "arr",
        Path.root_path(),
        1,
        *[1, 2, 3],
    )
    assert [0, 1, 2, 3, 4] == r.json().get("arr")

    # test prepends
    r.json().set(
        "val2",
        Path.root_path(),
        [5, 6, 7, 8, 9],
    )
    r.json().arrinsert(
        "val2",
        Path.root_path(),
        0,
        ["some", "thing"],
    )
    assert r.json().get("val2") == [["some", "thing"], 5, 6, 7, 8, 9]


@pytest.mark.xfail
def test_arrpop(r: redis.Redis) -> None:
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 1, 2, 3, 4],
    )

    assert 4 == r.json().arrpop(
        "arr",
        Path.root_path(),
        4,
    )
    assert 3 == r.json().arrpop(
        "arr",
        Path.root_path(),
        -1,
    )
    assert 2 == r.json().arrpop(
        "arr",
        Path.root_path(),
    )
    assert 0 == r.json().arrpop(
        "arr",
        Path.root_path(),
        0,
    )
    assert [1] == r.json().get("arr")

    # test out of bounds
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 1, 2, 3, 4],
    )
    assert 4 == r.json().arrpop(
        "arr",
        Path.root_path(),
        99,
    )

    # none test
    r.json().set(
        "arr",
        Path.root_path(),
        [],
    )
    assert r.json().arrpop("arr") is None


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
def test_objkeys(r: redis.Redis) -> None:
    obj = {
        "foo": "bar",
        "baz": "qaz",
    }

    r.json().set(
        "obj",
        Path.root_path(),
        obj,
    )

    keys = r.json().objkeys(
        "obj",
        Path.root_path(),
    )

    keys.sort()
    exp = list(obj.keys())
    exp.sort()

    assert exp == keys

    r.json().set("obj", Path.root_path(), obj)
    keys = r.json().objkeys("obj")
    assert keys == list(obj.keys())

    assert r.json().objkeys("fake-key") is None


@pytest.mark.xfail
def test_objlen(r: redis.Redis) -> None:
    obj = {
        "foo": "bar",
        "baz": "qaz",
    }

    r.json().set(
        "obj",
        Path.root_path(),
        obj,
    )
    assert len(obj) == r.json().objlen(
        "obj",
        Path.root_path(),
    )

    r.json().set("obj", Path.root_path(), obj)
    assert len(obj) == r.json().objlen("obj")


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
def test_arrappend_dollar(r: redis.Redis) -> None:
    r.json().set("doc1", "$", SAMPLE_DATA)

    # Test multi
    assert r.json().arrappend("doc1", "$..a", "bar", "racuda") == [3, 5, None]
    assert r.json().get("doc1", "$") == [
        {
            "a": ["foo", "bar", "racuda"],
            "nested1": {"a": ["hello", None, "world", "bar", "racuda"]},
            "nested2": {"a": 31},
        }
    ]

    # Test single
    assert r.json().arrappend("doc1", "$.nested1.a", "baz") == [6]
    assert r.json().get("doc1", "$") == [
        {
            "a": ["foo", "bar", "racuda"],
            "nested1": {"a": ["hello", None, "world", "bar", "racuda", "baz"]},
            "nested2": {"a": 31},
        }
    ]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().arrappend("non_existing_doc", "$..a")

    # Test legacy
    r.json().set("doc1", "$", SAMPLE_DATA)
    # Test multi (all paths are updated, but return result of last path)
    assert r.json().arrappend("doc1", "..a", "bar", "racuda") == 5

    assert r.json().get("doc1", "$") == [{
        "a": ["foo", "bar", "racuda"],
        "nested1": {"a": ["hello", None, "world", "bar", "racuda"]},
        "nested2": {"a": 31},
    }]
    # Test single
    assert r.json().arrappend("doc1", ".nested1.a", "baz") == 6
    assert r.json().get("doc1", "$") == [{
        "a": ["foo", "bar", "racuda"],
        "nested1": {"a": ["hello", None, "world", "bar", "racuda", "baz"]},
        "nested2": {"a": 31},
    }]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().arrappend("non_existing_doc", "$..a")


@pytest.mark.xfail
def test_arrinsert_dollar(r: redis.Redis) -> None:
    r.json().set("doc1", "$", SAMPLE_DATA)
    # Test multi
    assert r.json().arrinsert("doc1", "$..a", "1", "bar", "racuda") == [3, 5, None]

    assert r.json().get("doc1", "$") == [{
        "a": ["foo", "bar", "racuda"],
        "nested1": {"a": ["hello", "bar", "racuda", None, "world"]},
        "nested2": {"a": 31},
    }]
    # Test single
    assert r.json().arrinsert("doc1", "$.nested1.a", -2, "baz") == [6]
    assert r.json().get("doc1", "$") == [{
        "a": ["foo", "bar", "racuda"],
        "nested1": {"a": ["hello", "bar", "racuda", "baz", None, "world"]},
        "nested2": {"a": 31},
    }]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().arrappend("non_existing_doc", "$..a")


@pytest.mark.xfail
def test_arrpop_dollar(r: redis.Redis) -> None:
    r.json().set("doc1", "$", SAMPLE_DATA)

    # # # Test multi
    assert r.json().arrpop("doc1", "$..a", 1) == ['"foo"', None, None]

    assert r.json().get("doc1", "$") == [
        {"a": [], "nested1": {"a": ["hello", "world"]}, "nested2": {"a": 31}}
    ]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().arrpop("non_existing_doc", "..a")

    # # Test legacy
    r.json().set("doc1", "$", SAMPLE_DATA)
    # Test multi (all paths are updated, but return result of last path)
    assert r.json().arrpop("doc1", "..a", "1") is None
    assert r.json().get("doc1", "$") == [
        {"a": [], "nested1": {"a": ["hello", "world"]}, "nested2": {"a": 31}}
    ]

    # # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().arrpop("non_existing_doc", "..a")


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


@pytest.mark.xfail
def test_objkeys_dollar(r: redis.Redis) -> None:
    r.json().set("doc1", "$", SAMPLE_DATA)

    # Test single
    assert r.json().objkeys("doc1", "$.nested1.a") == [["foo", "bar"]]

    # Test legacy
    assert r.json().objkeys("doc1", ".*.a") == ["foo", "bar"]
    # Test single
    assert r.json().objkeys("doc1", ".nested2.a") == ["baz"]

    # Test missing key
    assert r.json().objkeys("non_existing_doc", "..a") is None

    # Test non existing doc
    with pytest.raises(exceptions.ResponseError):
        assert r.json().objkeys("non_existing_doc", "$..a") == []

    assert r.json().objkeys("doc1", "$..nowhere") == []


@pytest.mark.xfail
def test_objlen_dollar(r: redis.Redis) -> None:
    r.json().set("doc1", "$", SAMPLE_DATA)
    # Test multi
    assert r.json().objlen("doc1", "$..a") == [None, 2, 1]
    # Test single
    assert r.json().objlen("doc1", "$.nested1.a") == [2]

    # Test missing key, and path
    with pytest.raises(exceptions.ResponseError):
        r.json().objlen("non_existing_doc", "$..a")

    assert r.json().objlen("doc1", "$.nowhere") == []

    # Test legacy
    assert r.json().objlen("doc1", ".*.a") == 2

    # Test single
    assert r.json().objlen("doc1", ".nested2.a") == 1

    # Test missing key
    assert r.json().objlen("non_existing_doc", "..a") is None

    # Test missing path
    # with pytest.raises(exceptions.ResponseError):
    r.json().objlen("doc1", ".nowhere")


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


@pytest.mark.xfail
def test_arrindex_dollar(r: redis.Redis) -> None:
    r.json().set(
        "store",
        "$",
        {
            "store": {
                "book": [
                    {
                        "category": "reference",
                        "author": "Nigel Rees",
                        "title": "Sayings of the Century",
                        "price": 8.95,
                        "size": [10, 20, 30, 40],
                    },
                    {
                        "category": "fiction",
                        "author": "Evelyn Waugh",
                        "title": "Sword of Honour",
                        "price": 12.99,
                        "size": [50, 60, 70, 80],
                    },
                    {
                        "category": "fiction",
                        "author": "Herman Melville",
                        "title": "Moby Dick",
                        "isbn": "0-553-21311-3",
                        "price": 8.99,
                        "size": [5, 10, 20, 30],
                    },
                    {
                        "category": "fiction",
                        "author": "J. R. R. Tolkien",
                        "title": "The Lord of the Rings",
                        "isbn": "0-395-19395-8",
                        "price": 22.99,
                        "size": [5, 6, 7, 8],
                    },
                ],
                "bicycle": {"color": "red", "price": 19.95},
            }
        },
    )

    assert r.json().get("store", "$.store.book[?(@.price<10)].size") == [
        [10, 20, 30, 40],
        [5, 10, 20, 30],
    ]
    assert r.json().arrindex("store", "$.store.book[?(@.price<10)].size", "20") == [-1, -1]

    # Test index of int scalar in multi values
    r.json().set(
        "test_num",
        "..",
        [
            {"arr": [0, 1, 3.0, 3, 2, 1, 0, 3]},
            {"nested1_found": {"arr": [5, 4, 3, 2, 1, 0, 1, 2, 3.0, 2, 4, 5]}},
            {"nested2_not_found": {"arr": [2, 4, 6]}},
            {"nested3_scalar": {"arr": "3"}},
            [
                {"nested41_not_arr": {"arr_renamed": [1, 2, 3]}},
                {"nested42_empty_arr": {"arr": []}},
            ],
        ],
    )

    assert r.json().get("test_num", "$..arr") == [
        [0, 1, 3.0, 3, 2, 1, 0, 3],
        [5, 4, 3, 2, 1, 0, 1, 2, 3.0, 2, 4, 5],
        [2, 4, 6],
        "3",
        [],
    ]

    assert r.json().arrindex("test_num", "$..arr", 3) == [3, 2, -1, None, -1]

    # Test index of double scalar in multi values
    assert r.json().arrindex("test_num", "$..arr", 3.0) == [2, 8, -1, None, -1]

    # Test index of string scalar in multi values
    r.json().set(
        "test_string",
        "..",
        [
            {"arr": ["bazzz", "bar", 2, "baz", 2, "ba", "baz", 3]},
            {"nested1_found": {"arr": [None, "baz2", "buzz", 2, 1, 0, 1, "2", "baz", 2, 4, 5]}},
            {"nested2_not_found": {"arr": ["baz2", 4, 6]}},
            {"nested3_scalar": {"arr": "3"}},
            [
                {"nested41_arr": {"arr_renamed": [1, "baz", 3]}},
                {"nested42_empty_arr": {"arr": []}},
            ],
        ],
    )
    assert r.json().get("test_string", "$..arr") == [
        ["bazzz", "bar", 2, "baz", 2, "ba", "baz", 3],
        [None, "baz2", "buzz", 2, 1, 0, 1, "2", "baz", 2, 4, 5],
        ["baz2", 4, 6],
        "3",
        [],
    ]

    assert r.json().arrindex("test_string", "$..arr", "baz") == [
        3,
        8,
        -1,
        None,
        -1,
    ]

    assert r.json().arrindex("test_string", "$..arr", "baz", 2) == [
        3,
        8,
        -1,
        None,
        -1,
    ]
    assert r.json().arrindex("test_string", "$..arr", "baz", 4) == [
        6,
        8,
        -1,
        None,
        -1,
    ]
    assert r.json().arrindex("test_string", "$..arr", "baz", -5) == [
        3,
        8,
        -1,
        None,
        -1,
    ]
    assert r.json().arrindex("test_string", "$..arr", "baz", 4, 7) == [
        6,
        -1,
        -1,
        None,
        -1,
    ]
    assert r.json().arrindex("test_string", "$..arr", "baz", 4, -1) == [
        6,
        8,
        -1,
        None,
        -1,
    ]
    assert r.json().arrindex("test_string", "$..arr", "baz", 4, 0) == [
        6,
        8,
        -1,
        None,
        -1,
    ]
    assert r.json().arrindex("test_string", "$..arr", "5", 7, -1) == [
        -1,
        -1,
        -1,
        None,
        -1,
    ]
    assert r.json().arrindex("test_string", "$..arr", "5", 7, 0) == [
        -1,
        -1,
        -1,
        None,
        -1,
    ]

    # Test index of None scalar in multi values
    r.json().set(
        "test_None",
        "..",
        [
            {"arr": ["bazzz", "None", 2, None, 2, "ba", "baz", 3]},
            {"nested1_found": {"arr": ["zaz", "baz2", "buzz", 2, 1, 0, 1, "2", None, 2, 4, 5]}},
            {"nested2_not_found": {"arr": ["None", 4, 6]}},
            {"nested3_scalar": {"arr": None}},
            [
                {"nested41_arr": {"arr_renamed": [1, None, 3]}},
                {"nested42_empty_arr": {"arr": []}},
            ],
        ],
    )
    assert r.json().get("test_None", "$..arr") == [
        ["bazzz", "None", 2, None, 2, "ba", "baz", 3],
        ["zaz", "baz2", "buzz", 2, 1, 0, 1, "2", None, 2, 4, 5],
        ["None", 4, 6],
        None,
        [],
    ]

    # Fail with none-scalar value
    with pytest.raises(exceptions.ResponseError):
        r.json().arrindex("test_None", "$..nested42_empty_arr.arr", {"arr": []})

    # Do not fail with none-scalar value in legacy mode
    assert r.json().arrindex("test_None", ".[4][1].nested42_empty_arr.arr", '{"arr":[]}') == -1

    # Test legacy (path begins with dot)
    # Test index of int scalar in single value
    assert r.json().arrindex("test_num", ".[0].arr", 3) == 3
    assert r.json().arrindex("test_num", ".[0].arr", 9) == -1

    with pytest.raises(exceptions.ResponseError):
        r.json().arrindex("test_num", ".[0].arr_not", 3)
    # Test index of string scalar in single value
    assert r.json().arrindex("test_string", ".[0].arr", "baz") == 3
    assert r.json().arrindex("test_string", ".[0].arr", "faz") == -1
    # Test index of None scalar in single value
    assert r.json().arrindex("test_None", ".[0].arr", "None") == 1
    assert r.json().arrindex("test_None", "..nested2_not_found.arr", "None") == 0
