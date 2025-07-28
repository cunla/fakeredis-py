import sys

if sys.version_info >= (3, 11):
    from typing import Self, Tuple, Literal
    from asyncio import timeout as async_timeout
else:
    from async_timeout import timeout as async_timeout
    from typing_extensions import Self
    from typing import Tuple, Literal

VersionType = Tuple[int, ...]
ServerType = Literal["redis", "dragonfly", "valkey"]

__all__ = [
    "Self",
    "async_timeout",
    "VersionType",
    "ServerType",
]
