"""The fake socket: parses requests, dispatches them to the command mixins, and queues the replies.

It sits between the command mixins below and the connections in ``fakeredis._clients`` above.
"""

from ._async import AsyncFakeSocket
from ._base import BaseFakeSocket
from ._fakesocket import FakeSocket

__all__ = ["AsyncFakeSocket", "BaseFakeSocket", "FakeSocket"]
