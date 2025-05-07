import pytest
import redis
import redis.client

from test import testtools
from test.test_mixins.test_streams_commands import get_stream_message
from test.testtools import raw_command


@pytest.mark.max_server("6.2.7")
def test_bitcount_mode_redis6(r: redis.Redis):
    r.set("key", "foobar")
    with pytest.raises(redis.ResponseError):
        r.bitcount("key", start=1, end=1, mode="byte")
    with pytest.raises(redis.ResponseError):
        r.bitcount("key", start=1, end=1, mode="bit")
    with pytest.raises(redis.ResponseError):
        raw_command(r, "bitcount", "key", "1", "2", "dsd", "cd")


@pytest.mark.max_server("6.2.7")
def test_bitops_mode_redis6(r: redis.Redis):
    key = "key:bitpos"
    r.set(key, b"\xff\xf0\x00")
    with pytest.raises(redis.ResponseError):
        assert r.bitpos(key, 0, 8, -1, "bit") == 12


@pytest.mark.max_server("7.2")
def test_bitcount_error_v6(r: redis.Redis):
    r = raw_command(r, b"BITCOUNT", b"", b"", b"")
    assert r == 0


@pytest.mark.max_server("6.2.7")
def test_pubsub_help_redis6(r: redis.Redis):
    assert testtools.raw_command(r, "PUBSUB HELP") == [
        b"PUBSUB <subcommand> [<arg> [value] [opt] ...]. Subcommands are:",
        b"CHANNELS [<pattern>]",
        b"    Return the currently active channels matching a <pattern> (default: '*').",
        b"NUMPAT",
        b"    Return number of subscriptions to patterns.",
        b"NUMSUB [<channel> ...]",
        b"    Return the number of subscribers for the specified channels, excluding",
        b"    pattern subscriptions(default: no channels).",
        b"HELP",
        b"    Prints this help.",
    ]


@pytest.mark.max_server("6.2.7")
def test_script_exists_redis6(r: redis.Redis):
    # test response for no arguments by bypassing the py-redis command
    # as it requires at least one argument
    assert raw_command(r, "SCRIPT EXISTS") == []

    # use single character characters for non-existing scripts, as those
    # will never be equal to an actual sha1 hash digest
    assert r.script_exists("a") == [0]
    assert r.script_exists("a", "b", "c", "d", "e", "f") == [0, 0, 0, 0, 0, 0]

    sha1_one = r.script_load("return 'a'")
    assert r.script_exists(sha1_one) == [1]
    assert r.script_exists(sha1_one, "a") == [1, 0]
    assert r.script_exists("a", "b", "c", sha1_one, "e") == [0, 0, 0, 1, 0]

    sha1_two = r.script_load("return 'b'")
    assert r.script_exists(sha1_one, sha1_two) == [1, 1]
    assert r.script_exists("a", sha1_one, "c", sha1_two, "e", "f") == [0, 1, 0, 1, 0, 0]


@pytest.mark.max_server("6.3")
@testtools.run_test_if_redispy_ver("gte", "4.4")
def test_xautoclaim_redis6(r: redis.Redis):
    stream, group, consumer1, consumer2 = "stream", "group", "consumer1", "consumer2"

    message_id1 = r.xadd(stream, {"john": "wick"})
    message_id2 = r.xadd(stream, {"johny": "deff"})
    message = get_stream_message(r, stream, message_id1)
    r.xgroup_create(stream, group, 0)

    # trying to claim a message that isn't already pending doesn't
    # do anything
    assert r.xautoclaim(stream, group, consumer2, min_idle_time=0) == [b"0-0", []]

    # read the group as consumer1 to initially claim the messages
    r.xreadgroup(group, consumer1, streams={stream: ">"})

    # claim one message as consumer2
    response = r.xautoclaim(stream, group, consumer2, min_idle_time=0, count=1)
    assert response[1] == [message]

    # reclaim the messages as consumer1, but use the justid argument
    # which only returns message ids
    assert r.xautoclaim(stream, group, consumer1, min_idle_time=0, start_id=0, justid=True) == [
        message_id1,
        message_id2,
    ]
    assert r.xautoclaim(stream, group, consumer1, min_idle_time=0, start_id=message_id2, justid=True) == [message_id2]


@pytest.mark.min_server("6.2")
@pytest.mark.max_server("6.2.7")
def test_set_get_nx_redis6(r: redis.Redis):
    # Note: this will most likely fail on a 7.0 server, based on the docs for SET
    with pytest.raises(redis.ResponseError):
        raw_command(r, "set", "foo", "bar", "NX", "GET")


@pytest.mark.max_server("6.2.7")
def test_zadd_minus_zero_redis6(r: redis.Redis):
    # Changing -0 to +0 is ignored
    r.zadd("foo", {"a": -0.0})
    r.zadd("foo", {"a": 0.0})
    assert raw_command(r, "zscore", "foo", "a") == b"-0"
