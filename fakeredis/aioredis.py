from __future__ import annotations

import asyncio
import threading
import warnings
from collections.abc import Iterable, Sequence
from typing import Any, Callable

import redis.asyncio as redis_async
from redis import ResponseError
from redis.asyncio.connection import DefaultParser

from . import _fakesocket, _helpers
from . import _msgs as msgs
from ._client_setup import build_client_kwds
from ._helpers import SimpleError
from ._server import FakeBaseConnectionMixin, FakeServer
from ._typing import RaiseErrorTypes, ServerType, VersionType, async_timeout, lib_version


class AsyncFakeSocket(_fakesocket.FakeSocket):
    _connection_error_class = redis_async.ConnectionError

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.responses: asyncio.Queue = asyncio.Queue()  # type:ignore
        # Set whenever a response is enqueued so can_read() can wait on it
        # instead of polling the queue (see can_read).
        self._response_available: asyncio.Event = asyncio.Event()
        self._event_loop = asyncio.get_running_loop()
        self._loop_thread_ident = threading.get_ident()

    def _decode_error(self, error: SimpleError) -> ResponseError:
        parser = DefaultParser(1)
        return parser.parse_error(error.value)

    def put_response(self, msg: Any) -> None:
        if not self.responses:
            return
        self.responses.put_nowait(msg)
        if threading.get_ident() == self._loop_thread_ident:
            self._response_available.set()
        else:
            # Called from another thread, e.g. a sync client publishing to a
            # channel this socket subscribes to on a shared FakeServer: a plain
            # set() would not wake this socket's sleeping event loop, so the
            # wakeup must be marshalled through it.
            try:
                self._event_loop.call_soon_threadsafe(self._response_available.set)
            except RuntimeError:  # the loop is already closed
                pass

    async def _async_blocking(
        self,
        timeout: float | None,
        func: Callable[[bool], Any],
        event: asyncio.Event,
        callback: Callable[[], None],
    ) -> None:
        result = None
        try:
            async with async_timeout(timeout if timeout else None):
                while True:
                    await event.wait()
                    event.clear()
                    # This is a coroutine outside the normal control flow that
                    # locks the server, so we have to take our own lock.
                    with self._server.lock:
                        if self._unblock_reason is not None:
                            try:
                                self._take_unblock_reason()
                            except SimpleError as exc:
                                result = self._decode_result(exc)
                            break
                        ret = func(False)
                        if ret is not None:
                            result = self._decode_result(ret)
                            break
        except asyncio.TimeoutError:
            pass
        finally:
            with self._server.lock:
                self._db.remove_change_callback(callback)
                self._blocked = False
                self._unblock_reason = None
            self.put_response(result)
            self.resume()

    def _blocking(
        self,
        timeout: float | None,
        func: Callable[[bool], None],
    ) -> Any:
        loop = asyncio.get_event_loop()
        ret = func(True)
        if ret is not None or self._in_transaction:
            return ret
        event = asyncio.Event()

        def callback() -> None:
            loop.call_soon_threadsafe(event.set)

        self._db.add_change_callback(callback)
        self._blocked = True
        self.pause()
        loop.create_task(self._async_blocking(timeout, func, event, callback))
        return _helpers.NoResponse()


class FakeReader:
    def __init__(self, socket: AsyncFakeSocket) -> None:
        self._socket = socket

    async def read(self, _: int) -> bytes:
        return await self._socket.responses.get()  # type:ignore

    def at_eof(self) -> bool:
        return self._socket.responses.empty() and not self._socket._server.connected


class FakeWriter:
    def __init__(self, socket: AsyncFakeSocket) -> None:
        self._socket: AsyncFakeSocket | None = socket

    def close(self) -> None:
        self._socket = None

    async def wait_closed(self) -> None:
        pass

    async def drain(self) -> None:
        pass

    def writelines(self, data: Iterable[Any]) -> None:
        if self._socket is None:
            return
        for chunk in data:
            self._socket.sendall(chunk)


