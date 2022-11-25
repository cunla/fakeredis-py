"""Tests for `fakeredis-py`'s emulation of Redis's JSON command subset."""

from __future__ import annotations

from typing import (
    Any,
    Dict,
    List,
    Tuple,
)

import pytest
import redis
from redis import exceptions
from redis.commands.json.decoders import (
    decode_list,
    unstring,
)
from redis.commands.json.path import Path


def test_jsonget(r: redis.Redis) -> None:
    r.json().set("foo2", Path.root_path(), {'x': "bar", 'y': {'x': 33}}, )
    assert r.json().get("foo2") == {'x': "bar", 'y': {'x': 33}}
    assert r.json().get("foo2", Path("$..x")) == ['bar', 33]

    r.json().set("foo", Path.root_path(), {'x': "bar"}, )
    assert r.json().get("foo") == {'x': "bar"}
    assert r.json().get("foo", Path("$.a"), Path("$.x")) == {'$.a': [], '$.x': ['bar']}


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


def test_json_setbinarykey(r: redis.Redis) -> None:
    data = {"hello": "world", b"some": "value"}

    with pytest.raises(TypeError):
        r.json().set("some-key", Path.root_path(), data)

    result = r.json().set(
        "some-key",
        Path.root_path(),
        data,
        decode_keys=True,
    )

    assert result


def test_json_setgetdeleteforget(r: redis.Redis) -> None:
    assert r.json().set("foo", Path.root_path(), {'x': "bar"}, ) == 1
    assert r.json().get("foo") == "bar"
    assert r.json().get("baz") is None
    assert r.json().delete("foo") == 1
    assert r.json().forget("foo") == 0  # second delete
    assert r.exists("foo") == 0


def test_json_get_jset(r: redis.Redis) -> None:
    assert r.json().set("foo", Path.root_path(), "bar", ) == 1
    assert "bar" == r.json().get("foo")
    assert r.json().get("baz") is None
    assert 1 == r.json().delete("foo")
    assert r.exists("foo") == 0


def test_nonascii_setgetdelete(r: redis.Redis) -> None:
    assert r.json().set("not-ascii", Path.root_path(), "hyvää-élève", )
    assert "hyvää-élève" == r.json().get("not-ascii", no_escape=True, )
    assert 1 == r.json().delete("not-ascii")
    assert r.exists("not-ascii") == 0


def test_json_set_existential_modifiers_should_succeed(r: redis.Redis) -> None:
    obj = {"foo": "bar"}
    assert r.json().set("obj", Path.root_path(), obj)

    # Test that flags prevent updates when conditions are unmet
    assert r.json().set("obj", Path("foo"), "baz", nx=True, ) is None

    assert r.json().set("obj", Path("qaz"), "baz", xx=True, ) is None

    # Test that flags allow updates when conditions are met
    assert r.json().set(
        "obj",
        Path("foo"),
        "baz",
        xx=True,
    )
    assert r.json().set(
        "obj",
        Path("qaz"),
        "baz",
        nx=True,
    )

    # Test that flags are mutually exclusive
    with pytest.raises(redis.ResponseError):
        r.json().set(
            "obj",
            Path("foo"),
            "baz",
            nx=True,
            xx=True,
        )


@pytest.mark.xfail
def test_mget_should_succeed(r: redis.Redis) -> None:
    r.json().set(
        "1",
        Path.root_path(),
        1,
    )
    r.json().set(
        "2",
        Path.root_path(),
        2,
    )

    assert r.json().mget(
        ["1"],
        Path.root_path(),
    ) == [1]

    assert r.json().mget(
        [1, 2],
        Path.root_path(),
    ) == [1, 2]


@pytest.mark.xfail
def test_clear(r: redis.Redis) -> None:
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 1, 2, 3, 4],
    )

    assert 1 == r.json().clear(
        "arr",
        Path.root_path(),
    )
    assert [] == r.json().get("arr")


