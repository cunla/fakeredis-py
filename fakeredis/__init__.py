from ._server import FakeServer, FakeRedis, FakeStrictRedis, FakeConnection   # noqa: F401


import importlib.metadata

__version__ = importlib.metadata.version('fakeredis')
