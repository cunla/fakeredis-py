import json
import os
import time
from typing import Any, List, Optional, Dict

from fakeredis import _msgs as msgs
from fakeredis._commands import command, DbIndex
from fakeredis._helpers import OK, SimpleError, casematch, BGSAVE_STARTED, Database, SimpleString

_COMMAND_INFO: Optional[Dict[bytes, List[Any]]] = None


def convert_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return obj.encode()
    if isinstance(obj, list):
        return [convert_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {convert_obj(k): convert_obj(obj[k]) for k in obj}
    return obj


def _load_command_info() -> None:
    global _COMMAND_INFO
    if _COMMAND_INFO is None:
        with open(os.path.join(os.path.dirname(__file__), "..", "commands.json")) as f:
            _COMMAND_INFO = convert_obj(json.load(f))


class ServerCommandsMixin:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        from fakeredis._server import FakeServer

        self._server: "FakeServer"
        self._db: Database

    @staticmethod
    def _get_command_info(cmd: bytes) -> Optional[List[Any]]:
        _load_command_info()
        if _COMMAND_INFO is None or cmd not in _COMMAND_INFO:
            return None
        return _COMMAND_INFO.get(cmd, None)

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
        # TODO: clear watches and/or pubsub as well?
        return OK

    @command(())
    def lastsave(self) -> int:
        return self._server.lastsave

    @command((), flags=msgs.FLAG_NO_SCRIPT)
    def save(self) -> SimpleString:
        self._server.lastsave = int(time.time())
        return OK

    @command(())
    def time(self) -> List[bytes]:
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
    def command_info(self, *commands: bytes) -> List[Any]:
        res = [self._get_command_info(cmd) for cmd in commands]
        return res

    @command(name="COMMAND COUNT", fixed=(), repeat=())
    def command_count(self) -> int:
        _load_command_info()
        return len(_COMMAND_INFO) if _COMMAND_INFO is not None else 0

    @command(name="COMMAND", fixed=(), repeat=())
    def command_(self) -> List[Any]:
        _load_command_info()
        if _COMMAND_INFO is None:
            return []
        res = [self._get_command_info(cmd) for cmd in _COMMAND_INFO]
        return res
