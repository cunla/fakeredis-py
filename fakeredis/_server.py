import inspect
import logging
import queue
import threading
import time
import warnings
import weakref
from collections import defaultdict
from typing import Dict, Tuple, Any, List, Optional, Union
import uuid

import redis

from fakeredis._fakesocket import FakeSocket
from fakeredis._helpers import Database, FakeSelector
from . import _msgs as msgs

LOGGER = logging.getLogger("fakeredis")

VersionType = Union[Tuple[int, ...], int, str]


def _create_version(v: VersionType) -> Tuple[int, ...]:
    if isinstance(v, tuple):
        return v
    if isinstance(v, int):
        return (v,)
    if isinstance(v, str):
        v_split = v.split(".")
        return tuple(int(x) for x in v_split)
    return v


class FakeServer:
    _servers_map: Dict[str, "FakeServer"] = dict()

    def __init__(self, version: VersionType = (7,)):
        self.lock = threading.Lock()
        self.dbs: Dict[int, Database] = defaultdict(lambda: Database(self.lock))
        # Maps channel/pattern to a weak set of sockets
        self.subscribers: Dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.psubscribers: Dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.ssubscribers: Dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.lastsave: int = int(time.time())
        self.connected = True
        # List of weakrefs to sockets that are being closed lazily
        self.closed_sockets: List[Any] = []
        self.version = _create_version(version)

    @staticmethod
    def get_server(key: str, version: VersionType) -> "FakeServer":
        return FakeServer._servers_map.setdefault(key, FakeServer(version=version))


class FakeBaseConnectionMixin(object):
    def __init__(self, *args: Any, version: VersionType = (7, 0), **kwargs: Any) -> None:
        self.client_name: Optional[str] = None
        self.server_key: str
        self._sock = None
        self._selector: Optional[FakeSelector] = None
        self._server = kwargs.pop("server", None)
        path = kwargs.pop("path", None)
        connected = kwargs.pop("connected", True)
        if self._server is None:
            if path:
                self.server_key = path
            else:
                host, port = kwargs.get("host"), kwargs.get("port")
                self.server_key = f"{host}:{port}"
            self.server_key += f":v{version}"
            self._server = FakeServer.get_server(self.server_key, version=version)
            self._server.connected = connected
        super().__init__(*args, **kwargs)


class FakeConnection(FakeBaseConnectionMixin, redis.Connection):
    def connect(self) -> None:
        super().connect()
        # The selector is set in redis.Connection.connect() after _connect() is called
        self._selector: Optional[FakeSelector] = FakeSelector(self._sock)

    def _connect(self) -> FakeSocket:
        if not self._server.connected:
            raise redis.ConnectionError(msgs.CONNECTION_ERROR_MSG)
        return FakeSocket(self._server, db=self.db)

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
            self, *args: Any,
            server: Optional[FakeServer] = None,
            version: VersionType = (7,),
            **kwargs: Any) -> None:
        # Interpret the positional and keyword arguments according to the
        # version of redis in use.
        parameters = list(inspect.signature(redis.Redis.__init__).parameters.values())[
                     1:
                     ]
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
                warnings.warn(
                    DeprecationWarning(
                        '"charset" is deprecated. Use "encoding" instead'
                    )
                )
                kwds["encoding"] = charset
            if errors is not None:
                warnings.warn(
                    DeprecationWarning(
                        '"errors" is deprecated. Use "encoding_errors" instead'
                    )
                )
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
            }
            connection_kwargs.update(
                {arg: kwds[arg] for arg in conn_pool_args if arg in kwds}
            )
            kwds["connection_pool"] = redis.connection.ConnectionPool(**connection_kwargs)  # type: ignore
        kwds.pop("server", None)
        kwds.pop("connected", None)
        kwds.pop("version", None)
        super().__init__(**kwds)

    @classmethod
    def from_url(cls, *args: Any, **kwargs: Any) -> "FakeRedisMixin":
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