@pytest.mark.xfail
def test_type(r: redis.Redis) -> None:
    r.json().set(
        "1",
        Path.root_path(),
        1,
    )

    assert "integer" == r.json().type(
        "1",
        Path.root_path(),
    )
    assert "integer" == r.json().type("1")


@pytest.mark.xfail
def test_numincrby(r: redis.Redis) -> None:
    r.json().set(
        "num",
        Path.root_path(),
        1,
    )

    assert 2 == r.json().numincrby(
        "num",
        Path.root_path(),
        1,
    )
    assert 2.5 == r.json().numincrby(
        "num",
        Path.root_path(),
        0.5,
    )
    assert 1.25 == r.json().numincrby(
        "num",
        Path.root_path(),
        -1.25,
    )


@pytest.mark.xfail
def test_nummultby(r: redis.Redis) -> None:
    r.json().set(
        "num",
        Path.root_path(),
        1,
    )

    with pytest.deprecated_call():
        assert 2 == r.json().nummultby(
            "num",
            Path.root_path(),
            2,
        )
        assert 5 == r.json().nummultby(
            "num",
            Path.root_path(),
            2.5,
        )
        assert 2.5 == r.json().nummultby(
            "num",
            Path.root_path(),
            0.5,
        )


@pytest.mark.xfail
def test_toggle(r: redis.Redis) -> None:
    r.json().set(
        "bool",
        Path.root_path(),
        False,
    )
    assert r.json().toggle(
        "bool",
        Path.root_path(),
    )
    assert (
            r.json().toggle(
                "bool",
                Path.root_path(),
            )
            is False
    )

    # check non-boolean value
    r.json().set(
        "num",
        Path.root_path(),
        1,
    )

    with pytest.raises(redis.exceptions.ResponseError):
        r.json().toggle("num", Path.root_path())


@pytest.mark.xfail
def test_strappend(r: redis.Redis) -> None:
    r.json().set(
        "json-key",
        Path.root_path(),
        "foo",
    )

    assert 6 == r.json().strappend(
        "json-key",
        "bar",
    )
    assert "foobar" == r.json().get(
        "json-key",
        Path.root_path(),
    )


@pytest.mark.xfail
def test_debug(r: redis.Redis) -> None:
    r.json().set(
        "str",
        Path.root_path(),
        "foo",
    )
    assert 24 == r.json().debug(
        "MEMORY",
        "str",
        Path.root_path(),
    )
    assert 24 == r.json().debug(
        "MEMORY",
        "str",
    )

    # technically help is valid
    assert isinstance(
        r.json().debug("HELP"),
        list,
    )


@pytest.mark.xfail
def test_strlen(r: redis.Redis) -> None:
    r.json().set(
        "str",
        Path.root_path(),
        "foo",
    )

    assert 3 == r.json().strlen(
        "str",
        Path.root_path(),
    )

    r.json().strappend(
        "str",
        "bar",
        Path.root_path(),
    )

    assert 6 == r.json().strlen(
        "str",
        Path.root_path(),
    )
    assert 6 == r.json().strlen("str")


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
def test_arrlen(r: redis.Redis) -> None:
    r.json().set(
        "arr",
        Path.root_path(),
        [0, 1, 2, 3, 4],
    )
    assert 5 == r.json().arrlen(
        "arr",
        Path.root_path(),
    )
    assert 5 == r.json().arrlen("arr")
    assert r.json().arrlen("fake-key") is None


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


def test_json_commands_in_pipeline(r: redis.Redis) -> None:
    p = r.json().pipeline()
    p.set(
        "foo",
        Path.root_path(),
        "bar",
    )
    p.get("foo")
    p.delete("foo")
    assert [True, "bar", 1] == p.execute()
    assert r.keys() == []
    assert r.get("foo") is None

    # now with a true, json object
    r.flushdb()
    p = r.json().pipeline()
    d = {"hello": "world", "oh": "snap"}

    with pytest.deprecated_call():
        p.jsonset("foo", Path.root_path(), d)
        p.jsonget("foo")

    p.exists("not-a-real-key")
    p.delete("foo")

    assert [True, d, 0, 1] == p.execute()
    assert r.keys() == []
    assert r.get("foo") is None


