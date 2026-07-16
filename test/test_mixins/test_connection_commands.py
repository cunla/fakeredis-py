import contextlib
import threading
import time

import pytest
import redis
import valkey
from packaging.version import Version

from fakeredis import _msgs as msgs
from fakeredis._typing import ClientType
from test import testtools
from test.testtools import raw_command, resp_conversion

RESPONSE_ERRORS = (redis.ResponseError, valkey.ResponseError)
CONNECTION_ERRORS = (redis.ConnectionError, valkey.ConnectionError)


@contextlib.contextmanager
def raw_connection(r: ClientType):
    """Yield a dedicated connection, thrown away afterwards.

    CLIENT REPLY and RESET leave per-connection state behind, so the connection must not
    go back into the pool. Commands are sent without reading a reply, which is the only
    way to drive CLIENT REPLY OFF/SKIP without hanging.
    """
    # redis-py made the command_name argument optional in 5.0 and deprecated it in 5.3.
    if testtools.REDIS_PY_VERSION >= Version("5.0"):
        conn = r.connection_pool.get_connection()
    else:
        conn = r.connection_pool.get_connection("_")
    try:
        yield conn
    finally:
        conn.disconnect()
        r.connection_pool.release(conn)


def client_info_field(conn, field: bytes) -> bytes:
    conn.send_command("CLIENT", "INFO")
    info = conn.read_response()
    if isinstance(info, str):
        info = info.encode()
    for part in info.split():
        name, _, value = part.partition(b"=")
        if name == field:
            return value
    raise AssertionError(f"{field!r} missing from CLIENT INFO")


def test_ping(r: ClientType):
    assert r.ping()
    assert testtools.raw_command(r, "ping", "test") == b"test"
    with pytest.raises(Exception, match=msgs.WRONG_ARGS_MSG6.format("ping")[4:]) as ctx:
        raw_command(r, "ping", "arg1", "arg2")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_echo(r: ClientType):
    assert r.echo(b"hello") == b"hello"
    assert r.echo("hello") == b"hello"


def test_unknown_command(r: ClientType):
    with pytest.raises(Exception) as ctx:
        raw_command(r, "0 3 3")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@pytest.mark.fake_only
def test_time(r: ClientType, mocker):
    fake_time = mocker.patch("time.time")
    fake_time.return_value = 1234567890.1234567
    assert r.time() == (1234567890, 123457)
    fake_time.return_value = 1234567890.000001
    assert r.time() == (1234567890, 1)
    fake_time.return_value = 1234567890.9999999
    assert r.time() == (1234567891, 0)


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="7")
def test_client_list(r: ClientType):
    client_info = r.client_info()
    client_id = client_info["id"]
    client_list = r.client_list()
    assert isinstance(client_list, list)
    assert len(client_list) >= 1
    assert isinstance(client_list[0], dict)
    client_ids = [int(client["id"]) for client in client_list]
    assert client_id in client_ids
    # rq and other libraries rely on the addr field being present (see issue #512)
    assert all("addr" in client for client in client_list)
    assert all("age" in client for client in client_list)
    assert all("_created" not in client for client in client_list)

    client_list = r.client_list()
    assert isinstance(client_list, list)
    client_ids = [int(client["id"]) for client in client_list]
    non_existing_client_id = max(client_ids) + 1
    client_list = r.client_list(client_id=[str(non_existing_client_id)])
    assert isinstance(client_list, list)
    assert len(client_list) == 0


@pytest.mark.supported_server_versions(min_redis_ver="7")
@pytest.mark.unsupported_server_types("dragonfly")
@testtools.run_test_if_redispy_ver("gte", "5")
def test_client_info(r: ClientType):
    client_info = r.client_info()
    assert "age" in client_info
    assert "_created" not in client_info
    assert "addr" in client_info
    assert client_info.get("lib-name", "redis-py") in {"redis-py", "valkey-py"}
    r.client_setinfo(b"lib-name", b"fakeredis")
    r.client_setinfo(b"lib-ver", b"1.0.0")
    client_info = r.client_info()
    assert client_info["lib-name"] == "fakeredis"
    assert client_info["lib-ver"] == "1.0.0"


