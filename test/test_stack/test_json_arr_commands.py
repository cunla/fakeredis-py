import pytest
import redis
import valkey
from redis.commands.json.path import Path

from test import testtools
from test.conftest import ServerDetails
from test.testtools import raw_command

json_tests = pytest.importorskip("jsonpath_ng")


def test_arrlen(r: redis.Redis, real_server_details: ServerDetails):
    server_type = real_server_details.server_type
    r.json().set("arr", Path.root_path(), [0, 1, 2, 3, 4])
    assert r.json().arrlen("arr", Path.root_path()) == testtools.json_legacy_reply(r, server_type, 5)
    assert r.json().arrlen("arr") == testtools.json_legacy_reply(r, server_type, 5)
    assert r.json().arrlen("fake-key") is None

    r.json().set(
        "doc1", Path.root_path(), {"a": ["foo"], "nested1": {"a": ["hello", None, "world"]}, "nested2": {"a": 31}}
    )

    assert r.json().arrlen("doc1", "$..a") == [1, 3, None]
    assert r.json().arrlen("doc1", "$.nested1.a") == [3]

    r.json().set("doc2", "$", {"a": ["foo"], "nested1": {"a": ["hello", 1, 1, None, "world"]}, "nested2": {"a": 31}})
    assert r.json().arrlen("doc2", "$..a") == [1, 5, None]
    assert r.json().arrlen("doc2", ".nested1.a") == testtools.json_legacy_reply(r, server_type, 5)
    r.json().set("doc1", "$", {"a": ["foo"], "nested1": {"a": ["hello", None, "world"]}, "nested2": {"a": 31}})

    # Test multi
    assert r.json().arrlen("doc1", "$..a") == [1, 3, None]
    assert r.json().arrappend("doc1", "$..a", "non", "abba", "stanza") == [4, 6, None]

    r.json().clear("doc1", "$.a")
    assert r.json().arrlen("doc1", "$..a") == [0, 6, None]
    # Test single
    assert r.json().arrlen("doc1", "$.nested1.a") == [6]

    # Test missing key
    with pytest.raises(Exception) as ctx:
        r.json().arrappend("non_existing_doc", "$..a")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    r.json().set("doc1", "$", {"a": ["foo"], "nested1": {"a": ["hello", None, "world"]}, "nested2": {"a": 31}})
    # Test multi (return result of last path)
    assert r.json().arrlen("doc1", "$..a") == [1, 3, None]
    assert r.json().arrappend("doc1", "..a", "non", "abba", "stanza") == testtools.json_legacy_reply(r, server_type, 6)

    # Test single
    assert r.json().arrlen("doc1", ".nested1.a") == testtools.json_legacy_reply(r, server_type, 6)

    # Test missing key
    assert r.json().arrlen("non_existing_doc", "..a") is None


