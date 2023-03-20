from ._server import FakeServer, FakeRedis, FakeRedisMixin, FakeStrictRedis, FakeConnection, FakeRedisConnSingleton

try:
    from importlib import metadata
except ImportError:  # for Python<3.8
    import importlib_metadata as metadata  # type: ignore
__version__ = metadata.version("fakeredis")


__all__ = ["FakeServer", "FakeRedis", "FakeRedisMixin", "FakeStrictRedis", "FakeConnection", "FakeRedisConnSingleton"]
