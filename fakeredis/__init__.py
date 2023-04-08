from ._server import FakeServer, FakeRedis, FakeStrictRedis, FakeConnection, FakeRedisConnSingleton
from .aioredis import (
    FakeServer as AsyncFakeServer,
    FakeRedis as AsyncFakeRedis,
    FakeConnection as AsyncFakeConntection
)

try:
    from importlib import metadata
except ImportError:  # for Python<3.8
    import importlib_metadata as metadata  # type: ignore
__version__ = metadata.version("fakeredis")


__all__ = ["FakeServer", "FakeRedis", "FakeStrictRedis", "FakeConnection", "FakeRedisConnSingleton",
           "AsyncFakeServer", "AsyncFakeRedis", "AsyncFakeConntection"]
