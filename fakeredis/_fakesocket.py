from typing import Optional, Set

from fakeredis.stack import (
    JSONCommandsMixin,
    BFCommandsMixin,
    CFCommandsMixin,
    CMSCommandsMixin,
    TopkCommandsMixin,
    TDigestCommandsMixin,
)
from ._server import FakeServer
from ._basefakesocket import BaseFakeSocket
from .commands_mixins.bitmap_mixin import BitmapCommandsMixin
from .commands_mixins.connection_mixin import ConnectionCommandsMixin
from .commands_mixins.generic_mixin import GenericCommandsMixin
from .commands_mixins.geo_mixin import GeoCommandsMixin
from .commands_mixins.hash_mixin import HashCommandsMixin
from .commands_mixins.list_mixin import ListCommandsMixin
from .commands_mixins.pubsub_mixin import PubSubCommandsMixin

try:
    from .commands_mixins.scripting_mixin import ScriptingCommandsMixin
except ImportError:

    class ScriptingCommandsMixin:  # type: ignore  # noqa: E303
        def __init__(self, *args, **kwargs) -> None:
            kwargs.pop("lua_modules", None)
            super(ScriptingCommandsMixin, self).__init__(*args, **kwargs)


from .commands_mixins.server_mixin import ServerCommandsMixin
from .commands_mixins.set_mixin import SetCommandsMixin
from .commands_mixins.sortedset_mixin import SortedSetCommandsMixin
from .commands_mixins.streams_mixin import StreamsCommandsMixin
from .commands_mixins.string_mixin import StringCommandsMixin
from .commands_mixins.transactions_mixin import TransactionsCommandsMixin


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
):
    def __init__(
        self,
        server: "FakeServer",
        db: int,
        lua_modules: Optional[Set[str]] = None,  # type: ignore # noqa: F821
    ) -> None:
        super(FakeSocket, self).__init__(server, db, lua_modules=lua_modules)
