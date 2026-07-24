from __future__ import annotations

import sys
from typing import Any, Dict, List, Literal, Tuple, Union

import redis
import redis.asyncio

if sys.version_info >= (3, 11):
    from asyncio import timeout as async_timeout
    from typing import Self
else:
    from async_timeout import timeout as async_timeout
    from typing_extensions import Self

try:
    from importlib import metadata
except ImportError:  # for Python < 3.8
    import importlib_metadata as metadata  # type: ignore

lib_version = metadata.version("fakeredis")
# These are evaluated at runtime (not annotations), so they must use typing
# aliases rather than PEP 585 builtins to remain importable on Python 3.8.
VersionType = Tuple[int, ...]
ServerType = Literal["redis", "dragonfly", "valkey"]
JsonType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]
RaiseErrorTypes: tuple[type[Exception], ...] = (redis.ResponseError, redis.AuthenticationError)
ResponseErrorType = redis.ResponseError
ClientType = redis.Redis
AsyncClientType = redis.asyncio.Redis
try:
    import valkey

    ClientType = Union[redis.Redis, valkey.Valkey]  # type: ignore[misc, assignment]
    AsyncClientType = Union[redis.asyncio.Redis, valkey.asyncio.Valkey]  # type: ignore[misc, assignment]
    RaiseErrorTypes = (redis.ResponseError, redis.AuthenticationError, valkey.ResponseError, valkey.AuthenticationError)
    ResponseErrorType = Union[redis.ResponseError, valkey.ResponseError]  # type: ignore[misc, assignment]
except ImportError:
    pass

__all__ = [
    "ClientType",
    "RaiseErrorTypes",
    "ResponseErrorType",
    "Self",
    "ServerType",
    "VersionType",
    "async_timeout",
    "lib_version",
]
