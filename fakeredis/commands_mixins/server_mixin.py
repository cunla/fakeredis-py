from __future__ import annotations

import time
from typing import Any

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import DbIndex
from fakeredis._commands import command
from fakeredis._helpers import BGSAVE_STARTED, OK, SimpleError, SimpleString, casematch
from fakeredis.commands_mixins._mixin_base import CommandsMixinBase
from fakeredis.model import get_all_commands_info, get_command_info

# The INFO sections fakeredis reports, in the order Redis prints them. Sections whose figures fakeredis does not track
# (memory, stats, cpu, commandstats, ...) are left out rather than filled with made-up numbers.
_INFO_SECTIONS = (b"server", b"clients", b"persistence", b"replication", b"cluster", b"keyspace")


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
        fields = self._info_fields(name)
        lines = [f"# {name.decode().capitalize()}"]
        for key, value in fields.items():
            if isinstance(value, dict):  # a keyspace line: db0:keys=1,expires=0,...
                value = ",".join(f"{stat}={number}" for stat, number in value.items())
            lines.append(f"{key}:{value}")
        return "".join(f"{line}\r\n" for line in lines).encode()

    def _info_fields(self, name: bytes) -> dict[str, Any]:
        """The fields of INFO section `name`, in the order they are printed."""
        if name == b"server":
            return self._server.info_server_fields()
        if name == b"clients":
            return {"connected_clients": len(self._server.sockets)}
        if name == b"persistence":
            save_field = "last_success_save" if self.server_type == "dragonfly" else "rdb_last_save_time"
            return {"loading": 0, save_field: self._server.lastsave}
        if name == b"replication":
            return {"role": "master", "connected_slaves": 0}
        if name == b"cluster":
            return {"cluster_enabled": 0}
        return self._server.info_keyspace_fields()
