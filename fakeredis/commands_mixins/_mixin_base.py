from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

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

    def _blocking(
        self, timeout: float | None, func: Callable[[bool], Any], shape: Callable[[Any], Any] | None = None
    ) -> Any:
        """Implemented by the socket, sync and async alike; see `FakeSocket._blocking`."""
        raise NotImplementedError

    def _empty_blocking_reply(self, result: Any) -> Any:
        """Shape a timed-out array-returning blocking pop (BLPOP/BRPOP/BZPOPMIN/BZPOPMAX).

        Redis sends a null array, which RESP3 renders as nil. Dragonfly sends an empty array instead, so under RESP3 the
        client sees `[]` rather than `None`. Under RESP2 both encode to `*-1` and the client sees `None` either way.
        """
        if result is None and self.server_type == "dragonfly" and self._client_info.protocol_version == 3:
            return []
        return result