@pytest.mark.unsupported_server_types("dragonfly")
def test_client_id(r: ClientType):
    client_id = r.client_id()
    client_info = r.client_info()
    assert client_id == client_info["id"]


def test_client_setname(r: ClientType):
    assert r.client_setname("test") is True
    assert r.client_getname() == resp_conversion(r, b"test", "test")


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="7")
def test_client_no_evict(r: ClientType):
    assert raw_command(r, "CLIENT", "NO-EVICT", "ON") == b"OK"
    assert raw_command(r, "CLIENT", "NO-EVICT", "off") == b"OK"
    with pytest.raises(RESPONSE_ERRORS, match="syntax error"):
        raw_command(r, "CLIENT", "NO-EVICT", "MAYBE")
    with pytest.raises(RESPONSE_ERRORS):
        raw_command(r, "CLIENT", "NO-EVICT")


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="7.2")
def test_client_no_touch(r: ClientType):
    assert raw_command(r, "CLIENT", "NO-TOUCH", "ON") == b"OK"
    assert raw_command(r, "CLIENT", "NO-TOUCH", "off") == b"OK"
    with pytest.raises(RESPONSE_ERRORS, match="syntax error"):
        raw_command(r, "CLIENT", "NO-TOUCH", "MAYBE")


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="7.2")
def test_client_no_evict_and_no_touch_show_in_client_info_flags(r: ClientType):
    with raw_connection(r) as conn:
        assert client_info_field(conn, b"flags") == b"N"
        conn.send_command("CLIENT", "NO-TOUCH", "ON")
        assert conn.read_response() == b"OK"
        assert client_info_field(conn, b"flags") == b"T"
        conn.send_command("CLIENT", "NO-EVICT", "ON")
        assert conn.read_response() == b"OK"
        assert client_info_field(conn, b"flags") == b"eT"
        conn.send_command("CLIENT", "NO-TOUCH", "OFF")
        assert conn.read_response() == b"OK"
        assert client_info_field(conn, b"flags") == b"e"


@pytest.mark.unsupported_server_types("dragonfly")
def test_client_pause(r: ClientType):
    assert raw_command(r, "CLIENT", "PAUSE", "0") == b"OK"
    assert raw_command(r, "CLIENT", "PAUSE", "0", "WRITE") == b"OK"
    assert raw_command(r, "CLIENT", "PAUSE", "0", "ALL") == b"OK"
    with pytest.raises(RESPONSE_ERRORS, match="CLIENT PAUSE mode must be WRITE or ALL"):
        raw_command(r, "CLIENT", "PAUSE", "0", "BOGUS")
    with pytest.raises(RESPONSE_ERRORS, match="timeout is negative"):
        raw_command(r, "CLIENT", "PAUSE", "-1")
    with pytest.raises(RESPONSE_ERRORS, match="timeout is not an integer or out of range"):
        raw_command(r, "CLIENT", "PAUSE", "notanumber")


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6.2")
def test_client_unpause(r: ClientType):
    assert raw_command(r, "CLIENT", "PAUSE", "10000") == b"OK"
    assert raw_command(r, "CLIENT", "UNPAUSE") == b"OK"
    # CLIENT PAUSE never actually suspends fakeredis, so this only proves the server
    # still answers; it is UNPAUSE's contract on a real server that matters here.
    assert r.ping()


@pytest.mark.unsupported_server_types("dragonfly")
def test_client_reply_on_is_the_default(r: ClientType):
    assert raw_command(r, "CLIENT", "REPLY", "ON") == b"OK"
    with pytest.raises(RESPONSE_ERRORS, match="syntax error"):
        raw_command(r, "CLIENT", "REPLY", "BOGUS")


@pytest.mark.unsupported_server_types("dragonfly")
def test_client_reply_off_suppresses_replies_until_on(r: ClientType):
    with raw_connection(r) as conn:
        conn.send_command("CLIENT", "REPLY", "OFF")
        conn.send_command("PING")
        conn.send_command("SET", "reply-off-key", "value")
        # None of the above replies; CLIENT REPLY ON always does, so its OK is first.
        conn.send_command("CLIENT", "REPLY", "ON")
        assert conn.read_response() == b"OK"
        conn.send_command("PING")
        assert conn.read_response() == b"PONG"
        # The suppressed SET still ran.
        conn.send_command("GET", "reply-off-key")
        assert conn.read_response() == b"value"


