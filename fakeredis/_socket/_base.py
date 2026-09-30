from __future__ import annotations

import itertools
import queue
import threading
import time
import weakref
from collections.abc import Generator
from typing import Any, AnyStr, Callable, ClassVar

import redis

from fakeredis import _msgs as msgs
from fakeredis._commands import SUPPORTED_COMMANDS, Signature
from fakeredis._core import CommandItem, FakeServer
from fakeredis._helpers import QUEUED, NoResponse, SimpleError, SimpleString
from fakeredis._socket._dragonfly import (
    DRAGONFLY_NO_SCRIPT_COMMANDS,
    DRAGONFLY_NO_TRANSACTION_COMMANDS,
    dirty_watched_keys,
)
from fakeredis._socket._notifications import NotificationsMixin
from fakeredis._socket._resp import convert_to_resp2, extract_command, valid_response_type
from fakeredis._typing import ResponseErrorType, ServerType, VersionType
from fakeredis.model import ClientInfo

_file_no_counter = itertools.count(8)


def _get_next_file_no() -> int:
    return next(_file_no_counter)


class BaseFakeSocket(NotificationsMixin):
    _clear_watches: Callable[[], None]
    abort_transaction: Callable[[], None]
    _forget_transaction: Callable[[], None]
    _queueing: bool
    ACCEPTED_COMMANDS_WHILE_PUBSUB: ClassVar[set[str]] = {
        "ping",
        "subscribe",
        "unsubscribe",
        "psubscribe",
        "punsubscribe",
        "ssubscribe",
        "sunsubscribe",
        "reset",
    }
    _connection_error_class = redis.ConnectionError

    def __init__(
        self,
        server: FakeServer,
        db: int,
        client_class: type,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # Copied: the connection passes in its own ClientInfo, which must not pick up this socket's id.
        info = dict(kwargs.pop("client_info", None) or {})
        super().__init__(*args, **kwargs)
        self._server: FakeServer = server
        self._fileno = _get_next_file_no()
        self._db_num = db
        self._db = server.dbs[self._db_num]
        self._client_class = client_class
        self.responses: queue.Queue[bytes] | None = queue.Queue()
        # Set whenever a response is queued or the socket closes, so FakeSelector can wait for one instead of polling.
        self.response_ready = threading.Event()
        # Prevents parser from processing commands. Not used in this module, but set by aioredis module to prevent new
        # commands being processed while handling a blocking command.
        self._paused = False
        # Set by CLIENT KILL. The owning client only notices when it next writes, matching a real server closing the
        # connection underneath it.
        self._killed = False
        # CLIENT REPLY state, mirroring redis' CLIENT_REPLY_OFF/SKIP/SKIP_NEXT flags.
        self._reply_off = False
        self._reply_skip = False
        self._reply_skip_next = False
        # CLIENT NO-EVICT / CLIENT NO-TOUCH, reported in the CLIENT INFO flags field.
        self._no_evict = False
        self._no_touch = False
        # Set while parked in _blocking, so CLIENT UNBLOCK can tell whether this client is blocked and, if so, how it
        # should be woken.
        self._blocked = False
        self._unblock_reason: bytes | None = None
        self._subkey_events = []
        self._parser = self._parse_commands()
        self._parser.send(None)
        # Assigned elsewhere
        self._transaction: list[Any] | None
        self._in_transaction: bool
        self._pubsub: int
        self._transaction_failed: bool
        self._transaction_paused: bool
        info["id"] = self._server.get_next_client_id()
        self._client_info = ClientInfo(**info)
        self._server.sockets.append(self)

    @property
    def current_user(self) -> bytes:
        return self._client_info.user

    @property
    def version(self) -> VersionType:
        return self._server.version

    @property
    def server_type(self) -> ServerType:
        return self._server.server_type

    def put_response(self, msg: Any) -> None:
        """Put a response message into the queue of responses.

        :param msg: The response message.
        """
        # redis.Connection.__del__ might call self.close at any time, which will set self.responses to None. We assume
        # this will happen atomically, and the code below then protects us against this.
        responses = self.responses
        if responses:
            responses.put(msg)
            self.response_ready.set()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False
        self._parser.send(b"")

    def shutdown(self, _: Any) -> None:
        self._parser.close()

    def fileno(self) -> int:
        return self._fileno

    def _cleanup(self, server: Any) -> None:
        """Remove all the references to `self` from `server`.

        This is called with the server lock held, but it may be some time after self.close.
        """
        for subs in server.subscribers.values():
            subs.discard(self)
        for subs in server.psubscribers.values():
            subs.discard(self)
        self._clear_watches()

    def kill(self) -> None:
        """Disconnect this socket on behalf of CLIENT KILL, from any connection.

        The socket is dropped from the server immediately, so it stops showing up in CLIENT LIST and stops receiving
        published messages, but the queued responses are left intact: a client that killed itself still has to read the
        reply to the CLIENT KILL itself. Called with the server lock held.
        """
        self._killed = True
        try:
            self._server.sockets.remove(self)
        except ValueError:  # already closed by its owner
            pass
        self._cleanup(self._server)

    def close(self) -> None:
        # Mark ourselves for cleanup. This might be called from redis.Connection.__del__, which the garbage collection
        # could call at any time, and hence we can't safely take the server lock. We rely on list.append being atomic.
        try:
            self._server.sockets.remove(self)
        except ValueError:  # already removed by CLIENT KILL
            pass
        self._server.closed_sockets.append(weakref.ref(self))
        self._server = None  # type: ignore
        self._db = None  # type: ignore
        self.responses = None
        # Wake a FakeSelector waiting for a response that will now never come.
        self.response_ready.set()

    def _unknown_command(self, command: str, args: str | None = None) -> SimpleError:
        """Build the server's "unknown command" error.

        Dragonfly uses its own wording and never echoes the arguments back, and KiviDB names nothing at all, so
        `args` is only appended for the Redis/Valkey format.
        """
        if self._server.server_type == "dragonfly":
            return SimpleError(msgs.DRAGONFLY_UNKNOWN_COMMAND_MSG.format(command.upper()))
        if self._server.server_type == "kividb":
            return SimpleError(msgs.KIVIDB_UNKNOWN_COMMAND_MSG)
        msg = msgs.UNKNOWN_COMMAND_MSG.format(command)
        if args is not None:
            msg += f"'{args}' "
        return SimpleError(msg)

    def _extract_line(self, buf: bytes) -> tuple[bytes, bytes]:
        pos = buf.find(b"\n") + 1
        if pos <= 0:
            raise self._unknown_command(buf.decode().strip())
        line = buf[:pos]
        buf = buf[pos:]
        if not line.endswith(b"\r\n"):
            parts = line.decode().strip().split(" ", 1)
            command = parts[0]
            args = parts[1] if len(parts) > 1 else ""
            raise self._unknown_command(command, args)
        return line, buf

    def _parse_commands(self) -> Generator[None, Any, None]:
        """Generator that parses commands.

        It is fed pieces of redis protocol data (via `send`) and calls
        `_process_command` whenever it has a complete one.
        """
        buf = b""
        while True:
            while self._paused or b"\n" not in buf:
                buf += yield
            line, buf = self._extract_line(buf)
            if not line[:1] == b"*":  # array
                raise self._unknown_command(buf.decode().strip())
            n_fields = int(line[1:-2])
            fields = []
            for i in range(n_fields):
                while b"\n" not in buf:
                    buf += yield
                line, buf = self._extract_line(buf)
                if line[:1] != b"$":
                    raise self._unknown_command(buf.decode().strip())
                length = int(line[1:-2])
                while len(buf) < length + 2:
                    buf += yield
                fields.append(buf[:length])
                buf = buf[length + 2 :]  # +2 to skip the CRLF
            self._process_command(fields)

    def _process_command(self, fields: list[bytes]) -> None:
        if not fields:
            return
        result: Any
        cmd, cmd_arguments = extract_command(fields)
        from_run_command = False
        unknown_command = False
        try:
            try:
                func, sig = self._name_to_func(cmd)
            except SimpleError:
                unknown_command = True
                raise
            # ACL check
            self._server.acl.validate_command(self._client_info.user, self._client_info.as_bytes(), fields)
            with self._server.lock:
                # Clean out old connections
                while True:
                    try:
                        weak_sock = self._server.closed_sockets.pop()
                    except IndexError:
                        break
                    else:
                        sock = weak_sock()
                        if sock:
                            sock._cleanup(self._server)
                now = time.time()
                for db in self._server.dbs.values():
                    db.time = now
                sig.check_arity(cmd_arguments, self.version)
                if self._queueing and self._transaction is not None and msgs.FLAG_TRANSACTION not in sig.flags:
                    if self.server_type == "dragonfly" and cmd in DRAGONFLY_NO_TRANSACTION_COMMANDS:
                        raise SimpleError(msgs.DRAGONFLY_NOT_IN_TRANSACTION_MSG.format(cmd.upper()))
                    self._transaction.append((func, sig, cmd_arguments))
                    result = QUEUED
                else:
                    from_run_command = True
                    result = self._run_command(func, sig, cmd_arguments, False)
        except SimpleError as exc:
            if self._queueing and not from_run_command:
                if self.server_type != "dragonfly":
                    self._transaction_failed = True
                elif not unknown_command:
                    # Dragonfly stops queueing as soon as a command fails to queue, rather than queueing on and refusing
                    # the EXEC. An unknown command is the one exception: there the transaction carries on unharmed.
                    self.abort_transaction()
            if cmd == "exec" and exc.value.startswith("ERR "):
                exc.value = "EXECABORT Transaction discarded because of: " + exc.value[4:]
                self._forget_transaction()
                self._clear_watches()
            result = exc
        result = self._decode_result(result)
        suppressed = self._reply_off or self._reply_skip
        # Mirror redis' resetClient(): the SKIP armed by CLIENT REPLY SKIP takes effect on the command *after* it, then
        # clears itself.
        self._reply_skip, self._reply_skip_next = self._reply_skip_next, False
        if suppressed or isinstance(result, NoResponse):
            return
        self.put_response(result)

    def _run_command(
        self, func: Callable[[Any], Any] | None, sig: Signature, args: list[Any], from_script: bool
    ) -> Any:
        command_items: list[CommandItem] = []
        self._subkey_events = []
        is_dragonfly = self.server_type == "dragonfly"
        try:
            ret = sig.apply(args, self._db, self.version)
            if from_script and (
                msgs.FLAG_NO_SCRIPT in sig.flags or (is_dragonfly and sig.name in DRAGONFLY_NO_SCRIPT_COMMANDS)
            ):
                raise SimpleError(msgs.DRAGONFLY_COMMAND_IN_SCRIPT_MSG if is_dragonfly else msgs.COMMAND_IN_SCRIPT_MSG)
            if self._pubsub and sig.name not in BaseFakeSocket.ACCEPTED_COMMANDS_WHILE_PUBSUB:
                raise SimpleError(msgs.BAD_COMMAND_IN_PUBSUB_MSG)
            if len(ret) == 1:
                result = ret[0]
            else:
                args, command_items = ret
                result = func(*args)  # type: ignore
                resp_version = self._resp_version
                if resp_version == 2 and msgs.FLAG_SKIP_CONVERT_TO_RESP2 not in sig.flags:
                    result = convert_to_resp2(
                        result,
                        self.server_type,
                        # Dragonfly gives a script's `redis.call` a double as a Lua number whatever protocol the client
                        # that invoked the script speaks.
                        keep_doubles=from_script and is_dragonfly,
                    )
                if msgs.FLAG_SKIP_CONVERT_TO_RESP2 not in sig.flags and not valid_response_type(result, resp_version):
                    raise AssertionError(f"Invalid response type for {result}")
        except SimpleError as exc:
            result = exc
        for command_item in command_items:
            command_item.writeback(remove_empty_val=msgs.FLAG_LEAVE_EMPTY_VAL not in sig.flags)
        if is_dragonfly:
            dirty_watched_keys(self._db, sig, command_items)
        self._keyspace_notifications(command_items, sig.name.encode())
        self._subkey_notifications(command_items)
        return result

    def _decode_error(self, error: SimpleError) -> ResponseErrorType:
        if self._client_class.__module__.startswith("valkey"):
            from valkey.connection import DefaultParser as ValkeyDefaultParser

            return ValkeyDefaultParser(socket_read_size=65536).parse_error(error.value)  # type: ignore
        else:
            from redis.connection import DefaultParser as RedisDefaultParser

            return RedisDefaultParser(socket_read_size=65536).parse_error(error.value)  # type: ignore

    def _decode_result(self, result: Any) -> Any:
        """Convert SimpleString and SimpleError, recursively"""
        if isinstance(result, list):
            return [self._decode_result(r) for r in result]
        elif isinstance(result, SimpleString):
            return result.value
        elif isinstance(result, SimpleError):
            return self._decode_error(result)
        else:
            return result

    def _blocking(
        self, timeout: float | None, func: Callable[[bool], Any], shape: Callable[[Any], Any] | None = None
    ) -> Any:
        """Run a function until it succeeds or timeout is reached.

        The timeout is in seconds, and 0 means infinite. The function is called with a boolean to indicate whether this
        is the first call. If it returns None, it is considered to have "failed" and is retried each time the condition
        variable is notified, until the timeout is reached.

        `shape` turns the outcome into the reply the command sends, the timed-out None
        included. It belongs here rather than around the call because the async socket answers a command that blocks
        outside the command's own control flow, so anything the command does with the return value would be skipped
        there. The timed-out reply is shaped when the timeout fires, so it can report what is there by then (TS.READ).

        Returns the function return value, or None if the timeout has passed.
        """
        ret = func(True)  # Call with first_pass=True
        if ret is not None or self._in_transaction:
            return ret if shape is None else shape(ret)

        def empty() -> Any:
            return None if shape is None else shape(None)

        deadline = time.time() + timeout if timeout else None
        self._blocked = True
        try:
            while True:
                timeout = (deadline - time.time()) if deadline is not None else None
                if timeout is not None and timeout <= 0:
                    return empty()
                if self._db.condition.wait(timeout=timeout) is False:
                    return empty()  # Timeout expired
                if self._unblock_reason is not None:
                    self._take_unblock_reason()
                    return empty()  # Unblocked with TIMEOUT: same empty result as a timeout
                ret = func(False)  # Second pass => first_pass=False
                if ret is not None:
                    return ret if shape is None else shape(ret)
        finally:
            self._blocked = False
            self._unblock_reason = None

    def _take_unblock_reason(self) -> None:
        """Consume a pending CLIENT UNBLOCK request, raising if it asked for ERROR."""
        reason, self._unblock_reason = self._unblock_reason, None
        if reason == b"error":
            raise SimpleError(msgs.UNBLOCKED_MSG)

    def _name_to_func(self, cmd_name: str) -> tuple[Callable[[Any], Any] | None, Signature]:
        """Get the signature and the method from the command name."""
        if cmd_name not in SUPPORTED_COMMANDS:
            # redis remaps \r or \n in an error to ' ' to make it legal protocol
            clean_name = cmd_name.replace("\r", " ").replace("\n", " ")
            raise self._unknown_command(clean_name)
        sig = SUPPORTED_COMMANDS[cmd_name]
        if self._server.server_type not in sig.server_types:
            # redis remaps \r or \n in an error to ' ' to make it legal protocol
            clean_name = cmd_name.replace("\r", " ").replace("\n", " ")
            raise self._unknown_command(clean_name)
        func = getattr(self, sig.func_name, None)
        return func, sig

    def sendall(self, data: AnyStr) -> None:
        if not self._server.connected or self._killed:
            raise self._connection_error_class(msgs.CONNECTION_ERROR_MSG)
        if isinstance(data, str):
            data = data.encode("ascii")  # type: ignore
        self._parser.send(data)
