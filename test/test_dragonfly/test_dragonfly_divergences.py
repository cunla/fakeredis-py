"""Behaviour where Dragonfly deliberately differs from Redis.

The Redis-flavoured versions of these tests are marked
`@pytest.mark.unsupported_server_types("dragonfly")` in `test/test_mixins`; these are the
Dragonfly counterparts, so both sides of each divergence stay covered.
"""

from __future__ import annotations

import time
import uuid

import pytest
import redis

from fakeredis._typing import ClientType
from test.testtools import raw_command

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("redis", "valkey"),
    ]
)

RESPONSE_ERRORS = ("redis.exceptions.ResponseError", "valkey.exceptions.ResponseError")


def _raises(r: ClientType, match: str, *args):
    with pytest.raises(Exception, match=match) as ctx:
        raw_command(r, *args)
    assert type(ctx.value).__module__ + "." + type(ctx.value).__qualname__ in RESPONSE_ERRORS
    return ctx.value


def test_unknown_command_message_format(r: ClientType):
    # Dragonfly names the command in backticks and uppercase, and does not echo the args.
    err = _raises(r, "unknown command", "nosuchcmd", "a", "b")
    assert str(err) == "unknown command `NOSUCHCMD`"


def test_lcs_is_not_supported(r: ClientType):
    r.mset({"key1": "ohmytext", "key2": "mynewtext"})
    err = _raises(r, "unknown command", "lcs", "key1", "key2")
    assert str(err) == "unknown command `LCS`"


@pytest.mark.parametrize("subcommand", ["SHARDCHANNELS", "SHARDNUMSUB"])
def test_pubsub_shard_introspection_needs_cluster_mode(r: ClientType, subcommand: str):
    _raises(r, f"PUBSUB {subcommand} is not supported in non cluster mode", "PUBSUB", subcommand)


def test_spublish_and_ssubscribe_still_work(r: ClientType):
    # Only the introspection subcommands are refused; sharded publishing itself works.
    assert raw_command(r, "SPUBLISH", "chan", "msg") == 0


def test_copy_has_no_db_option(r: ClientType):
    r.set("src", "val")
    for db in ("0", "1", "-1", "not-a-db"):
        _raises(r, "syntax error", "COPY", "src", "dst", "DB", db)
    # ...but a plain COPY works, and carries the TTL over.
    r.expire("src", 100)
    assert r.copy("src", "dst") is True
    assert r.get("dst") == b"val"
    assert 0 < r.ttl("dst") <= 100


def test_absolute_expiry_beyond_horizon_is_rejected(r: ClientType):
    # Dragonfly refuses a deadline more than 2**28-1 seconds away.
    horizon = 2**28 - 1
    r.set("foo", "bar")
    _raises(r, "expiry is out of range", "EXPIREAT", "foo", int(time.time()) + horizon + 60)
    _raises(r, "expiry is out of range", "PEXPIREAT", "foo", (int(time.time()) + horizon + 60) * 1000)
    assert r.expireat("foo", int(time.time()) + horizon - 60) is True


def test_relative_expiry_is_clamped_to_horizon(r: ClientType):
    # A relative expiry past the horizon is accepted and silently clamped instead.
    horizon = 2**28 - 1
    r.set("foo", "bar")
    assert r.expire("foo", horizon + 10_000) is True
    assert r.ttl("foo") == horizon


def test_expire_accepts_nx_with_gt_or_lt(r: ClientType):
    # Redis rejects these combinations; dragonfly only refuses NX+XX and GT+LT.
    r.set("foo", "bar")
    raw_command(r, "EXPIRE", "foo", 100, "NX", "GT")
    raw_command(r, "EXPIRE", "foo", 100, "NX", "LT")
    _raises(r, "NX and XX options at the same time are not compatible", "EXPIRE", "foo", 100, "NX", "XX")
    _raises(r, "GT and LT options at the same time are not compatible", "EXPIRE", "foo", 100, "GT", "LT")
    _raises(r, "Unsupported option: BOGUS", "EXPIRE", "foo", 100, "BOGUS")


def test_sort_has_no_hash_field_patterns(r: ClientType):
    # "record_*->age" is taken as a literal key name rather than a hash field reference.
    r.rpush("foo", "middle", "eldest", "youngest")
    for name, age in (("youngest", 1), ("middle", 10), ("eldest", 20)):
        r.hset(f"record_{name}", "age", age)
    assert r.sort("foo", by="record_*->age") == [b"middle", b"eldest", b"youngest"]
    assert r.sort("foo", by="record_*->age", get="record_*->name") == [b"", b"", b""]