@pytest.mark.unsupported_server_types("dragonfly")
def test_client_reply_skip_skips_only_the_next_command(r: ClientType):
    with raw_connection(r) as conn:
        conn.send_command("CLIENT", "REPLY", "SKIP")
        conn.send_command("PING")  # reply skipped
        conn.send_command("ECHO", "after-skip")
        assert conn.read_response() == b"after-skip"


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
def test_client_kill_by_id(r: ClientType, create_connection):
    victim = create_connection(db=2)
    victim.ping()
    victim_id = victim.client_id()

    assert raw_command(r, "CLIENT", "KILL", "ID", str(victim_id)) == 1

    # The killed connection is gone, so the victim can only reach the server over a new
    # one. Whether the drop first surfaces as an error depends on the client's retry
    # policy rather than on the server, so accept either.
    try:
        new_id = victim.client_id()
    except CONNECTION_ERRORS:
        new_id = victim.client_id()
    assert new_id != victim_id


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="7")
def test_client_kill_removes_client_from_client_list(r: ClientType, create_connection):
    victim = create_connection(db=2)
    victim.ping()
    victim_id = victim.client_id()

    assert victim_id in [int(c["id"]) for c in r.client_list()]
    assert raw_command(r, "CLIENT", "KILL", "ID", str(victim_id)) == 1
    assert victim_id not in [int(c["id"]) for c in r.client_list()]


@pytest.mark.unsupported_server_types("dragonfly")
def test_client_kill_unknown_client_old_form(r: ClientType):
    with pytest.raises(RESPONSE_ERRORS, match="No such client"):
        raw_command(r, "CLIENT", "KILL", "1.2.3.4:5")


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
def test_client_kill_no_match_returns_zero(r: ClientType):
    assert raw_command(r, "CLIENT", "KILL", "ID", "99999999") == 0
    # fakeredis has no replication, so these never match a live connection.
    assert raw_command(r, "CLIENT", "KILL", "TYPE", "master") == 0
    assert raw_command(r, "CLIENT", "KILL", "TYPE", "replica") == 0


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
def test_client_kill_skipme_defaults_to_yes(r: ClientType):
    # The caller is a normal client, but SKIPME defaults to yes, so it is spared and
    # stays usable.
    raw_command(r, "CLIENT", "KILL", "TYPE", "normal")
    assert r.ping()


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
def test_client_kill_invalid_filters(r: ClientType):
    with pytest.raises(RESPONSE_ERRORS, match="client-id should be greater than 0"):
        raw_command(r, "CLIENT", "KILL", "ID", "0")
    with pytest.raises(RESPONSE_ERRORS, match="client-id should be greater than 0"):
        raw_command(r, "CLIENT", "KILL", "ID", "notanumber")
    with pytest.raises(RESPONSE_ERRORS, match="Unknown client type 'bogus'"):
        raw_command(r, "CLIENT", "KILL", "TYPE", "bogus")
    with pytest.raises(RESPONSE_ERRORS, match="No such user 'nosuchuser'"):
        raw_command(r, "CLIENT", "KILL", "USER", "nosuchuser")
    with pytest.raises(RESPONSE_ERRORS, match="syntax error"):
        raw_command(r, "CLIENT", "KILL", "SKIPME", "bogus")
    with pytest.raises(RESPONSE_ERRORS, match="syntax error"):
        raw_command(r, "CLIENT", "KILL", "BOGUSFILTER", "x")


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="7.4")
def test_client_kill_maxage(r: ClientType):
    assert raw_command(r, "CLIENT", "KILL", "MAXAGE", "100000") == 0
    with pytest.raises(RESPONSE_ERRORS, match="maxage should be greater than 0"):
        raw_command(r, "CLIENT", "KILL", "MAXAGE", "0")
    with pytest.raises(RESPONSE_ERRORS, match="maxage is not an integer or out of range"):
        raw_command(r, "CLIENT", "KILL", "MAXAGE", "bogus")


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
def test_client_unblock_not_blocked(r: ClientType):
    assert raw_command(r, "CLIENT", "UNBLOCK", str(r.client_id())) == 0
    assert raw_command(r, "CLIENT", "UNBLOCK", "99999999") == 0


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
def test_client_unblock_invalid_args(r: ClientType):
    with pytest.raises(RESPONSE_ERRORS, match="value is not an integer or out of range"):
        raw_command(r, "CLIENT", "UNBLOCK", "notanid")
    with pytest.raises(RESPONSE_ERRORS, match="CLIENT UNBLOCK reason should be TIMEOUT or ERROR"):
        raw_command(r, "CLIENT", "UNBLOCK", "1", "BOGUS")


