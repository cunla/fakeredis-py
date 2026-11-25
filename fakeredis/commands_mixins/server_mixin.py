from __future__ import annotations

import os
import platform
import struct
import time
from typing import Any

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import DbIndex
from fakeredis._commands import command
from fakeredis._helpers import BGSAVE_STARTED, OK, SimpleError, SimpleString, casematch
from fakeredis.commands_mixins._mixin_base import CommandsMixinBase
from fakeredis.model import Hash, get_all_commands_info, get_command_info

# The INFO sections fakeredis reports, in the order Redis prints them. Sections whose figures fakeredis does not track
# (memory, stats, cpu, commandstats, ...) are left out rather than filled with made-up numbers.
_INFO_SECTIONS = (b"server", b"clients", b"persistence", b"replication", b"cluster", b"keyspace")


def _version_string(version: tuple[int, ...]) -> str:
    """`(7, 4)` -> `"7.4.0"`: servers always report at least major.minor.patch."""
    return ".".join(str(part) for part in (*version, 0, 0, 0)[: max(3, len(version))])


class ServerCommandsMixin(CommandsMixinBase):
    @command((), (bytes,), flags=msgs.FLAG_NO_SCRIPT)
    def bgsave(self, *args: bytes) -> SimpleString:
        if len(args) > 1 or (len(args) == 1 and not casematch(args[0], b"schedule")):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        self._server.lastsave = int(time.time())
        return BGSAVE_STARTED

    @command(())
    def dbsize(self) -> int:
        return len(self._db)

    @command((), (bytes,))
    def flushdb(self, *args: bytes) -> SimpleString:
        if len(args) > 0 and (len(args) != 1 or not casematch(args[0], b"async")):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        self._db.clear()
        return OK

    @command((), (bytes,))
    def flushall(self, *args: bytes) -> SimpleString:
        if len(args) > 0 and (len(args) != 1 or not casematch(args[0], b"async")):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        for db in self._server.dbs.values():
            db.clear()
        return OK

    @command(())
    def lastsave(self) -> int:
        return self._server.lastsave

    @command((), flags=msgs.FLAG_NO_SCRIPT)
    def save(self) -> SimpleString:
        self._server.lastsave = int(time.time())
        return OK

    @command(())
    def time(self) -> list[bytes]:
        now_us = round(time.time() * 1_000_000)
        now_s = now_us // 1_000_000
        now_us %= 1_000_000
        return [str(now_s).encode(), str(now_us).encode()]

    @command((DbIndex, DbIndex))
    def swapdb(self, index1: int, index2: int) -> SimpleString:
        if index1 != index2:
            db1 = self._server.dbs[index1]
            db2 = self._server.dbs[index2]
            db1.swap(db2)
        return OK

    @command(name="COMMAND INFO", fixed=(), repeat=(bytes,))
    def command_info(self, *commands: bytes) -> list[Any]:
        res = [get_command_info(cmd) for cmd in commands]
        return res

    @command(name="COMMAND COUNT", fixed=(), repeat=())
    def command_count(self) -> int:
        return len(get_all_commands_info())

    @command(name="COMMAND", fixed=(), repeat=())
    def command_(self) -> list[Any]:
        res = [get_command_info(cmd) for cmd in get_all_commands_info()]
        return res

    @command(name="INFO", fixed=(), repeat=(bytes,))
    def info(self, *sections: bytes) -> bytes:
        if len(sections) > 1 and self.server_type == "redis" and self.version < (7,):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)  # Redis 7.0 made INFO take several sections
        requested = [section.lower() for section in sections]
        if self.server_type == "dragonfly":
            # Dragonfly prints the sections in the order asked, repeating one asked twice. Of the keywords it knows only
            # "all": "default" and "everything" are unknown sections to it, which print nothing. Asked for nothing, it
            # prints every section but persistence.
            if not requested:
                return b"\r\n".join(self._info_section(name) for name in _INFO_SECTIONS if name != b"persistence")
            names = [
                name
                for section in requested
                for name in (_INFO_SECTIONS if section == b"all" else (section,))
                if name in _INFO_SECTIONS
            ]
        elif not requested or any(section in (b"default", b"all", b"everything") for section in requested):
            names = list(_INFO_SECTIONS)
        else:
            names = [name for name in _INFO_SECTIONS if name in requested]
        return b"\r\n".join(self._info_section(name) for name in names)

    def _info_section(self, name: bytes) -> bytes:
        fields: dict[str, Any]
        if name == b"server":
            fields = self._info_server_fields()
        elif name == b"clients":
            fields = {"connected_clients": len(self._server.sockets)}
        elif name == b"persistence":
            save_field = "last_success_save" if self.server_type == "dragonfly" else "rdb_last_save_time"
            fields = {"loading": 0, save_field: self._server.lastsave}
        elif name == b"replication":
            fields = {"role": "master", "connected_slaves": 0}
        elif name == b"cluster":
            fields = {"cluster_enabled": 0}
        else:
            fields = self._info_keyspace_fields()
        lines = [f"# {name.decode().capitalize()}"]
        for key, value in fields.items():
            if isinstance(value, dict):  # a keyspace line: db0:keys=1,expires=0,...
                value = ",".join(f"{stat}={number}" for stat, number in value.items())
            lines.append(f"{key}:{value}")
        return "".join(f"{line}\r\n" for line in lines).encode()

    def _info_server_fields(self) -> dict[str, Any]:
        details = self._server.details
        fields: dict[str, Any] = {"redis_version": _version_string(details.redis_version)}
        if details.valkey_version is not None:
            fields["server_name"] = "valkey"
            fields["valkey_version"] = _version_string(details.valkey_version)
        if details.dragonfly_version is not None:
            fields["dragonfly_version"] = f"df-v{_version_string(details.dragonfly_version)}"
        if details.kividb_version is not None:
            fields["kividb_version"] = _version_string(details.kividb_version)
        # Valkey 8.0 renamed redis_mode to server_mode.
        valkey_8 = details.valkey_version is not None and details.valkey_version >= (8,)
        fields["server_mode" if valkey_8 else "redis_mode"] = "standalone"
        now = time.time()
        uptime = int(now - self._server.started_at)
        fields["os"] = f"{platform.system()} {platform.release()} {platform.machine()}"
        fields["arch_bits"] = struct.calcsize("P") * 8
        fields["process_id"] = os.getpid()
        if self.server_type != "dragonfly":
            fields["run_id"] = self._server.run_id
        if self.server_type in ("redis", "valkey"):
            fields["server_time_usec"] = int(now * 1_000_000)
        fields["uptime_in_seconds"] = uptime
        fields["uptime_in_days"] = uptime // 86400
        return fields

    def _info_keyspace_fields(self) -> dict[str, Any]:
        """`{"db0": {"keys": 2, "expires": 1, ...}, ...}`, one entry per database listed."""
        fields: dict[str, Any] = {}
        indexes = set(self._server.dbs)
        if self.server_type == "dragonfly":
            indexes.add(0)  # Dragonfly lists db0 even when it is empty
        for index in sorted(indexes):
            db = self._server.dbs.get(index)
            items = [] if db is None else list(db.values())  # iterating sweeps out expired keys first
            if not items and not (self.server_type == "dragonfly" and index == 0):
                continue
            now = db.time if db is not None else 0.0
            ttls_ms = [(item.expireat - now) * 1000 for item in items if item.expireat is not None]
            stats: dict[str, int] = {"keys": len(items), "expires": len(ttls_ms)}
            if self.server_type == "dragonfly":
                stats["avg_ttl"] = -1  # Dragonfly does not compute it
            else:
                stats["avg_ttl"] = int(sum(ttls_ms) / len(ttls_ms)) if ttls_ms else 0
            # Keys holding hash fields with a TTL. Redis 7.4 calls them subexpiry, Valkey 9 keys_with_volatile_items.
            volatile_field = None
            if self.server_type == "redis" and self.version >= (7, 4):
                volatile_field = "subexpiry"
            elif self.server_type == "valkey" and self.version >= (9,):
                volatile_field = "keys_with_volatile_items"
            if volatile_field is not None:
                stats[volatile_field] = sum(
                    1 for item in items if isinstance(item.value, Hash) and item.value.has_volatile_fields()
                )
            fields[f"db{index}"] = stats
        return fields
