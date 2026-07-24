from __future__ import annotations

import time
from collections.abc import Sequence
from typing import Any, Callable

import fakeredis
from fakeredis import _msgs as msgs
from fakeredis._commands import DbIndex, Int, command
from fakeredis._helpers import OK, NoResponse, SimpleError, SimpleString, casematch
from fakeredis.commands_mixins._mixin_base import CommandsMixinBase

PONG = SimpleString(b"PONG")
RESET = SimpleString(b"RESET")
# Client types accepted by CLIENT KILL. fakeredis has no replication, so `master`,
# `replica` and `slave` are valid filters that never match a live connection.
CLIENT_KILL_TYPES = {b"normal", b"master", b"replica", b"slave", b"pubsub"}


class ConnectionCommandsMixin(CommandsMixinBase):
    _clear_watches: Callable[[], None]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._db_num: int
        self._pubsub: int
        self._transaction: list[Any] | None
        self._transaction_failed: bool
        self._killed: bool
        self._blocked: bool
        self._unblock_reason: bytes | None
        self._reply_off: bool
        self._reply_skip: bool
        self._reply_skip_next: bool
        self._no_evict: bool
        self._no_touch: bool

    @command((bytes,))
    def echo(self, message: bytes) -> bytes:
        return message

    @command((), (bytes,))
    def ping(self, *args: bytes) -> list[bytes] | bytes | SimpleString:
        if len(args) > 1:
            msg = msgs.WRONG_ARGS_MSG6.format("ping")
            raise SimpleError(msg)
        if self._pubsub and self._client_info.protocol_version == 2:
            return [b"pong", args[0] if args else b""]
        else:
            return args[0] if args else PONG

    @command(name="SELECT", fixed=(DbIndex,))
    def select(self, index: int) -> SimpleString:
        self._db = self._server.dbs[index]
        self._db_num = index
        return OK

    @command(name="CLIENT SETINFO", fixed=(bytes, bytes), repeat=())
    def client_setinfo(self, lib_data: bytes, value: bytes) -> SimpleString:
        if casematch(lib_data, b"LIB-NAME"):
            self._client_info["lib-name"] = value.decode("utf-8")
            return OK
        if casematch(lib_data, b"LIB-VER"):
            self._client_info["lib-ver"] = value.decode("utf-8")
            return OK
        raise SimpleError(msgs.SYNTAX_ERROR_MSG)

    @command(name="CLIENT SETNAME", fixed=(bytes,), repeat=())
    def client_setname(self, value: bytes) -> SimpleString:
        self._client_info["name"] = value.decode("utf-8")
        return OK

    @command(name="CLIENT GETNAME", fixed=(), repeat=())
    def client_getname(self) -> bytes:
        name: str = self._client_info.get("name", "")
        return name.encode("utf-8")

    @command(name="CLIENT ID", fixed=(), repeat=())
    def client_getid(self) -> int:
        return int(self._client_info.get("id", 1))

    @command(name="CLIENT INFO", fixed=(), repeat=())
    def client_info_cmd(self) -> bytes:
        return self._client_info.as_bytes()

    @command(name="CLIENT LIST", fixed=(), repeat=(bytes,))
    def client_list_cmd(self, *args: bytes) -> bytes:
        sockets = self._server.sockets.copy()
        i = 0
        filter_ids = set()
        while i < len(args):
            if casematch(args[i], b"TYPE") and i + 1 < len(args):
                i += 2
            if casematch(args[i], b"ID") and i + 1 < len(args):
                i += 1
                while i < len(args):
                    filter_ids.add(Int.decode(args[i]))
                    i += 1
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if len(filter_ids) > 0:
            sockets = [sock for sock in sockets if sock._client_info["id"] in filter_ids]
        res = [item._client_info.as_bytes() for item in sockets]
        return b"\n".join(res)

    @command(name="HELLO", fixed=(), repeat=(bytes,))
    def hello(self, *args: bytes) -> dict[str, Any]:
        self._client_info["resp"] = 2 if len(args) == 0 else Int.decode(args[0])
        i = 1
        while i < len(args):
            if args[i] == b"SETNAME" and i + 1 < len(args):
                self._client_info["name"] = args[i + 1].decode("utf-8")
                i += 2
            elif args[i] == b"AUTH" and i + 2 < len(args):
                user = args[i + 1]
                password = args[i + 2]
                self._server.acl.get_user_acl(user).check_password(password)
                i += 3
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        data = {
            "server": "fakeredis",
            "version": fakeredis.__version__,
            "proto": self._client_info["resp"],
            "id": self._client_info.get("id", 1),
            "mode": "standalone",
            "role": "master",
            "modules": [],
        }
        return data

    @command(name="CLIENT MAINT_NOTIFICATIONS", fixed=(), repeat=(bytes,))
    def client_maint_notifications(self, *args: bytes) -> SimpleString:
        return OK

    @staticmethod
    def _parse_on_off(value: bytes) -> bool:
        if casematch(value, b"on"):
            return True
        if casematch(value, b"off"):
            return False
        raise SimpleError(msgs.SYNTAX_ERROR_MSG)

    def _update_client_flags(self) -> None:
        flags = ("e" if self._no_evict else "") + ("T" if self._no_touch else "")
        self._client_info["flags"] = flags or "N"

    @command(name="CLIENT NO-EVICT", fixed=(bytes,), repeat=())
    def client_no_evict(self, mode: bytes) -> SimpleString:
        self._no_evict = self._parse_on_off(mode)
        self._update_client_flags()
        return OK

    @command(name="CLIENT NO-TOUCH", fixed=(bytes,), repeat=())
    def client_no_touch(self, mode: bytes) -> SimpleString:
        self._no_touch = self._parse_on_off(mode)
        self._update_client_flags()
        return OK

    @command(name="CLIENT REPLY", fixed=(bytes,), repeat=())
    def client_reply(self, mode: bytes) -> SimpleString | NoResponse:
        if casematch(mode, b"on"):
            self._reply_off = self._reply_skip = self._reply_skip_next = False
            return OK
        if casematch(mode, b"off"):
            self._reply_off = True
            return NoResponse()
        if casematch(mode, b"skip"):
            # A pending OFF already suppresses everything, so SKIP is ignored.
            if not self._reply_off:
                self._reply_skip_next = True
            return NoResponse()
        raise SimpleError(msgs.SYNTAX_ERROR_MSG)

    @command(name="CLIENT PAUSE", fixed=(bytes,), repeat=(bytes,))
    def client_pause(self, timeout: bytes, *args: bytes) -> SimpleString:
        timeout_ms = Int.decode(timeout, msgs.CLIENT_PAUSE_TIMEOUT_NOT_INT_MSG)
        if timeout_ms < 0:
            raise SimpleError(msgs.TIMEOUT_NEGATIVE_MSG)
        mode = b"all"
        if len(args) > 1:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if len(args) == 1:
            if not casematch(args[0], b"write") and not casematch(args[0], b"all"):
                raise SimpleError(msgs.CLIENT_PAUSE_MODE_MSG)
            mode = args[0].lower()
        self._server.pause_until = time.time() + timeout_ms / 1000.0
        self._server.pause_mode = mode
        return OK

    @command(name="CLIENT UNPAUSE", fixed=(), repeat=())
    def client_unpause(self) -> SimpleString:
        self._server.pause_until = 0.0
        self._server.pause_mode = b"all"
        return OK

    @command(name="CLIENT UNBLOCK", fixed=(Int,), repeat=(bytes,))
    def client_unblock(self, client_id: int, *args: bytes) -> int:
        error = False
        if len(args) > 1:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if len(args) == 1:
            if casematch(args[0], b"error"):
                error = True
            elif not casematch(args[0], b"timeout"):
                raise SimpleError(msgs.CLIENT_UNBLOCK_REASON_MSG)
        for sock in list(self._server.sockets):
            if int(sock._client_info.get("id", 0)) != client_id or not sock._blocked:
                continue
            sock._unblock_reason = b"error" if error else b"timeout"
            sock._db.wake_all()
            return 1
        return 0

    @staticmethod
    def _client_type(sock: Any) -> bytes:
        return b"pubsub" if getattr(sock, "_pubsub", 0) else b"normal"

    @staticmethod
    def _client_age(sock: Any) -> int:
        return int(time.time()) - int(sock._client_info.get("-created", 0))

    def _parse_client_kill_filters(self, args: Sequence[bytes]) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        i = 0
        while i < len(args):
            if i + 1 >= len(args):
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            name, value = args[i], args[i + 1]
            if casematch(name, b"id"):
                # valkey rejects an unparsable id as a syntax error, redis reports it as
                # an out-of-range client-id.
                decode_error = (
                    msgs.SYNTAX_ERROR_MSG if self.server_type == "valkey" else msgs.CLIENT_KILL_INVALID_ID_MSG
                )
                client_id = Int.decode(value, decode_error)
                if client_id <= 0:
                    raise SimpleError(msgs.CLIENT_KILL_INVALID_ID_MSG)
                filters["client_id"] = client_id
            elif casematch(name, b"addr"):
                filters["addr"] = value
            elif casematch(name, b"laddr"):
                filters["laddr"] = value
            elif casematch(name, b"type"):
                if value.lower() not in CLIENT_KILL_TYPES:
                    raise SimpleError(msgs.CLIENT_KILL_UNKNOWN_TYPE_MSG.format(value.decode()))
                filters["client_type"] = value.lower()
            elif casematch(name, b"user"):
                if value not in self._server.acl.get_users():
                    raise SimpleError(msgs.CLIENT_KILL_NO_SUCH_USER_MSG.format(value.decode()))
                filters["user"] = value
            elif casematch(name, b"maxage"):
                maxage = Int.decode(value, msgs.CLIENT_KILL_INVALID_MAXAGE_MSG)
                if maxage <= 0:
                    raise SimpleError(msgs.CLIENT_KILL_MAXAGE_MSG)
                filters["maxage"] = maxage
            elif casematch(name, b"skipme"):
                filters["skipme"] = self._parse_yes_no(value)
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            i += 2
        return filters

    @staticmethod
    def _parse_yes_no(value: bytes) -> bool:
        if casematch(value, b"yes"):
            return True
        if casematch(value, b"no"):
            return False
        raise SimpleError(msgs.SYNTAX_ERROR_MSG)

    def _kill_clients(
        self,
        addr: bytes | None = None,
        laddr: bytes | None = None,
        client_id: int | None = None,
        client_type: bytes | None = None,
        user: bytes | None = None,
        maxage: int | None = None,
        skipme: bool = True,
    ) -> int:
        killed = 0
        for sock in list(self._server.sockets):
            info = sock._client_info
            if skipme and sock is self:
                continue
            if addr is not None and str(info.get("addr", "")).encode() != addr:
                continue
            if laddr is not None and str(info.get("laddr", "")).encode() != laddr:
                continue
            if client_id is not None and int(info.get("id", 0)) != client_id:
                continue
            if client_type is not None and self._client_type(sock) != client_type:
                continue
            if user is not None and info.user != user:
                continue
            if maxage is not None and self._client_age(sock) < maxage:
                continue
            sock.kill()
            killed += 1
        return killed

    @command(name="CLIENT KILL", fixed=(bytes,), repeat=(bytes,))
    def client_kill(self, *args: bytes) -> SimpleString | int:
        # The one-argument form is the old `CLIENT KILL addr:port` syntax, which reports
        # whether it killed anything rather than a count, and may kill the caller.
        if len(args) == 1:
            if self._kill_clients(addr=args[0], skipme=False) == 0:
                raise SimpleError(msgs.CLIENT_KILL_NO_SUCH_CLIENT_MSG)
            return OK
        return self._kill_clients(**self._parse_client_kill_filters(args))

    def _discard_subscriptions(self) -> None:
        """Drop every subscription without sending the usual unsubscribe confirmations."""
        subscriber_maps: list[dict[bytes, Any]] = [
            self._server.subscribers,
            self._server.psubscribers,
            self._server.ssubscribers,
        ]
        for subscribers in subscriber_maps:
            for channel in list(subscribers.keys()):
                subs: set[Any] = subscribers[channel]
                subs.discard(self)
                if not subs:
                    del subscribers[channel]
        self._pubsub = 0

    @command(name="RESET", fixed=(), repeat=(), flags=[msgs.FLAG_NO_SCRIPT, msgs.FLAG_TRANSACTION])
    def reset(self) -> SimpleString:
        self._transaction = None
        self._transaction_failed = False
        self._clear_watches()
        self._discard_subscriptions()
        self._reply_off = self._reply_skip = self._reply_skip_next = False
        self._no_evict = self._no_touch = False
        self._update_client_flags()
        self._client_info["name"] = ""
        self._client_info["resp"] = 2
        self._client_info["user"] = "default"
        self.select(0)
        return RESET
