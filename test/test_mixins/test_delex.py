"""DELEX: Redis 8.4 and Valkey 9.2.

Valkey takes only IFEQ/IFNE and requires one; Redis also has the digest conditions (see
`test_specific_redis_versions/test_redis_8_4_digest_delex.py`) and DELEX with no condition.
"""

import pytest
import redis
import valkey

from fakeredis._typing import ClientType
from test.conftest import ServerDetails
from test.testtools import RESPONSE_ERRORS, raw_command

pytestmark = [
    pytest.mark.supported_server_versions(min_redis_ver="8.4", min_valkey_ver="9.2"),
    pytest.mark.unsupported_server_types("dragonfly"),
]


def _valkey(details: ServerDetails) -> bool:
    return details.server_type == "valkey"


def test_delex_no_condition(r: ClientType, real_server_details: ServerDetails):
    if _valkey(real_server_details):
        # Valkey requires a condition.
        r.set("foo", "hello")
        with pytest.raises(RESPONSE_ERRORS, match="wrong number of arguments for 'delex' command"):
            raw_command(r, "DELEX", "foo")
        assert r.get("foo") == b"hello"
        return
    assert raw_command(r, "DELEX", "foo") == 0
    r.set("foo", "hello")
    assert raw_command(r, "DELEX", "foo") == 1
    assert r.exists("foo") == 0
    r.rpush("foo", "a")
    assert raw_command(r, "DELEX", "foo") == 1
    assert r.exists("foo") == 0


@pytest.mark.parametrize("condition", ["IFEQ", "IFNE", "IFDEQ", "IFDNE", "FOO"])
def test_delex_missing_key(r: ClientType, real_server_details: ServerDetails, condition: str):
    if _valkey(real_server_details) and condition not in ("IFEQ", "IFNE"):
        # Valkey parses the condition before looking the key up.
        with pytest.raises(RESPONSE_ERRORS, match="syntax error"):
            raw_command(r, "DELEX", "foo", condition, "bar")
        return
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


@pytest.mark.parametrize("condition", ["IFEQ", "IFNE", "IFDEQ", "IFDNE", "FOO"])
def test_delex_condition_on_wrong_type(r: ClientType, real_server_details: ServerDetails, condition: str):
    r.rpush("foo", "a")
    if not _valkey(real_server_details):
        error = "Key should be of string type if conditions are specified"
    else:
        error = "WRONGTYPE" if condition in ("IFEQ", "IFNE") else "syntax error"
    with pytest.raises(RESPONSE_ERRORS, match=error):
        raw_command(r, "DELEX", "foo", condition, "a")
    assert r.exists("foo") == 1


def test_delex_invalid_condition(r: ClientType, real_server_details: ServerDetails):
    r.set("foo", "hello")
    error = "syntax error" if _valkey(real_server_details) else "Invalid condition. Use IFEQ, IFNE, IFDEQ, or IFDNE"
    with pytest.raises(RESPONSE_ERRORS, match=error):
        raw_command(r, "DELEX", "foo", "FOO", "hello")
    assert r.get("foo") == b"hello"


@pytest.mark.parametrize("args", [("IFEQ",), ("IFEQ", "hello", "extra")])
def test_delex_wrong_number_of_args(r: ClientType, args: tuple):
    r.set("foo", "hello")
    with pytest.raises(RESPONSE_ERRORS, match="wrong number of arguments for 'delex' command"):
        raw_command(r, "DELEX", "foo", *args)
    with pytest.raises(RESPONSE_ERRORS, match="wrong number of arguments for 'delex' command"):
        raw_command(r, "DELEX", "missing", *args)


def test_delex_invalidates_watch(r: ClientType):
    r.set("foo", "hello")
    with r.pipeline() as p:
        p.watch("foo")
        assert raw_command(r, "DELEX", "foo", "IFEQ", "hello") == 1
        p.multi()
        p.set("bar", "baz")
        with pytest.raises((redis.WatchError, valkey.WatchError)):
            p.execute()
