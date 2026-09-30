from __future__ import annotations

from typing import Any

from fakeredis._core import FakeServer
from fakeredis._socket._base import BaseFakeSocket
from fakeredis.commands_mixins import (
    AclCommandsMixin,
    ArrayCommandsMixin,
    BitmapCommandsMixin,
    ConnectionCommandsMixin,
    GenericCommandsMixin,
    GeoCommandsMixin,
    HashCommandsMixin,
    ListCommandsMixin,
    PubSubCommandsMixin,
    ScriptingCommandsMixin,
    ServerCommandsMixin,
    SetCommandsMixin,
    StreamsCommandsMixin,
    StringCommandsMixin,
    TransactionsCommandsMixin,
)
from fakeredis.commands_mixins.sortedset_mixin import SortedSetCommandsMixin
from fakeredis.server_specific_commands import DragonflyCommandsMixin
from fakeredis.stack import (
    BFCommandsMixin,
    CFCommandsMixin,
    CMSCommandsMixin,
    JSONCommandsMixin,
    TDigestCommandsMixin,
    TimeSeriesCommandsMixin,
    TopkCommandsMixin,
    VectorSetCommandsMixin,
)


class FakeSocket(
    BaseFakeSocket,
    ArrayCommandsMixin,
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
    StreamsCommandsMixin,
    JSONCommandsMixin,
    GeoCommandsMixin,
    BFCommandsMixin,
    CFCommandsMixin,
    CMSCommandsMixin,
    TopkCommandsMixin,
    TDigestCommandsMixin,
    TimeSeriesCommandsMixin,
    DragonflyCommandsMixin,
    AclCommandsMixin,
    VectorSetCommandsMixin,
):
    def __init__(
        self,
        server: FakeServer,
        db: int,
        lua_modules: set[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(server, db, *args, lua_modules=lua_modules, **kwargs)
