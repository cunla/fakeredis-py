from __future__ import annotations

import asyncio
import warnings
from collections.abc import Iterable, Sequence
from typing import Any

import redis.asyncio as redis_async

from fakeredis import _msgs as msgs
from fakeredis._clients._base import FakeBaseConnectionMixin
from fakeredis._clients._setup import build_client_kwds
from fakeredis._core import FakeServer
from fakeredis._socket import AsyncFakeSocket
from fakeredis._typing import RaiseErrorTypes, Self, ServerType, VersionType


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
            self._server,
            self.db,
            client_class=self._client_class,
            lua_modules=self._lua_modules,
            client_info=self._client_info,
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
        # asyncio.Queue has no "wait until non-empty without consuming" API, so wait on the socket's _response_available
        # event (set by put_response) rather than polling. timeout=None waits indefinitely.
        #
        # The event is only cleared here, never by the consumers that drain the queue (responses.get / get_nowait), so
        # "event set" does NOT imply "queue non-empty" -- it may be left set after the queue was drained. The recheck of
        # empty() immediately after clear() is therefore mandatory, not an optimization: it both closes the lost-wakeup
        # race (an item enqueued between the empty() check and the wait) and absorbs a stale set. Do not remove it.
        loop = asyncio.get_running_loop()
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
        try:
            response = await self._read_response(**kwargs)
        except BaseException:
            # redis-py's own read_response closes the connection on any BaseException, cancellation included, so that a
            # half-consumed command/reply pair never goes back to the pool. Without it, cancelling a blocking command
            # hands the socket back still paused and mid-block, and every later command on it hangs.
            #
            # Like redis-py, this covers only the read itself: an error *reply* is raised below, outside the guard, so a
            # WRONGTYPE or the like propagates without tearing the connection down.
            if kwargs.get("disconnect_on_error", True):
                await self.disconnect(nowait=True)
            raise
        if isinstance(response, RaiseErrorTypes):
            raise response
        if kwargs.get("disable_decoding", False):
            return response
        return self._decode(response)

    async def _read_response(self, **kwargs: Any) -> Any:
        if not self._sock:
            raise self._connection_error_class(msgs.CONNECTION_ERROR_MSG)
        if not self._server.connected:
            try:
                return self._sock.responses.get_nowait()
            except asyncio.QueueEmpty:
                if kwargs.get("disconnect_on_error", True):
                    await self.disconnect()
                raise self._connection_error_class(msgs.CONNECTION_ERROR_MSG)
        timeout: float | None = kwargs.pop("timeout", None)
        can_read = await self.can_read(timeout)
        return await self._reader.read(0) if can_read and self._reader else None


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
        super().__init__(**kwds)

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> Self:
        self: Self = super().from_url(url, **kwargs)  # type: ignore[misc]
        pool = self.connection_pool  # type: ignore[attr-defined]  # Now override how it creates connections
        pool.connection_class = kwargs.pop("connection_class", FakeAsyncRedisConnection)
        pool.connection_kwargs.setdefault("version", "7.4")
        pool.connection_kwargs.setdefault("server_type", "redis")
        return self


# Deprecated alias: kept so existing imports of aioredis.FakeRedisMixin keep working; it shadowed the (different) sync
# mixin of the same name in _sync.py.
FakeRedisMixin = FakeAsyncRedisMixin


class FakeRedis(FakeAsyncRedisMixin, redis_async.Redis):
    pass


def FakeConnection(*args: Any, **kwargs: Any) -> FakeAsyncRedisConnection:
    warnings.warn("FakeConnection is deprecated. Use FakeAsyncRedisConnection instead", DeprecationWarning, 2)
    return FakeAsyncRedisConnection(*args, **kwargs)


def FakeAsyncConnection(*args: Any, **kwargs: Any) -> FakeAsyncRedisConnection:
    warnings.warn("FakeAsyncConnection is deprecated. Use FakeAsyncRedisConnection instead", DeprecationWarning, 2)
    return FakeAsyncRedisConnection(*args, **kwargs)