class FakeBaseAsyncConnection(FakeBaseConnectionMixin):
    _connection_error_class = redis_async.ConnectionError

    async def _connect(self) -> None:
        if not self._server.connected:
            raise self._connection_error_class(msgs.CONNECTION_ERROR_MSG)
        self._sock: AsyncFakeSocket | None = AsyncFakeSocket(
            self._server, self.db, client_class=self._client_class, lua_modules=self._lua_modules
        )
        self._reader: FakeReader | None = FakeReader(self._sock)
        self._writer: FakeWriter | None = FakeWriter(self._sock)

    def __del__(self) -> None:
        # Ensure _writer is cleared even if disconnect() was never called
        # This prevents ResourceWarning on Python 3.13+ during garbage collection
        self._writer = None
        self._reader = None
        self._sock = None

    async def disconnect(self, nowait: bool = False, **kwargs: Any) -> None:
        # Clear these BEFORE calling super().disconnect() to prevent ResourceWarning
        self._sock = None
        self._reader = None
        self._writer = None
        await super().disconnect(**kwargs)

    async def can_read(self, timeout: float | None = 0) -> bool:
        if not self.is_connected:
            await self.connect()
        if timeout == 0:
            return self._sock is not None and not self._sock.responses.empty()
        # asyncio.Queue has no "wait until non-empty without consuming" API, so
        # wait on the socket's _response_available event (set by put_response)
        # rather than polling. timeout=None waits indefinitely.
        #
        # The event is only cleared here, never by the consumers that drain the
        # queue (responses.get / get_nowait), so "event set" does NOT imply
        # "queue non-empty" -- it may be left set after the queue was drained.
        # The recheck of empty() immediately after clear() is therefore
        # mandatory, not an optimization: it both closes the lost-wakeup race
        # (an item enqueued between the empty() check and the wait) and absorbs
        # a stale set. Do not remove it.
        loop = asyncio.get_event_loop()
        start = loop.time()
        while True:
            if self._sock is None:
                return False
            if not self._sock.responses.empty():
                return True
            self._sock._response_available.clear()
            if not self._sock.responses.empty():  # mandatory recheck, see above
                return True
            remaining = None if timeout is None else timeout - (loop.time() - start)
            if remaining is not None and remaining <= 0:
                return False
            try:
                await asyncio.wait_for(self._sock._response_available.wait(), remaining)
            except asyncio.TimeoutError:
                return False

    async def _get_from_local_cache(self, command: Sequence[str]) -> None:
        return None

    async def read_response(self, **kwargs: Any) -> Any:
        if not self._sock:
            raise self._connection_error_class(msgs.CONNECTION_ERROR_MSG)
        if not self._server.connected:
            try:
                response = self._sock.responses.get_nowait()
            except asyncio.QueueEmpty:
                if kwargs.get("disconnect_on_error", True):
                    await self.disconnect()
                raise self._connection_error_class(msgs.CONNECTION_ERROR_MSG)
        else:
            timeout: float | None = kwargs.pop("timeout", None)
            can_read = await self.can_read(timeout)
            response = await self._reader.read(0) if can_read and self._reader else None
        if isinstance(response, RaiseErrorTypes):
            raise response
        if kwargs.get("disable_decoding", False):
            return response
        return self._decode(response)


class FakeAsyncRedisConnection(FakeBaseAsyncConnection, redis_async.Connection):
    pass


class FakeAsyncRedisMixin:
    def __init__(
        self,
        *args: Any,
        server: FakeServer | None = None,
        version: VersionType | str | int = (7,),  # https://github.com/cunla/fakeredis-py/issues/401
        server_type: ServerType = "redis",
        lua_modules: set[str] | None = None,
        client_class: type[redis_async.Redis] = redis_async.Redis,
        connection_class: type[FakeBaseAsyncConnection] = FakeAsyncRedisConnection,
        connection_pool_class: type[redis_async.connection.ConnectionPool] = redis_async.connection.ConnectionPool,
        **kwargs: Any,
    ) -> None:
        connected = kwargs.pop("connected", True)
        kwds = build_client_kwds(
            *args,
            client_class=client_class,
            connection_class=connection_class,
            connection_pool_class=connection_pool_class,
            version=version,
            server_type=server_type,
            lua_modules=lua_modules,
            server=server,
            connected=connected,
            **kwargs,
        )
        if "lib_name" in kwds and "lib_version" in kwds and "driver_info" not in kwds:
            kwds["lib_name"] = "fakeredis"
            kwds["lib_version"] = lib_version
        if "driver_info" in kwds:
            from redis import DriverInfo

            kwds["driver_info"] = DriverInfo(name="fakeredis", lib_version=lib_version)
        super().__init__(**kwds)

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> FakeAsyncRedisMixin:
        self: redis_async.Redis = super().from_url(url, **kwargs)
        pool = self.connection_pool  # Now override how it creates connections
        pool.connection_class = kwargs.pop("connection_class", FakeAsyncRedisConnection)
        pool.connection_kwargs.setdefault("version", "7.4")
        pool.connection_kwargs.setdefault("server_type", "redis")
        return self


# Deprecated alias: kept so existing imports of aioredis.FakeRedisMixin keep
# working; it shadowed the (different) sync mixin of the same name in
# _connection.py.
FakeRedisMixin = FakeAsyncRedisMixin


class FakeRedis(FakeAsyncRedisMixin, redis_async.Redis):
    pass


def FakeConnection(*args: Any, **kwargs: Any) -> FakeAsyncRedisConnection:
    warnings.warn("FakeConnection is deprecated. Use FakeAsyncRedisConnection instead", DeprecationWarning, 2)
    return FakeAsyncRedisConnection(*args, **kwargs)


def FakeAsyncConnection(*args: Any, **kwargs: Any) -> FakeAsyncRedisConnection:
    warnings.warn("FakeAsyncConnection is deprecated. Use FakeAsyncRedisConnection instead", DeprecationWarning, 2)
    return FakeAsyncRedisConnection(*args, **kwargs)
