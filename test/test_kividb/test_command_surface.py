"""The commands KiviDB has, and the ones it does not.

KiviDB reports `redis_version:7.0.15` but its command surface is not Redis 7.0's: it ships the
hash-field TTL family (Redis 7.4), `INCREX` and the `XDELEX`/`XACKDEL`/`XNACK` family (Redis 8.8),
and lacks `UNLINK` and `SCRIPT HELP`, which Redis has had since 4.0 and 5.0. Support is therefore
keyed off the server type rather than off the version it claims.
"""

from __future__ import annotations

import pytest
import redis

import fakeredis
from fakeredis._typing import ClientType
from test.testtools import raw_command

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("redis", "valkey", "dragonfly"),
    ]
)


def test_lcs(r: ClientType):
    r.set("key1", "ohmytext")
    r.set("key2", "mynewtext")
    assert raw_command(r, "lcs", "key1", "key2") == b"mytext"


def test_hash_field_expiry_commands(r: ClientType):
    r.hset("h", mapping={"f1": "v1", "f2": "v2"})
    assert raw_command(r, "hexpire", "h", 100, "fields", 1, "f1") == [1]
    ttls = raw_command(r, "httl", "h", "fields", 2, "f1", "f2")
    assert ttls[0] in (99, 100) and ttls[1] == -1
    assert raw_command(r, "hpttl", "h", "fields", 1, "f1")[0] > 99000
    assert raw_command(r, "hexpiretime", "h", "fields", 1, "f2") == [-1]
    assert raw_command(r, "hpexpiretime", "h", "fields", 1, "f2") == [-1]
    assert raw_command(r, "hgetex", "h", "fields", 1, "f2") == [b"v2"]
    assert raw_command(r, "hgetdel", "h", "fields", 1, "f2") == [b"v2"]
    assert r.hget("h", "f2") is None


def test_increx(r: ClientType):
    assert raw_command(r, "increx", "counter") == [1, 1]
    assert raw_command(r, "increx", "counter", "ex", 100) == [2, 1]
    assert r.ttl("counter") == 100


def test_xdelex(r: ClientType):
    entry_id = r.xadd("stream", {"f": "v"})
    assert raw_command(r, "xdelex", "stream", "ids", 1, entry_id) == [1]
    assert raw_command(r, "xdelex", "stream", "keepref", "ids", 1, entry_id) == [-1]


def test_xnack(r: ClientType):
    entry_id = r.xadd("stream", {"f": "v"})
    r.xgroup_create("stream", "group", id="0")
    r.xreadgroup("group", "consumer", {"stream": ">"})
    assert raw_command(r, "xnack", "stream", "group", "fail", "ids", 1, entry_id) == 1


def test_no_unlink(r: ClientType):
    r.set("key", "value")
    with pytest.raises(redis.ResponseError, match="unknown command"):
        raw_command(r, "unlink", "key")
    assert r.get("key") == b"value"


def test_no_script_help(r: ClientType):
    with pytest.raises(redis.ResponseError, match="unknown subcommand 'help' for SCRIPT"):
        raw_command(r, "script", "help")


def test_unknown_command_names_nothing(r: ClientType):
    """Redis echoes the command and its arguments back; KiviDB reports neither."""
    with pytest.raises(redis.ResponseError) as ctx:
        raw_command(r, "nosuchcommand", "key", "value")
    assert str(ctx.value) == "unknown command"


@pytest.mark.fake
@pytest.mark.parametrize(
    "args",
    [
        # KiviDB takes `HSETEX key seconds FIELDS numfields field value`, not Redis' FVS form.
        ("hsetex", "h", 100, "fields", 1, "f", "v"),
        # KiviDB's XACKDEL is shaped like XACK: `XACKDEL key group id [id ...]`.
        ("xackdel", "stream", "group", "ids", 1, "1-1"),
    ],
)
def test_commands_kividb_spells_differently_are_refused(args):
    """Both commands exist on KiviDB, in an argument form fakeredis does not implement.

    Refusing them keeps a script that uses the Redis form from passing here and failing against a
    real KiviDB; emulating KiviDB's own form would be the better answer.
    """
    r = fakeredis.FakeStrictRedis(server_type="kividb")
    with pytest.raises(redis.ResponseError, match="unknown command"):
        raw_command(r, *args)