def test_arrappend(r: redis.Redis, real_server_details: ServerDetails):
    server_type = real_server_details.server_type
    with pytest.raises(Exception) as ctx:
        r.json().arrappend("non-existing-key", Path.root_path(), 2)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    r.json().set("arr", Path.root_path(), [1])
    assert r.json().arrappend("arr", Path.root_path(), 2) == testtools.json_legacy_reply(r, server_type, 2)
    assert r.json().arrappend("arr", Path.root_path(), 3, 4) == testtools.json_legacy_reply(r, server_type, 4)
    assert r.json().arrappend("arr", Path.root_path(), *[5, 6, 7]) == testtools.json_legacy_reply(r, server_type, 7)
    assert r.json().get("arr") == [1, 2, 3, 4, 5, 6, 7]
    r.json().set("doc1", "$", {"a": ["foo"], "nested1": {"a": ["hello", None, "world"]}, "nested2": {"a": 31}})
    # Test multi
    assert r.json().arrappend("doc1", "$..a", "bar", "racuda") == [3, 5, None]
    assert r.json().get("doc1", "$") == [
        {
            "a": ["foo", "bar", "racuda"],
            "nested1": {"a": ["hello", None, "world", "bar", "racuda"]},
            "nested2": {"a": 31},
        }
    ]
    assert r.json().arrappend("doc1", "$.nested1.a", "baz") == [6]

    # Test legacy
    r.json().set("doc1", "$", {"a": ["foo"], "nested1": {"a": ["hello", None, "world"]}, "nested2": {"a": 31}})
    # Test multi (all paths are updated, but return result of last path)
    assert r.json().arrappend("doc1", "..a", "bar", "racuda") == testtools.json_legacy_reply(r, server_type, 5)

    assert r.json().get("doc1", "$") == [
        {
            "a": ["foo", "bar", "racuda"],
            "nested1": {"a": ["hello", None, "world", "bar", "racuda"]},
            "nested2": {"a": 31},
        }
    ]
    # Test single
    assert r.json().arrappend("doc1", ".nested1.a", "baz") == testtools.json_legacy_reply(r, server_type, 6)
    assert r.json().get("doc1", "$") == [
        {
            "a": ["foo", "bar", "racuda"],
            "nested1": {"a": ["hello", None, "world", "bar", "racuda", "baz"]},
            "nested2": {"a": 31},
        }
    ]

    # Test missing key
    with pytest.raises(Exception) as ctx:
        r.json().arrappend("non_existing_doc", "$..a")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_arrindex(r: redis.Redis, real_server_details: ServerDetails):
    server_type = real_server_details.server_type
    r.json().set("foo", Path.root_path(), [0, 1, 2, 3, 4])

    assert r.json().arrindex("foo", Path.root_path(), 1) == testtools.json_legacy_reply(r, server_type, 1)
    assert r.json().arrindex("foo", Path.root_path(), 1, 2) == testtools.json_legacy_reply(r, server_type, -1)

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

    # Dragonfly's JSONPath has no filter expressions, so `[?(...)]` never gets as far as matching.
    if server_type == "dragonfly":
        with pytest.raises((redis.ResponseError, valkey.ResponseError), match="syntax error"):
            r.json().get("store", "$.store.book[?(@.price<10)].size")
    else:
        assert r.json().get("store", "$.store.book[?(@.price<10)].size") == [[10, 20, 30, 40], [5, 10, 20, 30]]
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
            [{"nested41_not_arr": {"arr_renamed": [1, 2, 3]}}, {"nested42_empty_arr": {"arr": []}}],
        ],
    )

    assert r.json().get("test_num", "$..arr") == [
        [0, 1, 3.0, 3, 2, 1, 0, 3],
        [5, 4, 3, 2, 1, 0, 1, 2, 3.0, 2, 4, 5],
        [2, 4, 6],
        "3",
        [],
    ]

    assert r.json().arrindex("test_num", "$..nonexistingpath", 3) == []
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
            [{"nested41_arr": {"arr_renamed": [1, "baz", 3]}}, {"nested42_empty_arr": {"arr": []}}],
        ],
    )
    assert r.json().get("test_string", "$..arr") == [
        ["bazzz", "bar", 2, "baz", 2, "ba", "baz", 3],
        [None, "baz2", "buzz", 2, 1, 0, 1, "2", "baz", 2, 4, 5],
        ["baz2", 4, 6],
        "3",
        [],
    ]

    assert r.json().arrindex("test_string", "$..arr", "baz") == [3, 8, -1, None, -1]

    assert r.json().arrindex("test_string", "$..arr", "baz", 2) == [3, 8, -1, None, -1]
    assert r.json().arrindex("test_string", "$..arr", "baz", 4) == [6, 8, -1, None, -1]
    assert r.json().arrindex("test_string", "$..arr", "baz", -5) == [3, 8, -1, None, -1]
    assert r.json().arrindex("test_string", "$..arr", "baz", 4, 7) == [6, -1, -1, None, -1]
    assert r.json().arrindex("test_string", "$..arr", "baz", 4, -1) == [6, 8, -1, None, -1]
    assert r.json().arrindex("test_string", "$..arr", "baz", 4, 0) == [6, 8, -1, None, -1]
    assert r.json().arrindex("test_string", "$..arr", "5", 7, -1) == [-1, -1, -1, None, -1]
    assert r.json().arrindex("test_string", "$..arr", "5", 7, 0) == [-1, -1, -1, None, -1]

    # Test index of None scalar in multi values
    r.json().set(
        "test_None",
        ".",
        [
            {"arr": ["bazzz", "None", 2, None, 2, "ba", "baz", 3]},
            {"nested1_found": {"arr": ["zaz", "baz2", "buzz", 2, 1, 0, 1, "2", None, 2, 4, 5]}},
            {"nested2_not_found": {"arr": ["None", 4, 6]}},
            {"nested3_scalar": {"arr": None}},
            [{"nested41_arr": {"arr_renamed": [1, None, 3]}}, {"nested42_empty_arr": {"arr": []}}],
        ],
    )
    assert r.json().get("test_None", "$..arr") == [
        ["bazzz", "None", 2, None, 2, "ba", "baz", 3],
        ["zaz", "baz2", "buzz", 2, 1, 0, 1, "2", None, 2, 4, 5],
        ["None", 4, 6],
        None,
        [],
    ]

    # Test with none-scalar value
    # assert r.json().arrindex("test_None", "$..nested42_empty_arr.arr", {"arr": []}) == [-1]

    # Test legacy (path begins with dot)
    # Test index of int scalar in single value
    assert r.json().arrindex("test_num", ".[0].arr", 3) == testtools.json_legacy_reply(r, server_type, 3)
    assert r.json().arrindex("test_num", ".[0].arr", 9) == testtools.json_legacy_reply(r, server_type, -1)

    with pytest.raises(Exception) as ctx:
        r.json().arrindex("test_num", ".[0].arr_not", 3)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    # Test index of string scalar in single value
    assert r.json().arrindex("test_string", ".[0].arr", "baz") == testtools.json_legacy_reply(r, server_type, 3)
    assert r.json().arrindex("test_string", ".[0].arr", "faz") == testtools.json_legacy_reply(r, server_type, -1)
    # Test index of None scalar in single value
    assert r.json().arrindex("test_None", ".[0].arr", "None") == testtools.json_legacy_reply(r, server_type, 1)
    assert r.json().arrindex("test_None", "..nested2_not_found.arr", "None") == testtools.json_legacy_reply(
        r, server_type, 0
    )


