from __future__ import annotations

import queue
import warnings
from collections.abc import Sequence
from typing import Any

import redis

from fakeredis._client_setup import build_client_kwds
from fakeredis._fakesocket import FakeSocket
from fakeredis._helpers import FakeSelector

from . import _msgs as msgs
from ._server import FakeBaseConnectionMixin, FakeServer
from ._typing import RaiseErrorTypes, Self, ServerType, VersionType, lib_version


class FakeBaseConnection(FakeBaseConnectionMixin):
    _connection_error_class = redis.ConnectionError

    def connect(self) -> None:
        super().connect()  # type: ignore
        # The selector is set in redis.Connection.connect() after _connect() is called
        self._selector: FakeSelector | None = FakeSelector(self._sock)

    def activate_maint_notifications_handling_if_enabled(self, *args: Any, **kwargs: Any) -> None:
        # redis-py>=8.0 performs a real socket.getaddrinfo() DNS lookup here to determine the
        # endpoint type for RESP3 maintenance notifications. A fake server never sends those
        # notifications, so we skip the handshake entirely to avoid any real network calls.
        # See https://github.com/cunla/fakeredis-py/issues/513
        return None

    def _connect(self) -> FakeSocket:
        if not self._server.connected:
            raise self._connection_error_class(msgs.CONNECTION_ERROR_MSG)
        return FakeSocket(
            self._server,
            client_class=self._client_class,
            db=self.db,
            lua_modules=self._lua_modules,
            client_info=self._client_info,
        )

    def can_read(self, timeout: float | None = 0) -> bool:
        if not self._server.connected:
            return True
        if not self._sock:
            self.connect()
        # We use check_can_read rather than can_read, because on redis-py<3.2,
        # FakeSelector inherits from a stub BaseSelector which doesn't
        # implement can_read. Normally can_read provides retries on EINTR,
        # but that's not necessary for the implementation of
        # FakeSelector.check_can_read.
        return self._selector is not None and self._selector.check_can_read(timeout)

    def read_response(self, **kwargs: Any) -> Any:
        if not self._sock:
            raise self._connection_error_class(msgs.CONNECTION_ERROR_MSG)
        if not self._server.connected:
            try:
                response = self._sock.responses.get_nowait()
            except queue.Empty:
                if kwargs.get("disconnect_on_error", True):
                    self.disconnect()
                raise self._connection_error_class(msgs.CONNECTION_ERROR_MSG)
        else:
            response = self._sock.responses.get()

        if isinstance(response, RaiseErrorTypes):
            raise response
        res = response if kwargs.get("disable_decoding", False) else self._decode(response)
        return res

    def _get_from_local_cache(self, command: Sequence[str]) -> None:
        return None

    def get_socket(self) -> FakeSocket:
        if not self._sock:
            self.connect()
        return self._sock  # type: ignore


class FakeRedisConnection(FakeBaseConnection, redis.Connection):
    _connection_error_class = redis.ConnectionError


def FakeConnection(*args: Any, **kwargs: Any) -> FakeRedisConnection:
    warnings.warn("FakeConnection is deprecated. Use FakeRedisConnection instead", DeprecationWarning, 2)
    return FakeRedisConnection(*args, **kwargs)


class FakeRedisMixin:
    def __init__(
        self,
        *args: Any,
        server: FakeServer | None = None,
        version: VersionType | str | int = (7,),  # https://github.com/cunla/fakeredis-py/issues/401
        server_type: ServerType = "redis",
        lua_modules: set[str] | None = None,
        client_class: type[redis.Redis] = redis.Redis,
        connection_class: type[FakeBaseConnection] = FakeRedisConnection,
        connection_pool_class: type[redis.ConnectionPool] = redis.ConnectionPool,
        **kwargs: Any,
    ) -> None:
        """
        :param server: The FakeServer instance to use for this connection.
        :param version: The Redis version to use, as a tuple (major, minor).
        :param server_type: The type of server, e.g., "redis", "valkey".
        :param lua_modules: A set of Lua modules to load.
        :param client_class: The Redis client class to use, e.g., redis.Redis or valkey.Valkey.
        """
        # Sync clients ignore the `connected` flag, preserving historical behavior.
        kwargs.pop("connected", None)
        kwds = build_client_kwds(
            *args,
            client_class=client_class,
            connection_class=connection_class,
            connection_pool_class=connection_pool_class,
            version=version,
            server_type=server_type,
            lua_modules=lua_modules,
            server=server,
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
    def from_url(cls, *args: Any, **kwargs: Any) -> Self:
        kwargs.setdefault("version", "7.4")
        kwargs.setdefault("server_type", "redis")
        connection_pool_class = kwargs.pop("connection_pool_class", redis.ConnectionPool)
        pool = connection_pool_class.from_url(*args, **kwargs)
        # Now override how it creates connections
        pool.connection_class = kwargs.get("connection_class", FakeRedisConnection)
        return cls(*args, connection_pool=pool, **kwargs)


class FakeStrictRedis(FakeRedisMixin, redis.StrictRedis):
    pass


class FakeRedis(FakeRedisMixin, redis.Redis):
    pass
