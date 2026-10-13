import importlib.util

import pytest
import redis

from fakeredis._typing import ClientType
from fakeredis.commands_mixins import string_mixin
from test.testtools import raw_command

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.supported_server_versions(min_redis_ver="8.4"),
        pytest.mark.unsupported_server_types("valkey", "dragonfly"),
    ]
)

run_test_if_xxhash = pytest.mark.skipif(
    importlib.util.find_spec("xxhash") is None, reason="Test is only applicable if xxhash is installed"
)

HELLO_DIGEST = b"9555e8555c62dcfd"


@run_test_if_xxhash
@pytest.mark.parametrize(
    "value,expected",
    [
        (b"hello", HELLO_DIGEST),
        (b"", b"2d06800538d394c2"),
        (b"123", b"404a763b3f4c8c9a"),
        (b"v8", b"0cc76dbb41381419"),  # leading zero is kept
    ],
)
def test_digest(r: ClientType, value: bytes, expected: bytes):
    r.set("foo", value)
    assert raw_command(r, "DIGEST", "foo") == expected


def test_digest_missing_key(r: ClientType):
    assert raw_command(r, "DIGEST", "foo") is None


def test_digest_wrong_type(r: ClientType):
    r.rpush("foo", "a")
    with pytest.raises(redis.ResponseError, match="WRONGTYPE"):
        raw_command(r, "DIGEST", "foo")


def test_digest_wrong_number_of_args(r: ClientType):
    with pytest.raises(redis.ResponseError, match="wrong number of arguments for 'digest' command"):
        raw_command(r, "DIGEST")
    with pytest.raises(redis.ResponseError, match="wrong number of arguments for 'digest' command"):
        raw_command(r, "DIGEST", "foo", "bar")


def test_delex_no_condition(r: ClientType):
    assert raw_command(r, "DELEX", "foo") == 0
    r.set("foo", "hello")
    assert raw_command(r, "DELEX", "foo") == 1
    assert r.exists("foo") == 0
    r.rpush("foo", "a")
    assert raw_command(r, "DELEX", "foo") == 1
    assert r.exists("foo") == 0


@pytest.mark.parametrize("condition", ["IFEQ", "IFNE", "IFDEQ", "IFDNE", "FOO"])
def test_delex_missing_key(r: ClientType, condition: str):
    assert raw_command(r, "DELEX", "foo", condition, "bar") == 0


def test_delex_ifeq(r: ClientType):
    r.set("foo", "hello")
    assert raw_command(r, "DELEX", "foo", "IFEQ", "other") == 0
    assert r.get("foo") == b"hello"
    assert raw_command(r, "DELEX", "foo", "ifeq", "hello") == 1
    assert r.exists("foo") == 0


def test_delex_ifne(r: ClientType):
    r.set("foo", "hello")
    assert raw_command(r, "DELEX", "foo", "IFNE", "hello") == 0
    assert r.get("foo") == b"hello"
    assert raw_command(r, "DELEX", "foo", "IfNe", "other") == 1
    assert r.exists("foo") == 0


def test_delex_ifeq_compares_bytes_not_numbers(r: ClientType):
    r.set("foo", "0123")
    assert raw_command(r, "DELEX", "foo", "IFEQ", "123") == 0
    assert raw_command(r, "DELEX", "foo", "IFNE", "123") == 1


@run_test_if_xxhash
def test_delex_ifdeq(r: ClientType):
    r.set("foo", "hello")
    assert raw_command(r, "DELEX", "foo", "IFDEQ", "0" * 16) == 0
    assert r.get("foo") == b"hello"
    assert raw_command(r, "DELEX", "foo", "IFDEQ", raw_command(r, "DIGEST", "foo")) == 1
    assert r.exists("foo") == 0


@run_test_if_xxhash
def test_delex_ifdne(r: ClientType):
    r.set("foo", "hello")
    assert raw_command(r, "DELEX", "foo", "IFDNE", HELLO_DIGEST) == 0
    assert r.get("foo") == b"hello"
    assert raw_command(r, "DELEX", "foo", "IFDNE", "0" * 16) == 1
    assert r.exists("foo") == 0


@run_test_if_xxhash
def test_delex_digest_is_case_insensitive(r: ClientType):
    r.set("foo", "hello")
    assert raw_command(r, "DELEX", "foo", "IFDNE", HELLO_DIGEST.upper()) == 0
    assert raw_command(r, "DELEX", "foo", "IFDEQ", HELLO_DIGEST.upper()) == 1


@run_test_if_xxhash
def test_delex_digest_only_length_is_validated(r: ClientType):
    r.set("foo", "hello")
    assert raw_command(r, "DELEX", "foo", "IFDEQ", "z" * 16) == 0
    assert raw_command(r, "DELEX", "foo", "IFDNE", "z" * 16) == 1


@pytest.mark.parametrize("condition", ["IFDEQ", "IFDNE"])
@pytest.mark.parametrize("digest", [b"", b"0123", HELLO_DIGEST[1:], b"0" + HELLO_DIGEST])
def test_delex_digest_wrong_length(r: ClientType, condition: str, digest: bytes):
    r.set("foo", "hello")
    with pytest.raises(redis.ResponseError, match="must be exactly 16 hexadecimal characters"):
        raw_command(r, "DELEX", "foo", condition, digest)
    assert r.get("foo") == b"hello"


@pytest.mark.parametrize("condition", ["IFEQ", "IFNE", "IFDEQ", "IFDNE", "FOO"])
def test_delex_condition_on_wrong_type(r: ClientType, condition: str):
    r.rpush("foo", "a")
    with pytest.raises(redis.ResponseError, match="Key should be of string type if conditions are specified"):
        raw_command(r, "DELEX", "foo", condition, "a")
    assert r.exists("foo") == 1


def test_delex_invalid_condition(r: ClientType):
    r.set("foo", "hello")
    with pytest.raises(redis.ResponseError, match="Invalid condition. Use IFEQ, IFNE, IFDEQ, or IFDNE"):
        raw_command(r, "DELEX", "foo", "FOO", "hello")
    assert r.get("foo") == b"hello"


@pytest.mark.parametrize("args", [("IFEQ",), ("IFEQ", "hello", "extra")])
def test_delex_wrong_number_of_args(r: ClientType, args: tuple):
    r.set("foo", "hello")
    with pytest.raises(redis.ResponseError, match="wrong number of arguments for 'delex' command"):
        raw_command(r, "DELEX", "foo", *args)
    with pytest.raises(redis.ResponseError, match="wrong number of arguments for 'delex' command"):
        raw_command(r, "DELEX", "missing", *args)


def test_delex_invalidates_watch(r: ClientType):
    r.set("foo", "hello")
    with r.pipeline() as p:
        p.watch("foo")
        assert raw_command(r, "DELEX", "foo", "IFEQ", "hello") == 1
        p.multi()
        p.set("bar", "baz")
        with pytest.raises(redis.WatchError):
            p.execute()


@pytest.mark.fake_only
def test_digest_without_xxhash(r: ClientType, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(string_mixin, "xxhash", None)
    r.set("foo", "hello")
    assert raw_command(r, "DIGEST", "missing") is None
    with pytest.raises(redis.ResponseError, match=r"fakeredis\[digest\]"):
        raw_command(r, "DIGEST", "foo")
    with pytest.raises(redis.ResponseError, match=r"fakeredis\[digest\]"):
        raw_command(r, "DELEX", "foo", "IFDEQ", HELLO_DIGEST)
    # Conditions that need no digest keep working
    assert raw_command(r, "DELEX", "foo", "IFEQ", "hello") == 1
