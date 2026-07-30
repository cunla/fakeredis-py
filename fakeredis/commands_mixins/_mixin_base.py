from __future__ import annotations

from typing import TYPE_CHECKING, Any

from fakeredis import _msgs as msgs
from fakeredis._helpers import SimpleError
from fakeredis._typing import ServerType, VersionType

if TYPE_CHECKING:
    from fakeredis._helpers import Database
    from fakeredis._server import FakeServer
    from fakeredis.model import ClientInfo

# Dragonfly refuses to store an expiry deadline more than 2**28-1 seconds away. A relative
# expiry (EXPIRE, PEXPIRE, SET EX) is silently clamped to that horizon, whereas an absolute
# one (EXPIREAT, PEXPIREAT) beyond it is rejected outright.
DRAGONFLY_MAX_EXPIRE_SECONDS = 2**28 - 1
# A hash field's TTL is capped more tightly still, and overshooting it is an error.
DRAGONFLY_MAX_HASH_EXPIRE_SECONDS = 2**26


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

    def _empty_blocking_reply(self, result: Any) -> Any:
        """Shape a timed-out array-returning blocking pop (BLPOP/BRPOP/BZPOPMIN/BZPOPMAX).

        Redis sends a null array, which RESP3 renders as nil. Dragonfly sends an empty
        array instead, so under RESP3 the client sees `[]` rather than `None`. Under RESP2
        both encode to `*-1` and the client sees `None` either way.
        """
        if result is None and self.server_type == "dragonfly" and self._client_info.protocol_version == 3:
            return []
        return result

    def _expiry_horizon(self) -> float:
        return self._db.time + DRAGONFLY_MAX_EXPIRE_SECONDS

    def _clamp_relative_expiry(self, timestamp: float) -> float:
        """Clamp a relative expiry deadline to what the server is willing to store."""
        if self.server_type != "dragonfly":
            return timestamp
        return min(timestamp, self._expiry_horizon())

    def _check_absolute_expiry(self, timestamp: float) -> None:
        """Reject an absolute expiry deadline the server considers too far in the future."""
        if self.server_type == "dragonfly" and timestamp > self._expiry_horizon():
            raise SimpleError(msgs.EXPIRY_OUT_OF_RANGE_MSG)