def test_arrinsert(r: redis.Redis, real_server_details: ServerDetails):
    server_type = real_server_details.server_type
    r.json().set("arr", Path.root_path(), [0, 4])

    assert r.json().arrinsert("arr", Path.root_path(), 1, *[1, 2, 3]) == testtools.json_legacy_reply(r, server_type, 5)
    assert r.json().get("arr") == [0, 1, 2, 3, 4]

    # test prepends
    r.json().set("val2", Path.root_path(), [5, 6, 7, 8, 9])
    assert r.json().arrinsert("val2", Path.root_path(), 0, ["some", "thing"]) == testtools.json_legacy_reply(
        r, server_type, 6
    )
    assert r.json().get("val2") == [["some", "thing"], 5, 6, 7, 8, 9]
    r.json().set("doc1", "$", {"a": ["foo"], "nested1": {"a": ["hello", None, "world"]}, "nested2": {"a": 31}})
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
    with pytest.raises(Exception) as ctx:
        r.json().arrappend("non_existing_doc", "$..a")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_arrpop(r: redis.Redis, real_server_details: ServerDetails):
    server_type = real_server_details.server_type
    r.json().set("arr", Path.root_path(), [0, 1, 2, 3, 4])
    assert raw_command(r, "json.arrpop", "arr") == testtools.json_legacy_reply(r, server_type, b"4")

    r.json().set("arr", Path.root_path(), [0, 1, 2, 3, 4])
    assert r.json().arrpop("arr", Path.root_path(), 4) == testtools.json_arrpop_reply(r, server_type, 4)
    assert r.json().arrpop("arr", Path.root_path(), -1) == testtools.json_arrpop_reply(r, server_type, 3)
    assert r.json().arrpop("arr", Path.root_path()) == testtools.json_arrpop_reply(r, server_type, 2)
    assert r.json().arrpop("arr", Path.root_path(), 0) == testtools.json_arrpop_reply(r, server_type, 0)
    assert r.json().get("arr") == [1]

    # test out of bounds
    r.json().set("arr", Path.root_path(), [0, 1, 2, 3, 4])
    assert r.json().arrpop("arr", Path.root_path(), 99) == testtools.json_arrpop_reply(r, server_type, 4)

    # none test
    r.json().set("arr", Path.root_path(), [])
    assert r.json().arrpop("arr") is None

    r.json().set("doc1", "$", {"a": ["foo"], "nested1": {"a": ["hello", None, "world"]}, "nested2": {"a": 31}})

    # # Test legacy
    r.json().set("doc1", "$", {"a": ["foo"], "nested1": {"a": ["hello", None, "world"]}, "nested2": {"a": 31}})
    # Test multi (all paths are updated, but return result of last path)
    assert r.json().arrpop("doc1", "..a", "1") == testtools.json_legacy_reply(r, server_type, None)
    assert r.json().get("doc1", "$") == [{"a": [], "nested1": {"a": ["hello", "world"]}, "nested2": {"a": 31}}]

    # # Test missing key
    with pytest.raises(Exception) as ctx:
        r.json().arrpop("non_existing_doc", "..a")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_arrtrim(r: redis.Redis, real_server_details: ServerDetails):
    server_type = real_server_details.server_type
    r.json().set("arr", Path.root_path(), [0, 1, 2, 3, 4])

    assert r.json().arrtrim("arr", Path.root_path(), 1, 3) == testtools.json_legacy_reply(r, server_type, 3)
    assert r.json().get("arr") == [1, 2, 3]

    # <0 test, should be 0 equivalent
    r.json().set("arr", Path.root_path(), [0, 1, 2, 3, 4])
    assert r.json().arrtrim("arr", Path.root_path(), -1, 3) == testtools.json_legacy_reply(r, server_type, 0)

    # testing stop > end
    r.json().set("arr", Path.root_path(), [0, 1, 2, 3, 4])
    assert r.json().arrtrim("arr", Path.root_path(), 3, 99) == testtools.json_legacy_reply(r, server_type, 2)

    # start > array size and stop
    r.json().set("arr", Path.root_path(), [0, 1, 2, 3, 4])
    assert r.json().arrtrim("arr", Path.root_path(), 9, 1) == testtools.json_legacy_reply(r, server_type, 0)

    # all larger
    r.json().set("arr", Path.root_path(), [0, 1, 2, 3, 4])
    assert r.json().arrtrim("arr", Path.root_path(), 9, 11) == testtools.json_legacy_reply(r, server_type, 0)

    r.json().set("doc1", "$", {"a": ["foo"], "nested1": {"a": ["hello", None, "world"]}, "nested2": {"a": 31}})
    # Test multi
    assert r.json().arrtrim("doc1", "$..a", "1", -1) == [0, 2, None]
    assert r.json().get("doc1", "$") == [{"a": [], "nested1": {"a": [None, "world"]}, "nested2": {"a": 31}}]

    r.json().set("doc1", "$", {"a": [], "nested1": {"a": [None, "world"]}, "nested2": {"a": 31}})
    assert r.json().arrtrim("doc1", "$..a", "1", "1") == [0, 1, None]
    assert r.json().get("doc1", "$") == [{"a": [], "nested1": {"a": ["world"]}, "nested2": {"a": 31}}]
    # Test single
    assert r.json().arrtrim("doc1", "$.nested1.a", 1, 0) == [0]
    assert r.json().get("doc1", "$") == [{"a": [], "nested1": {"a": []}, "nested2": {"a": 31}}]

    # Test missing key
    with pytest.raises(Exception) as ctx:
        r.json().arrtrim("non_existing_doc", "..a", "0", 1)

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    # Test legacy
    r.json().set("doc1", "$", {"a": ["foo"], "nested1": {"a": ["hello", None, "world"]}, "nested2": {"a": 31}})

    # Test multi (all paths are updated, but return result of last path)
    assert r.json().arrtrim("doc1", "..a", "1", "-1") == testtools.json_legacy_reply(r, server_type, 2)

    # Test single
    assert r.json().arrtrim("doc1", ".nested1.a", "1", "1") == testtools.json_legacy_reply(r, server_type, 1)
    assert r.json().get("doc1", "$") == [{"a": [], "nested1": {"a": ["world"]}, "nested2": {"a": 31}}]

    # Test missing key
    with pytest.raises(Exception) as ctx:
        r.json().arrtrim("non_existing_doc", "..a", 1, 1)
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
