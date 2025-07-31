import sys
from typing import Tuple, Literal, Union, Dict, Any, List

if sys.version_info >= (3, 11):
    from typing import Self
    from asyncio import timeout as async_timeout
else:
    from async_timeout import timeout as async_timeout
    from typing_extensions import Self

VersionType = Tuple[int, ...]
ServerType = Literal["redis", "dragonfly", "valkey"]
JsonType = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]

__all__ = [
    "Self",
    "async_timeout",
    "VersionType",
    "ServerType",
    "JsonType",
]