def _block_on_blpop(client: ClientType, result: dict) -> threading.Thread:
    def target() -> None:
        try:
            result["value"] = client.blpop("unblock-list", timeout=5)
        except Exception as e:  # noqa: BLE001 - recorded so the assertion can describe it
            result["error"] = e

    thread = threading.Thread(target=target)
    thread.start()
    # Give the client time to actually park in the blocking command.
    time.sleep(0.3)
    return thread


@pytest.mark.slow
@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
def test_client_unblock_timeout(r: ClientType, create_connection):
    victim = create_connection(db=2)
    victim.ping()
    victim_id = victim.client_id()
    result: dict = {}
    thread = _block_on_blpop(victim, result)
    try:
        assert raw_command(r, "CLIENT", "UNBLOCK", str(victim_id)) == 1
        thread.join(timeout=3)
        assert not thread.is_alive(), "client was not unblocked"
        # Unblocking with TIMEOUT looks exactly like the command timing out.
        assert result == {"value": None}
    finally:
        thread.join(timeout=6)


@pytest.mark.slow
@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6")
def test_client_unblock_error(r: ClientType, create_connection):
    victim = create_connection(db=2)
    victim.ping()
    victim_id = victim.client_id()
    result: dict = {}
    thread = _block_on_blpop(victim, result)
    try:
        assert raw_command(r, "CLIENT", "UNBLOCK", str(victim_id), "ERROR") == 1
        thread.join(timeout=3)
        assert not thread.is_alive(), "client was not unblocked"
        assert isinstance(result.get("error"), RESPONSE_ERRORS)
        assert "UNBLOCKED" in str(result["error"])
    finally:
        thread.join(timeout=6)


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6.2")
def test_reset_returns_reset(r: ClientType):
    with raw_connection(r) as conn:
        conn.send_command("RESET")
        assert conn.read_response() == b"RESET"


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6.2")
def test_reset_discards_transaction(r: ClientType):
    with raw_connection(r) as conn:
        conn.send_command("MULTI")
        assert conn.read_response() == b"OK"
        conn.send_command("SET", "reset-key", "queued")
        assert conn.read_response() == b"QUEUED"
        # RESET runs immediately instead of being queued.
        conn.send_command("RESET")
        assert conn.read_response() == b"RESET"
        conn.send_command("EXEC")
        with pytest.raises(RESPONSE_ERRORS, match="EXEC without MULTI"):
            conn.read_response()
        assert r.get("reset-key") is None


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6.2")
def test_reset_clears_connection_state(r: ClientType):
    with raw_connection(r) as conn:
        conn.send_command("CLIENT", "SETNAME", "to-be-reset")
        assert conn.read_response() == b"OK"
        conn.send_command("CLIENT", "NO-TOUCH", "ON")
        assert conn.read_response() == b"OK"
        assert client_info_field(conn, b"name") == b"to-be-reset"

        conn.send_command("RESET")
        assert conn.read_response() == b"RESET"

        assert client_info_field(conn, b"name") == b""
        assert client_info_field(conn, b"db") == b"0"
        assert client_info_field(conn, b"resp") == b"2"
        assert client_info_field(conn, b"flags") == b"N"


# RESP2 only: a real server delivers the subscribe confirmation as a RESP3 push message,
# while fakeredis queues plain Python objects and has no push framing to mirror it with.
@pytest.mark.resp2_only
@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_server_versions(min_redis_ver="6.2")
def test_reset_unsubscribes(r: ClientType):
    with raw_connection(r) as conn:
        conn.send_command("SUBSCRIBE", "reset-channel")
        assert conn.read_response() == [b"subscribe", b"reset-channel", 1]
        assert r.pubsub_channels() == [b"reset-channel"]

        conn.send_command("RESET")
        assert conn.read_response() == b"RESET"

        assert r.pubsub_channels() == []
        # Out of subscribe mode, arbitrary commands are allowed again.
        conn.send_command("ECHO", "back-to-normal")
        assert conn.read_response() == b"back-to-normal"


