import time
from datetime import datetime
from time import sleep

import pytest
import redis
import valkey

from fakeredis._commands import SUPPORTED_COMMANDS
from fakeredis._typing import ClientType
from test import testtools


@pytest.mark.unsupported_server_types("dragonfly")
def test_swapdb(r, create_connection):
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


@testtools.fake_only
def test_command(r: ClientType):
    commands_dict = r.command()
    one_word_commands = {cmd for cmd in SUPPORTED_COMMANDS if " " not in cmd and SUPPORTED_COMMANDS[cmd].server_types}
    server_unsupported_commands = one_word_commands - set(commands_dict.keys())
    server_unsupported_commands = server_unsupported_commands - {"hgetdel", "hgetex", "hsetex", "msetex", "xcfgset"}
    for command in server_unsupported_commands:
        assert "redis" not in SUPPORTED_COMMANDS[command].server_types, (
            f"Command {command} is not supported by fakeredis"
        )


@testtools.fake_only
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
