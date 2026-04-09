from . import _typing
from ._connection import FakeRedis, FakeStrictRedis, FakeRedisConnection, FakeConnection
from ._server import FakeServer
from ._tcp_server import TcpFakeServer
from .aioredis import FakeRedis as FakeAsyncRedis, FakeAsyncRedisConnection, FakeConnection as FakeAsyncConnection

__version__ = _typing.lib_version
__author__ = "Daniel Moran"
__maintainer__ = "Daniel Moran"
__email__ = "daniel@moransoftware.ca"
__license__ = "BSD-3-Clause"
__url__ = "https://github.com/cunla/fakeredis-py"
__bugtrack_url__ = "https://github.com/cunla/fakeredis-py/issues"

__all__ = [
    "FakeServer",
    "FakeRedis",
    "FakeStrictRedis",
    "FakeRedisConnection",
    "FakeConnection",
    "FakeAsyncRedis",
    "FakeAsyncRedisConnection",
    "FakeAsyncConnection",
    "TcpFakeServer",
]

try:
    import valkey  # noqa: F401
    from ._valkey import FakeValkey, FakeAsyncValkey, FakeStrictValkey  # noqa: F401

    __all__.extend(
        [
            "FakeValkey",
            "FakeAsyncValkey",
            "FakeStrictValkey",
        ]
    )
except ImportError:
    pass
