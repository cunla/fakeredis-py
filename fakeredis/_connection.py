import inspect
import queue
import sys
import uuid
import warnings
from typing import Tuple, Any, List, Optional, Set

from ._server import FakeBaseConnectionMixin, FakeServer, VersionType

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

import redis

from fakeredis._fakesocket import FakeSocket
from fakeredis._helpers import FakeSelector
from . import _msgs as msgs


class FakeConnection(FakeBaseConnectionMixin, redis.Connection):
    def connect(self) -> None:
        super().connect()
        # The selector is set in redis.Connection.connect() after _connect() is called
        self._selector: Optional[FakeSelector] = FakeSelector(self._sock)

    def _connect(self) -> FakeSocket:
        if not self._server.connected:
            raise redis.ConnectionError(msgs.CONNECTION_ERROR_MSG)
        return FakeSocket(self._server, db=self.db, lua_modules=self._lua_modules)

    def can_read(self, timeout: Optional[float] = 0) -> bool:
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

    def _decode(self, response: Any) -> Any:
        if isinstance(response, list):
            return [self._decode(item) for item in response]
        elif isinstance(response, bytes):
            return self.encoder.decode(response)
        else:
            return response

    def read_response(self, **kwargs: Any) -> Any:  # type: ignore
        if not self._sock:
            raise redis.ConnectionError(msgs.CONNECTION_ERROR_MSG)
        if not self._server.connected:
            try:
                response = self._sock.responses.get_nowait()
            except queue.Empty:
                if kwargs.get("disconnect_on_error", True):
                    self.disconnect()
                raise redis.ConnectionError(msgs.CONNECTION_ERROR_MSG)
        else:
            response = self._sock.responses.get()
        if isinstance(response, redis.ResponseError):
            raise response
        if kwargs.get("disable_decoding", False):
            return response
        else:
            return self._decode(response)

    def repr_pieces(self) -> List[Tuple[str, Any]]:
        pieces = [("server", self._server), ("db", self.db)]
        if self.client_name:
            pieces.append(("client_name", self.client_name))
        return pieces

    def __str__(self) -> str:
        return self.server_key


class FakeRedisMixin:
    def __init__(
        self,
        *args: Any,
        server: Optional[FakeServer] = None,
        version: VersionType = (7,),
        lua_modules: Optional[Set[str]] = None,
        **kwargs: Any,
    ) -> None:
        # Interpret the positional and keyword arguments according to the
        # version of redis in use.
        parameters = list(inspect.signature(redis.Redis.__init__).parameters.values())[1:]
        # Convert args => kwargs
        kwargs.update({parameters[i].name: args[i] for i in range(len(args))})
        kwargs.setdefault("host", uuid.uuid4().hex)
        kwds = {
            p.name: kwargs.get(p.name, p.default)
            for ind, p in enumerate(parameters)
            if p.default != inspect.Parameter.empty
        }
        if not kwds.get("connection_pool", None):
            charset = kwds.get("charset", None)
            errors = kwds.get("errors", None)
            # Adapted from redis-py
            if charset is not None:
                warnings.warn(DeprecationWarning('"charset" is deprecated. Use "encoding" instead'))
                kwds["encoding"] = charset
            if errors is not None:
                warnings.warn(DeprecationWarning('"errors" is deprecated. Use "encoding_errors" instead'))
                kwds["encoding_errors"] = errors
            conn_pool_args = {
                "host",
                "port",
                "db",
                # Ignoring because AUTH is not implemented
                # 'username',
                # 'password',
                "socket_timeout",
                "encoding",
                "encoding_errors",
                "decode_responses",
                "retry_on_timeout",
                "max_connections",
                "health_check_interval",
                "client_name",
                "connected",
            }
            connection_kwargs = {
                "connection_class": FakeConnection,
                "server": server,
                "version": version,
                "lua_modules": lua_modules,
            }
            connection_kwargs.update({arg: kwds[arg] for arg in conn_pool_args if arg in kwds})
            kwds["connection_pool"] = redis.connection.ConnectionPool(**connection_kwargs)  # type: ignore
        kwds.pop("server", None)
        kwds.pop("connected", None)
        kwds.pop("version", None)
        kwds.pop("lua_modules", None)
        super().__init__(**kwds)

    @classmethod
    def from_url(cls, *args: Any, **kwargs: Any) -> Self:
        pool = redis.ConnectionPool.from_url(*args, **kwargs)
        # Now override how it creates connections
        pool.connection_class = FakeConnection
        # Using username and password fails since AUTH is not implemented.
        # https://github.com/cunla/fakeredis-py/issues/9
        pool.connection_kwargs.pop("username", None)
        pool.connection_kwargs.pop("password", None)
        return cls(connection_pool=pool)


class FakeStrictRedis(FakeRedisMixin, redis.StrictRedis):  # type: ignore
    pass


class FakeRedis(FakeRedisMixin, redis.Redis):  # type: ignore
    pass
