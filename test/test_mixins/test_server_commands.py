import time
from collections.abc import Callable
from datetime import datetime
from time import sleep

import pytest
import redis
import valkey

from fakeredis._commands import SUPPORTED_COMMANDS
from fakeredis._core._server import _create_version
from fakeredis._typing import ClientType
from test.conftest import ServerDetails
from test.testtools import RESPONSE_ERRORS, raw_command, run_test_if_lupa


@pytest.mark.unsupported_server_types("dragonfly")
def test_swapdb(r: ClientType, create_connection: Callable[..., ClientType]):
    r1 = create_connection(db=3)
    r.set("foo", "abc")
    r.set("bar", "xyz")
    r1.set("foo", "foo")
    r1.set("baz", "baz")
    assert r.swapdb(2, 3)
    assert r.get("foo") == b"foo"
    assert r.get("bar") is None
    assert r.get("baz") == b"baz"
    assert r1.get("foo") == b"abc"
    assert r1.get("bar") == b"xyz"
    assert r1.get("baz") is None


@pytest.mark.unsupported_server_types("dragonfly")
def test_swapdb_same_db(r: ClientType):
    assert r.swapdb(1, 1)


def test_save(r: ClientType):
    assert r.save()


@pytest.mark.unsupported_server_types("dragonfly")
def test_bgsave(r: ClientType):
    assert r.bgsave()
    time.sleep(0.1)
    with pytest.raises(Exception) as ctx:
        r.execute_command("BGSAVE", "SCHEDULE", "FOO")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))
    with pytest.raises(Exception) as ctx:
        r.execute_command("BGSAVE", "FOO")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_lastsave(r: ClientType):
    assert isinstance(r.lastsave(), datetime)


@pytest.mark.fake_only
def test_command(r: ClientType):
    commands_dict = r.command()
    one_word_commands = {cmd for cmd in SUPPORTED_COMMANDS if " " not in cmd and SUPPORTED_COMMANDS[cmd].server_types}
    server_unsupported_commands = one_word_commands - set(commands_dict.keys())
    server_unsupported_commands = server_unsupported_commands - {"hgetdel", "hgetex", "hsetex", "msetex", "xcfgset"}
    for command in server_unsupported_commands:
        assert "redis" not in SUPPORTED_COMMANDS[command].server_types, (
            f"Command {command} is not supported by fakeredis"
        )


@pytest.mark.fake_only
def test_command_count(r: ClientType):
    assert r.command_count() >= len(
        [cmd for (cmd, cmd_info) in SUPPORTED_COMMANDS.items() if " " not in cmd and "redis" in cmd_info.server_types]
    )


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.slow
def test_bgsave_timestamp_update(r: ClientType):
    early_timestamp = r.lastsave()
    sleep(1)
    assert r.bgsave()
    sleep(1)
    late_timestamp = r.lastsave()
    assert early_timestamp < late_timestamp


@pytest.mark.slow
def test_save_timestamp_update(r: ClientType):
    early_timestamp = r.lastsave()
    sleep(1)
    assert r.save()
    late_timestamp = r.lastsave()
    assert early_timestamp < late_timestamp


def test_dbsize(r: ClientType):
    assert r.dbsize() == 0
    r.set("foo", "bar")
    r.set("bar", "foo")
    assert r.dbsize() == 2


def test_flushdb_redispy4(r: ClientType):
    r.set("foo", "bar")
    assert r.keys() == [b"foo"]
    assert r.flushdb() is True
    assert r.keys() == []


def _info_headers(r: ClientType, *sections: str) -> list[str]:
    """The `# Section` headers of a raw INFO reply, in the order the server printed them."""
    reply = raw_command(r, "INFO", *sections)
    return [line for line in reply.decode().split("\r\n") if line.startswith("#")]


def _keyspace_name(r: ClientType) -> str:
    """The name INFO KEYSPACE lists the client's database under: `db2` and so on."""
    return f"db{r.connection_pool.connection_kwargs.get('db', 0)}"


def test_info_server_version(r: ClientType, real_server_details: ServerDetails):
    info = r.info("server")
    server_type = real_server_details.server_type
    if server_type == "valkey":
        # Valkey reports the Redis version it forked from, and its own version beside it.
        assert info["redis_version"] == "7.2.4"
        assert info["server_name"] == "valkey"
        assert _create_version(info["valkey_version"])[:2] == real_server_details.valkey_version[:2]
    else:
        assert _create_version(info["redis_version"])[:2] == real_server_details.redis_version[:2]
        assert "server_name" not in info
    # Dragonfly and KiviDB are told apart by their own version field.
    assert ("dragonfly_version" in info) == (server_type == "dragonfly")
    assert ("kividb_version" in info) == (server_type == "kividb")
    assert isinstance(info["uptime_in_seconds"], int)
    assert isinstance(info["process_id"], int)


