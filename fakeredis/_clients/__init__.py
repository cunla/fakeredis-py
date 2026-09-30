"""Client-facing classes: the fake connections and the ``FakeRedis``-style clients built on them.

This is the top layer: it depends on the sockets and, through them, on every command mixin. Nothing below it may import
from here. The valkey clients live in ``_valkey`` and are not imported here, since valkey-py is an optional dependency.
"""

from ._async import FakeAsyncRedisConnection, FakeAsyncRedisMixin, FakeBaseAsyncConnection
from ._async import FakeRedis as FakeAsyncRedis
from ._base import FakeBaseConnectionMixin
from ._setup import build_client_kwds
from ._sync import (
    FakeBaseConnection,
    FakeConnection,
    FakeRedis,
    FakeRedisConnection,
    FakeRedisMixin,
    FakeStrictRedis,
)
from ._tcp_server import TcpFakeServer

__all__ = [
    "FakeAsyncRedis",
    "FakeAsyncRedisConnection",
    "FakeAsyncRedisMixin",
    "FakeBaseAsyncConnection",
    "FakeBaseConnection",
    "FakeBaseConnectionMixin",
    "FakeConnection",
    "FakeRedis",
    "FakeRedisConnection",
    "FakeRedisMixin",
    "FakeStrictRedis",
    "TcpFakeServer",
    "build_client_kwds",
]
