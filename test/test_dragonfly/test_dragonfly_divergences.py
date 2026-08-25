"""Behaviour where Dragonfly deliberately differs from Redis.

The Redis-flavoured versions of these tests are marked
`@pytest.mark.unsupported_server_types("dragonfly")` in `test/test_mixins`; these are the
Dragonfly counterparts, so both sides of each divergence stay covered.
"""

from __future__ import annotations

import time
import uuid

import pytest

from fakeredis._typing import ClientType
from test import testtools
from test.testtools import raw_command, resp_conversion

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


def test_at_least_one_key_is_needed_for_numkeys_commands(r: ClientType):
    r.sadd("s", "m")
    r.zadd("z", {"m": 1.0})
    for args in (
        ("sintercard", 0, "s"),
        ("zintercard", 0, "z"),
        ("zunion", 0, "z"),
        ("zunionstore", "dst", 0, "z"),
    ):
        _raises(r, "at least 1 input key is needed for this command", *args)
    # Dragonfly reads numkeys as unsigned, so a negative one never decodes.
    for args in (("sintercard", -1, "s"), ("zintercard", -1, "z")):
        _raises(r, "value is not an integer or out of range", *args)


def test_xinfo_groups_reports_unknown_lag_as_nil(r: ClientType):
    # Dragonfly uses -1 as its "lag unknown" sentinel and reports it as nil.
    message_id = r.xadd("stream", {"foo": "bar"})
    r.xgroup_create("stream", "group", 0)
    r.xgroup_setid("stream", "group", message_id, entries_read=2)
    assert r.xinfo_groups("stream")[0]["lag"] is None
    # A lag it can work out is reported as usual, negative ones included.
    r.xgroup_setid("stream", "group", message_id, entries_read=5)
    assert r.xinfo_groups("stream")[0]["lag"] == -4


def test_xinfo_stream_reports_the_entries_of_an_empty_stream_as_a_null_array(r: ClientType):
    # Redis sends nil, which RESP3 renders as nil; dragonfly keeps sending the RESP2 null
    # array, so a RESP3 client reads it back as an empty array.
    r.xadd("stream", {"foo": "bar"})
    r.xtrim("stream", maxlen=0)
    info = testtools.xinfo_stream_raw(r, "stream")
    empty = testtools.null_array_reply(r, "dragonfly")
    assert info["first-entry"] == empty
    assert info["last-entry"] == empty


def test_xpending_looks_the_key_up_before_the_group(r: ClientType):
    # Redis reports both possibilities in one NOGROUP error; dragonfly checks the key
    # first, and only names the group once the key exists.
    _raises(r, "no such key", "xpending", "nosuchstream", "group")
    r.xadd("stream", {"foo": "bar"})
    err = _raises(r, "NOGROUP", "xpending", "stream", "group")
    assert str(err) == "NOGROUP No such consumer group 'group' for key name 'stream'"


def test_zpopmin_returns_an_array_of_pairs_under_resp3(r: ClientType):
    # Redis answers a countless ZPOPMIN/ZPOPMAX with a flat member/score pair under RESP3;
    # dragonfly wraps it in an array, exactly as it does for the counted form.
    r.zadd("z", {"a": 1.0, "b": 2.0})
    expected = resp_conversion(r, [[b"a", 1.0]], [b"a", b"1"])
    assert raw_command(r, "zpopmin", "z") == expected
    assert raw_command(r, "zpopmax", "z") == resp_conversion(r, [[b"b", 2.0]], [b"b", b"2"])


def test_zpopmin_on_a_missing_key_is_still_an_empty_array(r: ClientType):
    assert raw_command(r, "zpopmin", "nosuchkey") == []


def test_zunion_and_zinter_keep_the_flat_withscores_shape(r: ClientType):
    # Under RESP3 redis pairs each member with its score; dragonfly keeps the RESP2 shape
    # for these two, though not for ZDIFF.
    r.zadd("a", {"m": 1.0})
    r.zadd("b", {"m": 2.0})
    for command in ("zunion", "zinter"):
        assert raw_command(r, command, 2, "a", "b", "withscores") == resp_conversion(r, [b"m", 3.0], [b"m", b"3"])
    assert raw_command(r, "zdiff", 2, "a", "nosuchkey", "withscores") == resp_conversion(r, [[b"m", 1.0]], [b"m", b"1"])


def test_zdiff_only_accepts_sorted_sets(r: ClientType):
    # Redis reads a plain set as a sorted set scoring every member 1; so does dragonfly,
    # except here.
    r.sadd("s", "m")
    r.zadd("z", {"m": 1.0})
    _raises(r, "WRONGTYPE", "zdiff", 2, "s", "z")
    _raises(r, "WRONGTYPE", "zdiff", 2, "z", "s")
    _raises(r, "WRONGTYPE", "zdiffstore", "dst", 2, "z", "s")
    # The other set operations do take it.
    assert raw_command(r, "zinterstore", "dst", 2, "s", "z") == 1
    assert raw_command(r, "zunionstore", "dst", 2, "s", "z") == 1
    assert raw_command(r, "zintercard", 2, "s", "z") == 1


def test_smove_checks_the_destination_type_even_when_the_source_is_missing(r: ClientType):
    r.set("str", "x")
    _raises(r, "WRONGTYPE", "smove", "nosuchkey", "str", "m")
    # With both keys missing there is nothing to check, and the answer is 0.
    assert r.smove("nosuchkey", "alsomissing", "m") is False


def test_a_string_is_capped_at_256mb(r: ClientType):
    # Redis allows 512MB, and words the refusal with a "(proto-max-bulk-len)" suffix.
    max_size = 2**28
    _raises(r, "string exceeds maximum allowed size", "setrange", "foo", max_size - 1, "ab")
    assert raw_command(r, "setrange", "foo", max_size - 2, "ab") == max_size
    r.delete("foo")
    # The same cap bounds SETBIT's offset.
    _raises(r, "bit offset is not an integer or out of range", "setbit", "foo", 8 * max_size, 1)
    assert raw_command(r, "setbit", "foo", 8 * max_size - 1, 1) == 0
