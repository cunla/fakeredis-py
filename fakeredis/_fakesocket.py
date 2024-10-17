from typing import Optional, Set

from fakeredis.commands_mixins import (
    BitmapCommandsMixin,
    ConnectionCommandsMixin,
    GenericCommandsMixin,
    GeoCommandsMixin,
    HashCommandsMixin,
    ListCommandsMixin,
    PubSubCommandsMixin,
    ScriptingCommandsMixin,
    ServerCommandsMixin,
    StringCommandsMixin,
    TransactionsCommandsMixin,
    SetCommandsMixin,
    StreamsCommandsMixin,
)
from fakeredis.stack import (
    JSONCommandsMixin,
    BFCommandsMixin,
    CFCommandsMixin,
    CMSCommandsMixin,
    TopkCommandsMixin,
    TDigestCommandsMixin,
    TimeSeriesCommandsMixin,
)
from ._basefakesocket import BaseFakeSocket
from ._server import FakeServer
from .commands_mixins.sortedset_mixin import SortedSetCommandsMixin
from .server_specific_commands import DragonflyCommandsMixin


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
):
    def __init__(
        self,
        server: "FakeServer",
        db: int,
        lua_modules: Optional[Set[str]] = None,  # noqa: F821
    ) -> None:
        super(FakeSocket, self).__init__(server, db, lua_modules=lua_modules)