@pytest.mark.decode_responses
class TestDecodeResponses:
    def test_decode_str(self, r):
        r.set("foo", "bar")
        assert r.get("foo") == "bar"

    def test_decode_set(self, r):
        r.sadd("foo", "member1")
        assert set(r.smembers("foo")) == {"member1"}

    def test_decode_list(self, r):
        r.rpush("foo", "a", "b")
        assert r.lrange("foo", 0, -1) == ["a", "b"]

    def test_decode_dict(self, r):
        r.hset("foo", "key", "value")
        assert r.hgetall("foo") == {"key": "value"}

    def test_decode_error(self, r):
        r.set("foo", "bar")
        with pytest.raises(Exception) as exc_info:
            r.hset("foo", "bar", "baz")
        assert isinstance(exc_info.value, (redis.ResponseError, valkey.ResponseError))
        assert isinstance(exc_info.value.args[0], str)


@pytest.mark.disconnected
@pytest.mark.fake_only
class TestFakeStrictRedisConnectionErrors:
    def test_flushdb(self, r):
        with pytest.raises(Exception):
            r.flushdb()

    def test_flushall(self, r):
        with pytest.raises(Exception):
            r.flushall()

    def test_append(self, r):
        with pytest.raises(Exception):
            r.append("key", "value")

    def test_bitcount(self, r):
        with pytest.raises(Exception):
            r.bitcount("key", 0, 20)

    def test_decr(self, r):
        with pytest.raises(Exception):
            r.decr("key", 2)

    def test_exists(self, r):
        with pytest.raises(Exception):
            r.exists("key")

    def test_expire(self, r):
        with pytest.raises(Exception):
            r.expire("key", 20)

    def test_pexpire(self, r):
        with pytest.raises(Exception):
            r.pexpire("key", 20)

    def test_echo(self, r):
        with pytest.raises(Exception):
            r.echo("value")

    def test_get(self, r):
        with pytest.raises(Exception):
            r.get("key")

    def test_getbit(self, r):
        with pytest.raises(Exception):
            r.getbit("key", 2)

    def test_getset(self, r):
        with pytest.raises(Exception):
            r.getset("key", "value")

    def test_incr(self, r):
        with pytest.raises(Exception):
            r.incr("key")

    def test_incrby(self, r):
        with pytest.raises(Exception):
            r.incrby("key")

    def test_ncrbyfloat(self, r):
        with pytest.raises(Exception):
            r.incrbyfloat("key")

    def test_keys(self, r):
        with pytest.raises(Exception):
            r.keys()

    def test_mget(self, r):
        with pytest.raises(Exception):
            r.mget(["key1", "key2"])

    def test_mset(self, r):
        with pytest.raises(Exception):
            r.mset({"key": "value"})

    def test_msetnx(self, r):
        with pytest.raises(Exception):
            r.msetnx({"key": "value"})

    def test_persist(self, r):
        with pytest.raises(Exception):
            r.persist("key")

    def test_rename(self, r):
        server = r.connection_pool.connection_kwargs["server"]
        server.connected = True
        r.set("key1", "value")
        server.connected = False
        with pytest.raises(Exception) as ctx:
            r.rename("key1", "key2")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))
        server.connected = True
        assert r.exists("key1")

    def test_eval(self, r):
        with pytest.raises(Exception) as ctx:
            r.eval("", 0)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lpush(self, r):
        with pytest.raises(Exception) as ctx:
            r.lpush("name", 1, 2)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lrange(self, r):
        with pytest.raises(Exception) as ctx:
            r.lrange("name", 1, 5)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_llen(self, r):
        with pytest.raises(Exception) as ctx:
            r.llen("name")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lrem(self, r):
        with pytest.raises(Exception) as ctx:
            r.lrem("name", 2, 2)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_rpush(self, r):
        with pytest.raises(Exception) as ctx:
            r.rpush("name", 1)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lpop(self, r):
        with pytest.raises(Exception) as ctx:
            r.lpop("name")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lset(self, r):
        with pytest.raises(Exception) as ctx:
            r.lset("name", 1, 4)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_rpushx(self, r):
        with pytest.raises(Exception) as ctx:
            r.rpushx("name", 1)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_ltrim(self, r):
        with pytest.raises(Exception):
            r.ltrim("name", 1, 4)

    def test_lindex(self, r):
        with pytest.raises(Exception) as ctx:
            r.lindex("name", 1)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lpushx(self, r):
        with pytest.raises(Exception) as ctx:
            r.lpushx("name", 1)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_rpop(self, r):
        with pytest.raises(Exception) as ctx:
            r.rpop("name")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_linsert(self, r):
        with pytest.raises(Exception) as ctx:
            r.linsert("name", "where", "refvalue", "value")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_rpoplpush(self, r):
        with pytest.raises(Exception) as ctx:
            r.rpoplpush("src", "dst")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_blpop(self, r):
        with pytest.raises(Exception) as ctx:
            r.blpop("keys")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_brpop(self, r):
        with pytest.raises(Exception) as ctx:
            r.brpop("keys")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_brpoplpush(self, r):
        with pytest.raises(Exception) as ctx:
            r.brpoplpush("src", "dst")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hdel(self, r):
        with pytest.raises(Exception) as ctx:
            r.hdel("name")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hexists(self, r):
        with pytest.raises(Exception) as ctx:
            r.hexists("name", "key")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hget(self, r):
        with pytest.raises(Exception) as ctx:
            r.hget("name", "key")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hgetall(self, r):
        with pytest.raises(Exception) as ctx:
            r.hgetall("name")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hincrby(self, r):
        with pytest.raises(Exception) as ctx:
            r.hincrby("name", "key")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hincrbyfloat(self, r):
        with pytest.raises(Exception):
            r.hincrbyfloat("name", "key")

    def test_hkeys(self, r):
        with pytest.raises(Exception):
            r.hkeys("name")

    def test_hlen(self, r):
        with pytest.raises(Exception):
            r.hlen("name")

    def test_hset(self, r):
        with pytest.raises(Exception):
            r.hset("name", "key", 1)

    def test_hsetnx(self, r):
        with pytest.raises(Exception):
            r.hsetnx("name", "key", 2)

    def test_hmset(self, r):
        with pytest.raises(Exception):
            r.hmset("name", {"key": 1})

    def test_hmget(self, r):
        with pytest.raises(Exception):
            r.hmget("name", ["a", "b"])

    def test_hvals(self, r):
        with pytest.raises(Exception):
            r.hvals("name")

    def test_sadd(self, r):
        with pytest.raises(Exception):
            r.sadd("name", 1, 2)

    def test_scard(self, r):
        with pytest.raises(Exception):
            r.scard("name")

    def test_sdiff(self, r):
        with pytest.raises(Exception):
            r.sdiff(["a", "b"])

    def test_sdiffstore(self, r):
        with pytest.raises(Exception):
            r.sdiffstore("dest", ["a", "b"])

    def test_sinter(self, r):
        with pytest.raises(Exception):
            r.sinter(["a", "b"])

    def test_sinterstore(self, r):
        with pytest.raises(Exception):
            r.sinterstore("dest", ["a", "b"])

    def test_sismember(self, r):
        with pytest.raises(Exception):
            r.sismember("name", 20)

    def test_smembers(self, r):
        with pytest.raises(Exception):
            r.smembers("name")

    def test_smove(self, r):
        with pytest.raises(Exception):
            r.smove("src", "dest", 20)

    def test_spop(self, r):
        with pytest.raises(Exception):
            r.spop("name")

    def test_srandmember(self, r):
        with pytest.raises(Exception):
            r.srandmember("name")

    def test_srem(self, r):
        with pytest.raises(Exception):
            r.srem("name")

    def test_sunion(self, r):
        with pytest.raises(Exception):
            r.sunion(["a", "b"])

    def test_sunionstore(self, r):
        with pytest.raises(Exception):
            r.sunionstore("dest", ["a", "b"])

    def test_zadd(self, r):
        with pytest.raises(Exception):
            r.zadd("name", {"key": "value"})

    def test_zcard(self, r):
        with pytest.raises(Exception):
            r.zcard("name")

    def test_zcount(self, r):
        with pytest.raises(Exception):
            r.zcount("name", 1, 5)

    def test_zincrby(self, r):
        with pytest.raises(Exception):
            r.zincrby("name", 1, 1)

    def test_zinterstore(self, r):
        with pytest.raises(Exception):
            r.zinterstore("dest", ["a", "b"])

    def test_zrange(self, r):
        with pytest.raises(Exception):
            r.zrange("name", 1, 5)

    def test_zrangebyscore(self, r):
        with pytest.raises(Exception):
            r.zrangebyscore("name", 1, 5)

    def test_rangebylex(self, r):
        with pytest.raises(Exception):
            r.zrangebylex("name", 1, 4)

    def test_zrem(self, r):
        with pytest.raises(Exception):
            r.zrem("name", "value")

    def test_zremrangebyrank(self, r):
        with pytest.raises(Exception):
            r.zremrangebyrank("name", 1, 5)

    def test_zremrangebyscore(self, r):
        with pytest.raises(Exception):
            r.zremrangebyscore("name", 1, 5)

    def test_zremrangebylex(self, r):
        with pytest.raises(Exception):
            r.zremrangebylex("name", 1, 5)

    def test_zlexcount(self, r):
        with pytest.raises(Exception):
            r.zlexcount("name", 1, 5)

    def test_zrevrange(self, r):
        with pytest.raises(Exception):
            r.zrevrange("name", 1, 5, 1)

    def test_zrevrangebyscore(self, r):
        with pytest.raises(Exception):
            r.zrevrangebyscore("name", 5, 1)

    def test_zrevrangebylex(self, r):
        with pytest.raises(Exception):
            r.zrevrangebylex("name", 5, 1)

    def test_zrevran(self, r):
        with pytest.raises(Exception):
            r.zrevrank("name", 2)

    def test_zscore(self, r):
        with pytest.raises(Exception):
            r.zscore("name", 2)

    def test_zunionstor(self, r):
        with pytest.raises(Exception):
            r.zunionstore("dest", ["1", "2"])

    def test_pipeline(self, r):
        with pytest.raises(Exception):
            r.pipeline().watch("key")

    def test_transaction(self, r):
        with pytest.raises(Exception):

            def func(a):
                return a * a

            r.transaction(func, 3)

    def test_lock(self, r):
        with pytest.raises(Exception):
            with r.lock("name"):
                pass

    def test_pubsub(self, r):
        with pytest.raises(Exception):
            r.pubsub().subscribe("channel")

    def test_pfadd(self, r):
        with pytest.raises(Exception):
            r.pfadd("name", 1)

    def test_pfmerge(self, r):
        with pytest.raises(Exception):
            r.pfmerge("dest", "a", "b")

    def test_scan(self, r):
        with pytest.raises(Exception):
            list(r.scan())

    def test_sscan(self, r):
        with pytest.raises(Exception):
            r.sscan("name")

    def test_hscan(self, r):
        with pytest.raises(Exception):
            r.hscan("name")

    def test_scan_iter(self, r):
        with pytest.raises(Exception):
            list(r.scan_iter())

    def test_sscan_iter(self, r):
        with pytest.raises(Exception):
            list(r.sscan_iter("name"))

    def test_hscan_iter(self, r):
        with pytest.raises(Exception):
            list(r.hscan_iter("name"))


@pytest.mark.disconnected
@pytest.mark.fake_only
class TestPubSubConnected:
    @pytest.fixture
    def pubsub(self, r):
        return r.pubsub()

    def test_basic_subscribe(self, pubsub):
        with pytest.raises(Exception) as ctx:
            pubsub.subscribe("logs")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_subscription_conn_lost(self, fake_server, pubsub):
        fake_server.connected = True
        pubsub.subscribe("logs")
        fake_server.connected = False
        # The initial message is already in the pipe
        msg = pubsub.get_message()
        check = {"type": "subscribe", "pattern": None, "channel": b"logs", "data": 1}
        assert msg == check, "Message was not published to channel"
        with pytest.raises(Exception) as ctx:
            pubsub.get_message()
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))