@pytest.mark.xfail
def test_json_delete_with_dollar(r: redis.Redis) -> None:
    doc1 = {"a": 1, "nested": {"a": 2, "b": 3}}
    assert r.json().set("doc1", "$", doc1)
    assert r.json().delete("doc1", "$..a") == 2
    r = r.json().get("doc1", "$")
    assert r == [{"nested": {"b": 3}}]

    doc2 = {"a": {"a": 2, "b": 3}, "b": ["a", "b"], "nested": {"b": [True, "a", "b"]}}
    assert r.json().set("doc2", "$", doc2)
    assert r.json().delete("doc2", "$..a") == 1
    res = r.json().get("doc2", "$")
    assert res == [{"nested": {"b": [True, "a", "b"]}, "b": ["a", "b"]}]

    doc3 = [
        {
            "ciao": ["non ancora"],
            "nested": [
                {"ciao": [1, "a"]},
                {"ciao": [2, "a"]},
                {"ciaoc": [3, "non", "ciao"]},
                {"ciao": [4, "a"]},
                {"e": [5, "non", "ciao"]},
            ],
        }
    ]
    assert r.json().set("doc3", "$", doc3)
    assert r.json().delete("doc3", '$.[0]["nested"]..ciao') == 3

    doc3val = [
        [
            {
                "ciao": ["non ancora"],
                "nested": [
                    {},
                    {},
                    {"ciaoc": [3, "non", "ciao"]},
                    {},
                    {"e": [5, "non", "ciao"]},
                ],
            }
        ]
    ]
    res = r.json().get("doc3", "$")
    assert res == doc3val

    # Test default path
    assert r.json().delete("doc3") == 1
    assert r.json().get("doc3", "$") is None

    r.json().delete("not_a_document", "..a")


@pytest.mark.xfail
def test_json_forget_with_dollar(r: redis.Redis) -> None:
    doc1 = {"a": 1, "nested": {"a": 2, "b": 3}}
    assert r.json().set("doc1", "$", doc1)
    assert r.json().forget("doc1", "$..a") == 2
    r = r.json().get("doc1", "$")
    assert r == [{"nested": {"b": 3}}]

    doc2 = {"a": {"a": 2, "b": 3}, "b": ["a", "b"], "nested": {"b": [True, "a", "b"]}}
    assert r.json().set("doc2", "$", doc2)
    assert r.json().forget("doc2", "$..a") == 1
    res = r.json().get("doc2", "$")
    assert res == [{"nested": {"b": [True, "a", "b"]}, "b": ["a", "b"]}]

    doc3 = [
        {
            "ciao": ["non ancora"],
            "nested": [
                {"ciao": [1, "a"]},
                {"ciao": [2, "a"]},
                {"ciaoc": [3, "non", "ciao"]},
                {"ciao": [4, "a"]},
                {"e": [5, "non", "ciao"]},
            ],
        }
    ]
    assert r.json().set("doc3", "$", doc3)
    assert r.json().forget("doc3", '$.[0]["nested"]..ciao') == 3

    doc3val = [
        [
            {
                "ciao": ["non ancora"],
                "nested": [
                    {},
                    {},
                    {"ciaoc": [3, "non", "ciao"]},
                    {},
                    {"e": [5, "non", "ciao"]},
                ],
            }
        ]
    ]
    res = r.json().get("doc3", "$")
    assert res == doc3val

    # Test default path
    assert r.json().forget("doc3") == 1
    assert r.json().get("doc3", "$") is None

    r.json().forget("not_a_document", "..a")


