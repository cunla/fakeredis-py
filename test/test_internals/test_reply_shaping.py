"""Replies are checked, converted and decoded element by element, with a shortcut for the plain elements that make up
most of them. These check that the shortcut does not change what comes out for the elements that are not plain."""

import pytest

import fakeredis
from fakeredis._helpers import OK, NoResponse, SimpleError
from fakeredis._socket._resp import convert_to_resp2, valid_response_type

pytestmark = [pytest.mark.fake]


def test_convert_to_resp2_converts_what_is_nested_between_plain_elements():
    reply = [b"a", 1, None, 1.5, "text", [b"b", 2.0, {"k": 3.25}], (b"c", True), {b"m": [0.5]}, OK]
    assert convert_to_resp2(reply) == [
        b"a",
        1,
        None,
        b"1.5",
        b"text",
        [b"b", b"2", [b"k", b"3.25"]],
        [b"c", True],
        [b"m", [b"0.5"]],
        OK,
    ]
    assert convert_to_resp2({b"k": 1.5, b"n": 2}) == [b"k", b"1.5", b"n", 2]
    assert convert_to_resp2([1.5, [2.5]], keep_doubles=True) == [1.5, [2.5]]


@pytest.mark.parametrize(
    "reply,resp2,resp3",
    [
        ([b"a", 1, None, [b"b", [2, None]]], True, True),
        ([b"a", OK, SimpleError("ERR x"), 1.5, True], True, True),
        ([b"a", "text"], False, True),
        ([b"a", [b"b", ["text"]]], False, True),
        ([b"a", {b"k": 1}], False, True),
        ([b"a", (b"b",)], False, False),
        ([b"a", [b"b", {1, 2}]], False, False),
        ([b"a", NoResponse()], False, False),
        (NoResponse(), True, True),
    ],
)
def test_valid_response_type(reply, resp2, resp3):
    assert valid_response_type(reply, 2) is resp2
    assert valid_response_type(reply, 3) is resp3


@pytest.mark.parametrize("protocol", [2, 3])
@pytest.mark.parametrize("decode_responses", [False, True])
def test_nested_replies_reach_the_client_intact(protocol: int, decode_responses: bool):
    r = fakeredis.FakeRedis(
        server=fakeredis.FakeServer(version=(8,)), protocol=protocol, decode_responses=decode_responses
    )

    def text(value: bytes):
        return value.decode() if decode_responses else value

    r.rpush("l", "a", "b")
    r.set("s", "v")
    assert r.lrange("l", 0, -1) == [text(b"a"), text(b"b")]
    assert r.mget("s", "missing", "s") == [text(b"v"), None, text(b"v")]
    # Status and error replies nested in an array, next to plain elements
    pipe = r.pipeline()
    pipe.set("s", "w")
    pipe.lpush("s", "x")
    pipe.get("s")
    pipe.lrange("l", 0, -1)
    ok, error, value, items = pipe.execute(raise_on_error=False)
    assert ok is True
    assert isinstance(error, Exception)
    assert value == text(b"w")
    assert items == [text(b"a"), text(b"b")]
    assert r.eval("return {1, 'two', {3, {'four', false}}, {ok='fine'}}", 0) == [
        1,
        text(b"two"),
        [3, [text(b"four"), None]],
        text(b"fine"),
    ]


def test_reply_lists_are_not_shared_with_the_stored_value():
    r = fakeredis.FakeRedis(server=fakeredis.FakeServer(version=(8,)))
    r.rpush("l", "a", "b")
    reply = r.execute_command("LRANGE", "l", 0, -1)
    reply.append(b"c")
    assert r.lrange("l", 0, -1) == [b"a", b"b"]
