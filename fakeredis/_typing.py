import sys
from typing import Tuple, Union

if sys.version_info < (3, 8):
    from typing_extensions import Literal
else:
    from typing import Literal
if sys.version_info >= (3, 11):
    from typing import Self
    from asyncio import timeout as async_timeout
else:
    from async_timeout import timeout as async_timeout
    from typing_extensions import Self

try:
    from importlib import metadata
except ImportError:  # for Python < 3.8
    import importlib_metadata as metadata  # type: ignore

lib_version = metadata.version("fakeredis")
VersionType = Tuple[int, ...]
ServerType = Literal["redis", "dragonfly", "valkey"]

try:  # redis + valkey
    import valkey
    import redis

    RaiseErrorTypes = (redis.ResponseError, redis.AuthenticationError, valkey.ResponseError, valkey.AuthenticationError)
    ResponseErrorType = Union[redis.ResponseError, valkey.ResponseError]
except ImportError:
    try:  # redis only
        import redis

        RaiseErrorTypes = (redis.ResponseError, redis.AuthenticationError)
        ResponseErrorType = redis.ResponseError
    except ImportError:
        pass
    try:  # Valkey only
        import valkey

        RaiseErrorTypes = (valkey.ResponseError, valkey.AuthenticationError)
        ResponseErrorType = valkey.ResponseError
    except ImportError:
        pass

__all__ = [
    "Self",
    "async_timeout",
    "VersionType",
    "ServerType",
    "lib_version",
    "RaiseErrorTypes",
    "ResponseErrorType",
]