@pytest.mark.xfail
def test_json_mget_dollar(r: redis.Redis) -> None:
    # Test mget with multi paths
    r.json().set(
        "doc1",
        "$",
        {"a": 1, "b": 2, "nested": {"a": 3}, "c": None, "nested2": {"a": None}},
    )
    r.json().set(
        "doc2",
        "$",
        {"a": 4, "b": 5, "nested": {"a": 6}, "c": None, "nested2": {"a": [None]}},
    )
    # Compare also to single JSON.GET
    assert r.json().get("doc1", "$..a") == [1, 3, None]
    assert r.json().get("doc2", "$..a") == [4, 6, [None]]

    # Test mget with single path
    assert r.json().mget("doc1", "$..a") == [1, 3, None]

    # Test mget with multi path
    assert r.json().mget(["doc1", "doc2"], "$..a") == [[1, 3, None], [4, 6, [None]]]

    # Test missing key
    assert r.json().mget(["doc1", "missing_doc"], "$..a") == [[1, 3, None], None]
    res = r.json().mget(["missing_doc1", "missing_doc2"], "$..a")

    assert res == [None, None]


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
def test_strappend_dollar(r: redis.Redis) -> None:
    r.json().set(
        "doc1",
        "$",
        {
            "a": "foo",
            "nested1": {"a": "hello"},
            "nested2": {"a": 31},
        },
    )

    # Test multi
    assert r.json().strappend(
        "doc1",
        "bar",
        "$..a",
    ) == [6, 8, None]

    assert r.json().get("doc1", "$") == [
        {
            "a": "foobar",
            "nested1": {"a": "hello-bar"},
            "nested2": {"a": 31},
        }
    ]
    # Test single
    assert r.json().strappend(
        "doc1",
        "baz",
        "$.nested1.a",
    ) == [11]

    assert r.json().get("doc1", "$") == [
        {
            "a": "foobar",
            "nested1": {"a": "hello-bar-baz"},
            "nested2": {"a": 31},
        }
    ]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().strappend(
            "non_existing_doc",
            "$..a",
            "err",
        )

    # Test multi
    assert (
            r.json().strappend(
                "doc1",
                "bar",
                ".*.a",
            )
            == 8
    )
    assert r.json().get("doc1", "$") == [
        {
            "a": "foo",
            "nested1": {"a": "hello-bar"},
            "nested2": {"a": 31},
        }
    ]

    # Test missing path
    with pytest.raises(exceptions.ResponseError):
        r.json().strappend("doc1", "piu")


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
    r.json().set(
        "doc1",
        "$",
        {
            "a": ["foo"],
            "nested1": {"a": ["hello", None, "world"]},
            "nested2": {"a": 31},
        },
    )
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
    r.json().set(
        "doc1",
        "$",
        {
            "a": ["foo"],
            "nested1": {"a": ["hello", None, "world"]},
            "nested2": {"a": 31},
        },
    )
    # Test multi (all paths are updated, but return result of last path)
    assert r.json().arrappend("doc1", "..a", "bar", "racuda") == 5

    assert r.json().get("doc1", "$") == [
        {
            "a": ["foo", "bar", "racuda"],
            "nested1": {"a": ["hello", None, "world", "bar", "racuda"]},
            "nested2": {"a": 31},
        }
    ]
    # Test single
    assert r.json().arrappend("doc1", ".nested1.a", "baz") == 6
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


@pytest.mark.xfail
def test_arrinsert_dollar(r: redis.Redis) -> None:
    r.json().set(
        "doc1",
        "$",
        {
            "a": ["foo"],
            "nested1": {"a": ["hello", None, "world"]},
            "nested2": {"a": 31},
        },
    )
    # Test multi
    assert r.json().arrinsert("doc1", "$..a", "1", "bar", "racuda") == [3, 5, None]

    assert r.json().get("doc1", "$") == [
        {
            "a": ["foo", "bar", "racuda"],
            "nested1": {"a": ["hello", "bar", "racuda", None, "world"]},
            "nested2": {"a": 31},
        }
    ]
    # Test single
    assert r.json().arrinsert("doc1", "$.nested1.a", -2, "baz") == [6]
    assert r.json().get("doc1", "$") == [
        {
            "a": ["foo", "bar", "racuda"],
            "nested1": {"a": ["hello", "bar", "racuda", "baz", None, "world"]},
            "nested2": {"a": 31},
        }
    ]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().arrappend("non_existing_doc", "$..a")


