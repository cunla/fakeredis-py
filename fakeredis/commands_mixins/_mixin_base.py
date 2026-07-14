from __future__ import annotations

from typing import TYPE_CHECKING

from fakeredis._typing import ServerType, VersionType

if TYPE_CHECKING:
    from fakeredis._helpers import Database
    from fakeredis._server import FakeServer
    from fakeredis.model import ClientInfo


class CommandsMixinBase:
    """Base class for command mixins that declares shared read-only attributes."""

    _server: FakeServer
    _client_info: ClientInfo
    _db: Database

    @property
    def version(self) -> VersionType:
        raise NotImplementedError

    @property
    def server_type(self) -> ServerType:
        raise NotImplementedError