def test_sort_by_nosort_ignores_desc(r: ClientType):
    natural = [b"3", b"1", b"2", b"5", b"4"]
    r.rpush("mylist", *natural)
    assert r.sort("mylist", by="nosort") == natural
    assert r.sort("mylist", by="nosort", desc=True) == natural


def test_sort_get_pattern_without_star_is_a_literal_key(r: ClientType):
    r.rpush("mylist", "a", "b")
    r.set("lit", "LITVAL")
    assert r.sort("mylist", by="nosort", get="lit") == [b"LITVAL", b"LITVAL"]
    # An unresolvable GET yields an empty string rather than nil.
    assert r.sort("mylist", by="nosort", get="missing_*") == [b"", b""]


def test_sort_leaves_equal_weights_in_place(r: ClientType):
    # Redis breaks ties on the element itself; dragonfly sorts on the weight alone.
    r.rpush("l", "zebra", "apple", "mango")
    for element in ("zebra", "apple", "mango"):
        r.set(f"w_{element}", "5")
    assert r.sort("l", by="w_*") == [b"zebra", b"apple", b"mango"]


def test_setbit_dirties_a_watched_key_even_when_unchanged(r: ClientType):
    r.set("foo", b"0")
    with r.pipeline() as p:
        p.watch("foo")
        assert r.setbit("foo", 0, 0) == 0
        p.multi()
        with pytest.raises(redis.WatchError):
            p.execute()


def test_sunsubscribe_is_confirmed_as_unsubscribe(r: ClientType):
    # A unique channel: dragonfly's "unsubscribe" reply leaves redis-py's shard_channels
    # set populated, so closing the pubsub does not reliably drop the server-side
    # subscription and a shared name would leak into other tests.
    channel = f"shard-{uuid.uuid4().hex}"
    p = r.pubsub()
    try:
        p.ssubscribe(channel)
        assert p.get_message(timeout=2)["type"] == "ssubscribe"
        p.sunsubscribe()
        # Dragonfly answers with "unsubscribe", not "sunsubscribe".
        assert p.get_message(timeout=2)["type"] == "unsubscribe"
    finally:
        p.close()


def test_pubsub_help_text(r: ClientType):
    assert raw_command(r, "PUBSUB", "HELP") == [
        b"PUBSUB <subcommand> [<arg> [value] [opt] ...]. Subcommands are:",
        b"CHANNELS [<pattern>]",
        b"\tReturn the currently active channels matching a <pattern> (default: '*').",
        b"NUMPAT",
        b"\tReturn number of subscriptions to patterns.",
        b"NUMSUB [<channel> <channel...>]",
        b"\tReturns the number of subscribers for the specified channels, excluding",
        b"\tpattern subscriptions.",
        b"SHARDCHANNELS [pattern]",
        b"\tReturns a list of active shard channels, optionally matching the specified pattern ",
        b"(default: '*').",
        b"SHARDNUMSUB [<channel> <channel...>]",
        b"\tReturns the number of subscribers for the specified shard channels, excluding",
        b"\tpattern subscriptions.",
        b"HELP",
        b"\tPrints this help.",
    ]


def test_shard_and_plain_channels_share_one_namespace(r: ClientType):
    # Outside cluster mode dragonfly has a single channel namespace: SPUBLISH reaches a
    # plain subscriber and PUBLISH reaches a sharded one. Only the message type differs.
    channel = f"chan-{uuid.uuid4().hex}"
    plain, shard = r.pubsub(), r.pubsub()
    try:
        plain.subscribe(channel)
        assert plain.get_message(timeout=2)["type"] == "subscribe"
        shard.ssubscribe(channel)
        assert shard.get_message(timeout=2)["type"] == "ssubscribe"

        assert r.spublish(channel, "via-spublish") == 2
        for p in (plain, shard):
            msg = p.get_message(timeout=2)
            assert (msg["type"], msg["data"]) == ("smessage", b"via-spublish")

        assert r.publish(channel, "via-publish") == 2
        for p in (plain, shard):
            msg = p.get_message(timeout=2)
            assert (msg["type"], msg["data"]) == ("message", b"via-publish")
    finally:
        plain.close()
        shard.close()
