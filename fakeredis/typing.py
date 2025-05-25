import sys

if sys.version_info >= (3, 11):
    from typing import Self
    from asyncio import timeout as async_timeout
else:
    from async_timeout import timeout as async_timeout
    from typing_extensions import Self

__all__ = [
    "Self",
    "async_timeout",
]
