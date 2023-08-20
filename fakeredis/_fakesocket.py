from fakeredis.stack import JSONCommandsMixin
from ._basefakesocket import BaseFakeSocket
from .commands_mixins.bitmap_mixin import BitmapCommandsMixin
from .commands_mixins.connection_mixin import ConnectionCommandsMixin
from .commands_mixins.generic_mixin import GenericCommandsMixin
from .commands_mixins.geo_mixin import GeoCommandsMixin
from .commands_mixins.hash_mixin import HashCommandsMixin
from .commands_mixins.list_mixin import ListCommandsMixin
from .commands_mixins.pubsub_mixin import PubSubCommandsMixin
from .commands_mixins.scripting_mixin import ScriptingCommandsMixin
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
):
    def __init__(self, server, db):
        super(FakeSocket, self).__init__(server, db)