def test_info_keyspace(r: ClientType, create_connection: Callable[..., ClientType], real_server_details: ServerDetails):
    db = _keyspace_name(r)
    other = create_connection(db=7)
    r.set("persistent", "v")
    r.set("volatile", "v", ex=100)
    other.set("other", "v")
    keyspace = r.info("keyspace")
    assert keyspace[db]["keys"] == 2
    assert keyspace[db]["expires"] == 1
    assert keyspace["db7"]["keys"] == 1
    assert keyspace["db7"]["expires"] == 0
    assert "db1" not in keyspace
    if real_server_details.server_type == "dragonfly":
        assert keyspace[db]["avg_ttl"] == -1
    else:
        # Redis estimates it from sampled keys, so it can still be 0 right after the key is set.
        assert 0 <= keyspace[db]["avg_ttl"] <= 100_000
        assert keyspace["db7"]["avg_ttl"] == 0


def test_info_keyspace_empty(r: ClientType, real_server_details: ServerDetails):
    keyspace = r.info("keyspace")
    if real_server_details.server_type == "dragonfly":
        assert keyspace["db0"]["keys"] == 0
    else:
        assert keyspace == {}


@pytest.mark.fake_only
def test_info_keyspace_drops_expired_keys(r: ClientType):
    # A real server keeps counting an expired key until its expiry cycle reclaims it, as DBSIZE does. fakeredis has no
    # such cycle and leaves expired keys out of both.
    r.set("gone", "v", px=1)
    r.set("kept", "v")
    sleep(0.01)
    assert r.info("keyspace")[_keyspace_name(r)]["keys"] == 1


@pytest.mark.unsupported_server_types("dragonfly", "kividb")
@pytest.mark.supported_server_versions(min_redis_ver="7.4", min_valkey_ver="9")
def test_info_keyspace_hash_field_ttl(r: ClientType, real_server_details: ServerDetails):
    r.hset("with_ttl", mapping={"f1": "v", "f2": "v"})
    r.hset("without_ttl", "f", "v")
    raw_command(r, "HEXPIRE", "with_ttl", 100, "FIELDS", 1, "f1")
    field = "keys_with_volatile_items" if real_server_details.server_type == "valkey" else "subexpiry"
    assert r.info("keyspace")[_keyspace_name(r)][field] == 1


def test_info_sections(r: ClientType, real_server_details: ServerDetails):
    assert raw_command(r, "INFO", "cluster").startswith(b"# Cluster\r\ncluster_enabled:0\r\n")
    assert raw_command(r, "INFO", "CLUSTER").startswith(b"# Cluster\r\n")
    assert raw_command(r, "INFO", "no-such-section") == b""
    assert r.info("replication")["role"] == "master"
    assert r.info("clients")["connected_clients"] >= 1
    assert r.info("persistence")["loading"] == 0
    default = _info_headers(r)
    assert default[0] == "# Server"
    assert {"# Clients", "# Replication", "# Cluster", "# Keyspace"} <= set(default)
    # Dragonfly leaves persistence out unless asked for it, or for "all".
    assert ("# Persistence" in default) == (real_server_details.server_type != "dragonfly")
    assert {"# Server", "# Persistence", "# Keyspace"} <= set(_info_headers(r, "all"))


def test_info_default_keywords(r: ClientType, real_server_details: ServerDetails):
    for keyword in ("default", "everything"):
        if real_server_details.server_type == "dragonfly":
            # Dragonfly only knows "all": to it these are unknown sections.
            assert raw_command(r, "INFO", keyword) == b""
        else:
            assert "# Server" in _info_headers(r, keyword)


@pytest.mark.unsupported_server_types("dragonfly")
def test_info_persistence_last_save(r: ClientType):
    assert r.info("persistence")["rdb_last_save_time"] == r.lastsave().timestamp()


@pytest.mark.supported_server_versions(min_redis_ver="7")
def test_info_several_sections(r: ClientType, real_server_details: ServerDetails):
    headers = _info_headers(r, "keyspace", "cluster", "server", "cluster")
    if real_server_details.server_type == "dragonfly":
        # Dragonfly prints sections in the order asked, repeats included.
        assert headers == ["# Keyspace", "# Cluster", "# Server", "# Cluster"]
    else:
        assert headers == ["# Server", "# Cluster", "# Keyspace"]
    info = r.info("server", "keyspace")
    assert "redis_version" in info


@pytest.mark.unsupported_server_types("valkey", "dragonfly", "kividb")
@pytest.mark.supported_server_versions(max_redis_ver="6.99")
def test_info_several_sections_before_redis_7(r: ClientType):
    with pytest.raises(RESPONSE_ERRORS, match="syntax error"):
        raw_command(r, "INFO", "server", "keyspace")


def test_info_in_transaction(r: ClientType):
    pipe = r.pipeline(transaction=True)
    pipe.info("server")
    assert "redis_version" in pipe.execute()[0]


@run_test_if_lupa
def test_info_in_script(r: ClientType):
    assert r.eval("return redis.call('INFO', 'cluster')", 0).startswith(b"# Cluster\r\n")