@pytest.mark.xfail
def test_arrlen_dollar(r: redis.Redis) -> None:
    r.json().set(
        "doc1",
        "$",
        {
            "a": ["foo"],
            "nested1": {"a": ["hello", None, "world"]},
            "nested2": {"a": 31},
        },
    )

    # Test multi
    assert r.json().arrlen("doc1", "$..a") == [1, 3, None]
    assert r.json().arrappend("doc1", "$..a", "non", "abba", "stanza") == [
        4,
        6,
        None,
    ]

    r.json().clear("doc1", "$.a")
    assert r.json().arrlen("doc1", "$..a") == [0, 6, None]
    # Test single
    assert r.json().arrlen("doc1", "$.nested1.a") == [6]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().arrappend("non_existing_doc", "$..a")

    r.json().set(
        "doc1",
        "$",
        {
            "a": ["foo"],
            "nested1": {"a": ["hello", None, "world"]},
            "nested2": {"a": 31},
        },
    )
    # Test multi (return result of last path)
    assert r.json().arrlen("doc1", "$..a") == [1, 3, None]
    assert r.json().arrappend("doc1", "..a", "non", "abba", "stanza") == 6

    # Test single
    assert r.json().arrlen("doc1", ".nested1.a") == 6

    # Test missing key
    assert r.json().arrlen("non_existing_doc", "..a") is None


@pytest.mark.xfail
def test_arrpop_dollar(r: redis.Redis) -> None:
    r.json().set(
        "doc1",
        "$",
        {
            "a": ["foo"],
            "nested1": {"a": ["hello", None, "world"]},
            "nested2": {"a": 31},
        },
    )

    # # # Test multi
    assert r.json().arrpop("doc1", "$..a", 1) == ['"foo"', None, None]

    assert r.json().get("doc1", "$") == [
        {"a": [], "nested1": {"a": ["hello", "world"]}, "nested2": {"a": 31}}
    ]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().arrpop("non_existing_doc", "..a")

    # # Test legacy
    r.json().set(
        "doc1",
        "$",
        {
            "a": ["foo"],
            "nested1": {"a": ["hello", None, "world"]},
            "nested2": {"a": 31},
        },
    )
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
    r.json().set(
        "doc1",
        "$",
        {
            "a": ["foo"],
            "nested1": {"a": ["hello", None, "world"]},
            "nested2": {"a": 31},
        },
    )
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
    r.json().set(
        "doc1",
        "$",
        {
            "a": ["foo"],
            "nested1": {"a": ["hello", None, "world"]},
            "nested2": {"a": 31},
        },
    )

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
    r.json().set(
        "doc1",
        "$",
        {
            "nested1": {"a": {"foo": 10, "bar": 20}},
            "a": ["foo"],
            "nested2": {"a": {"baz": 50}},
        },
    )

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
    r.json().set(
        "doc1",
        "$",
        {
            "nested1": {"a": {"foo": 10, "bar": 20}},
            "a": ["foo"],
            "nested2": {"a": {"baz": 50}},
        },
    )
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
    """TODO(the-wondersmith): Add docstring"""

    td = {
        "object": {},
        "array": [],
        "string": "str",
        "integer": 42,
        "number": 1.2,
        "boolean": False,
        "null": None,
    }
    jdata = {}
    types = []
    for i, (k, v) in zip(range(1, len(td) + 1), iter(td.items())):
        jdata[f"nested{i}"] = {nested_key_name: v}
        types.append(k)

    return jdata, types


@pytest.mark.xfail
def test_type_dollar(r: redis.Redis) -> None:
    jdata, jtypes = load_types_data("a")
    r.json().set("doc1", "$", jdata)
    # Test multi
    assert r.json().type("doc1", "$..a") == jtypes

    # Test single
    assert r.json().type("doc1", "$.nested2.a") == [jtypes[1]]

    # Test missing key
    assert r.json().type("non_existing_doc", "..a") is None


