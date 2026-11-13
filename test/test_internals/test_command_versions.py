"""`FakeServer(strict_version=True)`. CASES were checked against real Redis 3.2, 5.0, 6.0, 6.2, 7.0 and 7.2."""

from __future__ import annotations

from typing import Any

import pytest
import redis
from packaging.version import Version

import fakeredis
from fakeredis._commands import SUPPORTED_COMMANDS
from fakeredis._typing import VersionType
from fakeredis.model import is_command_in_version
from fakeredis.model._command_info import _COMMAND_SINCE
from test.testtools import REDIS_PY_VERSION, run_test_if_lupa_installed, run_test_if_redispy_ver

# (command, the Redis version that added it)
CASES: list[tuple[tuple[str, ...], VersionType]] = [
    (("UNLINK", "k"), (4, 0)),
    (("HELLO", "2"), (6, 0)),
    (("GETDEL", "k"), (6, 2)),
    (("LMPOP", "1", "k", "LEFT"), (7, 0)),
    (("CLIENT", "SETINFO", "LIB-NAME", "x"), (7, 2)),
]


def _client(version: Any, strict_version: bool = True, server_type: str = "redis", **kwargs: Any) -> redis.Redis:
    if REDIS_PY_VERSION >= Version("5"):
        kwargs.setdefault("protocol", 2)  # RESP3 connects with HELLO, which Redis < 6 doesn't have
    server = fakeredis.FakeServer(version=version, server_type=server_type, strict_version=strict_version)
    return fakeredis.FakeStrictRedis(server=server, **kwargs)


def _is_unknown(r: redis.Redis, *args: str) -> bool:
    try:
        r.execute_command(*args)
    except redis.ResponseError as e:
        return "unknown command" in str(e)
    return False


@pytest.mark.fake
@pytest.mark.parametrize("version", [(3, 2), (5, 0), (6, 0), (6, 2), (7, 0), (7, 2)], ids=str)
@pytest.mark.parametrize("args,since", CASES, ids=[" ".join(c[:2]) if c[0] == "CLIENT" else c[0] for c, _ in CASES])
def test_command_is_unknown_before_its_version(version: VersionType, args: tuple[str, ...], since: VersionType):
    assert _is_unknown(_client(version), *args) == (version < since)


@pytest.mark.fake
def test_off_by_default():
    r = _client((3, 2), strict_version=False)
    assert not any(_is_unknown(r, *args) for args, _ in CASES)


@pytest.mark.fake
def test_only_the_given_version_parts_are_compared():
    assert not _is_unknown(_client(6), "GETDEL", "k")
    assert _is_unknown(_client("6.0"), "GETDEL", "k")
    assert not _is_unknown(_client(8), "XACKDEL", "s", "g", "IDS", "1", "0-1")  # 8.2.0


@pytest.mark.fake
def test_other_server_types_are_not_checked():
    assert not _is_unknown(_client((5, 0), server_type="dragonfly"), "GETDEL", "k")


@pytest.mark.fake
@run_test_if_redispy_ver("gte", "5")
def test_resp3_needs_redis_6():
    with pytest.raises(redis.ResponseError, match="unknown command 'hello'"):
        _client(5, protocol=3).ping()
    assert _client(6, protocol=3).ping()


@pytest.mark.fake
@run_test_if_redispy_ver("gte", "5")
@pytest.mark.parametrize("client_class", ["FakeStrictRedis", "FakeValkey"])
def test_sync_clients(client_class: str):
    r = getattr(fakeredis, client_class)(server=fakeredis.FakeServer(version="6.0", strict_version=True), protocol=2)
    with pytest.raises(Exception, match="unknown command 'getdel'"):
        r.getdel("k")


@pytest.mark.fake
@pytest.mark.asyncio
@run_test_if_redispy_ver("gte", "5")
@pytest.mark.parametrize("client_class", ["FakeAsyncRedis", "FakeAsyncValkey"])
async def test_async_clients(client_class: str):
    r = getattr(fakeredis, client_class)(server=fakeredis.FakeServer(version="6.0", strict_version=True), protocol=2)
    with pytest.raises(Exception, match="unknown command 'getdel'"):
        await r.getdel("k")
    await r.aclose()


@pytest.mark.fake
@run_test_if_lupa_installed()
def test_script_calling_a_newer_command():
    with pytest.raises(redis.ResponseError, match="unknown command 'getdel'"):
        _client("6.0").eval("return redis.call('GETDEL', 'k')", 0)


@pytest.mark.real
def test_commands_since_matches_the_real_server(real_server_details: Any, real_server_address: tuple[str, int]):
    """The real server knows each command (COMMAND INFO) exactly when `is_command_in_version` says so."""
    if real_server_details.server_type != "redis":
        pytest.skip("Only Redis numbers its releases like redis/docs")
    version = real_server_details.redis_version
    real = redis.StrictRedis(*real_server_address)
    disagree = []
    for cmd in sorted(SUPPORTED_COMMANDS):
        if cmd.encode() not in _COMMAND_SINCE or (" " in cmd and version < (7,)):  # container|subcommand needs 7.0
            continue
        known = real.execute_command("COMMAND INFO", cmd.replace(" ", "|"))[0] is not None
        if known != is_command_in_version(cmd.encode(), version):
            disagree.append(cmd)
    real.close()
    assert disagree == []
