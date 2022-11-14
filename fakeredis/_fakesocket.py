"""FakeRedis's internal emulation of a Redis server socket."""

# Future Imports
from __future__ import annotations

# Standard Library Imports
from typing import (
    TYPE_CHECKING,
    ForwardRef,
    Type,
)

# Third-Party Imports
import redis

# Imports From Package Sub-Modules
from ._basefakesocket import BaseFakeSocket
from .commands_mixins.bitmap_mixin import BitmapCommandsMixin
from .commands_mixins.connection_mixin import ConnectionCommandsMixin
from .commands_mixins.generic_mixin import GenericCommandsMixin
from .commands_mixins.hash_mixin import HashCommandsMixin
from .commands_mixins.json_mixin import JSONCommandsMixin
from .commands_mixins.list_mixin import ListCommandsMixin
from .commands_mixins.pubsub_mixin import PubSubCommandsMixin
from .commands_mixins.scripting_mixin import ScriptingCommandsMixin
from .commands_mixins.server_mixin import ServerCommandsMixin
from .commands_mixins.set_mixin import SetCommandsMixin
from .commands_mixins.sortedset_mixin import SortedSetCommandsMixin
from .commands_mixins.string_mixin import StringCommandsMixin
from .commands_mixins.transactions_mixin import TransactionsCommandsMixin

if TYPE_CHECKING:
    # Package-Level Imports
    from fakeredis import FakeServer
else:
    FakeServer = ForwardRef("fakeredis.FakeServer")


class FakeSocket(
    BaseFakeSocket,
    GenericCommandsMixin,
    ScriptingCommandsMixin,
    HashCommandsMixin,
    ConnectionCommandsMixin,
    ListCommandsMixin,
    ServerCommandsMixin,
    StringCommandsMixin,
    TransactionsCommandsMixin,
    PubSubCommandsMixin,
    SetCommandsMixin,
    BitmapCommandsMixin,
    SortedSetCommandsMixin,
    JSONCommandsMixin,
):
    """An emulated Redis server socket."""

    _connection_error_class: Type[Exception] = redis.ConnectionError

    def __init__(self, server: FakeServer) -> None:
        super(FakeSocket, self).__init__(server)