@pytest.mark.xfail
def test_clear_dollar(r: redis.Redis) -> None:
    r.json().set(
        "doc1",
        "$",
        {
            "nested1": {"a": {"foo": 10, "bar": 20}},
            "a": ["foo"],
            "nested2": {"a": "claro"},
            "nested3": {"a": {"baz": 50}},
        },
    )
    # Test multi
    assert r.json().clear("doc1", "$..a") == 3

    assert r.json().get("doc1", "$") == [
        {"nested1": {"a": {}}, "a": [], "nested2": {"a": "claro"}, "nested3": {"a": {}}}
    ]

    # Test single
    r.json().set(
        "doc1",
        "$",
        {
            "nested1": {"a": {"foo": 10, "bar": 20}},
            "a": ["foo"],
            "nested2": {"a": "claro"},
            "nested3": {"a": {"baz": 50}},
        },
    )
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

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().clear("non_existing_doc", "$..a")


@pytest.mark.xfail
def test_toggle_dollar(r: redis.Redis) -> None:
    r.json().set(
        "doc1",
        "$",
        {
            "a": ["foo"],
            "nested1": {"a": False},
            "nested2": {"a": 31},
            "nested3": {"a": True},
        },
    )
    # Test multi
    assert r.json().toggle("doc1", "$..a") == [None, 1, None, 0]
    assert r.json().get("doc1", "$") == [
        {
            "a": ["foo"],
            "nested1": {"a": True},
            "nested2": {"a": 31},
            "nested3": {"a": False},
        }
    ]

    # Test missing key
    with pytest.raises(exceptions.ResponseError):
        r.json().toggle("non_existing_doc", "$..a")


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
        ".",
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
        ".",
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
        ".",
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


# @pytest.mark.xfail
def test_decoders_and_unstring():
    assert unstring("4") == 4
    assert unstring("45.55") == 45.55
    assert unstring("hello world") == "hello world"

    assert decode_list(b"45.55") == 45.55
    assert decode_list("45.55") == 45.55
    assert decode_list(["hello", b"world"]) == ["hello", "world"]


# noinspection PyUnresolvedReferences
@pytest.mark.xfail
def test_custom_decoder(r: redis.Redis) -> None:
    # Standard Library Imports
    import json

    # Third-Party Imports
    import orjson

    cj = r.json(encoder=orjson, decoder=orjson)
    assert cj.set("foo", Path.root_path(), "bar")
    assert "bar" == cj.get("foo")
    assert cj.get("baz") is None
    assert 1 == cj.delete("foo")
    assert r.exists("foo") == 0
    assert not isinstance(cj.__encoder__, json.JSONEncoder)
    assert not isinstance(cj.__decoder__, json.JSONDecoder)


# @pytest.mark.xfail
def test_set_file(r: redis.Redis) -> None:
    # Standard Library Imports
    import json
    import tempfile

    obj = {"hello": "world"}
    jsonfile = tempfile.NamedTemporaryFile(suffix=".json")
    with open(jsonfile.name, "w+") as fp:
        fp.write(json.dumps(obj))

    no_json_file = tempfile.NamedTemporaryFile()
    no_json_file.write(b"Hello World")

    assert r.json().set_file("test", Path.root_path(), jsonfile.name)
    assert r.json().get("test") == obj
    with pytest.raises(json.JSONDecodeError):
        r.json().set_file("test2", Path.root_path(), no_json_file.name)


# @pytest.mark.xfail
def test_set_path(r: redis.Redis) -> None:
    # Standard Library Imports
    import json
    import tempfile

    root = tempfile.mkdtemp()
    sub = tempfile.mkdtemp(dir=root)
    jsonfile = tempfile.mktemp(suffix=".json", dir=sub)
    no_json_file = tempfile.mktemp(dir=root)

    with open(jsonfile, "w+") as fp:
        fp.write(json.dumps({"hello": "world"}))
    with open(no_json_file, "a+") as fp:
        fp.write("hello")

    result = {jsonfile: True, no_json_file: False}
    assert r.json().set_path(Path.root_path(), root) == result
    assert r.json().get(jsonfile.rsplit(".")[0]) == {"hello": "world"}
