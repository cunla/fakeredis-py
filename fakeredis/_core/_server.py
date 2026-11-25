from __future__ import annotations

import logging
import secrets
import threading
import time
import weakref
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from typing import Any, ClassVar

from fakeredis._core._database import Database
from fakeredis._typing import ServerType, VersionType
from fakeredis.model import AccessControlList

LOGGER = logging.getLogger("fakeredis")


def _create_version(v: tuple[int, ...] | int | str) -> VersionType:
    if isinstance(v, tuple):
        return v
    if isinstance(v, int):
        return (v,)
    if isinstance(v, str):
        v_split = v.split(".")
        return tuple(int(x) for x in v_split)
    raise ValueError(f"Unsupported version: {v}")


# Valkey keeps reporting the Redis version it forked from, whatever its own version.
_VALKEY_REDIS_VERSION: VersionType = (7, 2, 4)
# A fake Dragonfly or KiviDB server is built with the Redis version it emulates, so fakeredis has no product version to
# report for it. One is still given: clients tell these servers apart by whether it is there.
_UNKNOWN_PRODUCT_VERSION: VersionType = (0, 0, 0)


@dataclass(frozen=True)
class ServerDetails:
    """What a server says about itself (in INFO SERVER): its type, the Redis version it reports, and its own version.

    Mirrors `ServerDetails` in `test/conftest.py`, which reads the same fields from a real server.
    """

    server_type: ServerType
    redis_version: VersionType
    valkey_version: VersionType | None = None
    dragonfly_version: VersionType | None = None
    kividb_version: VersionType | None = None

    @classmethod
    def create(cls, server_type: ServerType, version: VersionType) -> ServerDetails:
        """The details of a `FakeServer` built with `server_type` and `version`.

        `version` is Valkey's own version for Valkey, and the Redis version emulated for every other server type.
        """
        if server_type == "valkey":
            return cls(server_type, _VALKEY_REDIS_VERSION, valkey_version=version)
        if server_type == "dragonfly":
            return cls(server_type, version, dragonfly_version=_UNKNOWN_PRODUCT_VERSION)
        if server_type == "kividb":
            return cls(server_type, version, kividb_version=_UNKNOWN_PRODUCT_VERSION)
        return cls(server_type, version)

    @property
    def server_version(self) -> VersionType:
        """The version a `FakeServer` is built with, as in `create`."""
        return self.valkey_version if self.valkey_version is not None else self.redis_version


class FakeServer:
    _servers_map: ClassVar[dict[str, FakeServer]] = {}

    def __init__(
        self,
        version: VersionType = (8,),
        server_type: ServerType = "redis",
        config: dict[bytes, bytes] | None = None,
    ) -> None:
        """Initialize a new FakeServer instance.
        :param version: The version of the server (e.g. 6, 7.4, "7.4.1", can also be a tuple)
        :param server_type: The type of server (redis, dragonfly, valkey, kividb)
        :param config: A dictionary of configuration options.

        Configuration options:
        - `requirepass`: The password required to authenticate to the server.
        - `aclfile`: The path to the ACL file.
        """
        self.lock = threading.Lock()
        self.dbs: dict[int, Database] = defaultdict(lambda: Database(self.lock))
        # Maps channel/pattern to a weak set of sockets
        self.script_cache: dict[bytes, bytes] = {}  # Maps SHA1 to the script source
        self.subscribers: dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.psubscribers: dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.ssubscribers: dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.lastsave: int = int(time.time())
        # Reported by INFO SERVER: when the server started (for uptime_in_seconds) and the id of this run.
        self.started_at: float = time.time()
        self.run_id: str = secrets.token_hex(20)
        self.connected = True
        # List of weakrefs to sockets that are being closed lazily
        self.sockets: list[Any] = []
        self.closed_sockets: list[Any] = []
        self.version: VersionType = _create_version(version)
        if server_type not in ("redis", "dragonfly", "valkey", "kividb"):
            raise ValueError(f"Unsupported server type: {server_type}")
        self.server_type: ServerType = server_type
        self.config: dict[bytes, bytes] = config or {}
        self.acl: AccessControlList = AccessControlList()
        self.clients: dict[str, dict[str, Any]] = {}
        self._next_client_id = 1
        # CLIENT PAUSE state. Recorded so CLIENT PAUSE/UNPAUSE validate and round-trip, but command processing is never
        # actually suspended (see CLIENT PAUSE docs).
        self.pause_until: float = 0.0
        self.pause_mode: bytes = b"all"
        # Where each recent SCAN-family cursor resumes: (the iteration's sorted snapshot, the position in it), keyed by
        # (scan state, cursor). See `_scan`.
        self.scan_cursors: OrderedDict[tuple[Any, int], tuple[list[Any], int]] = OrderedDict()

    SCAN_CURSORS_LIMIT: ClassVar[int] = 1024

    @property
    def details(self) -> ServerDetails:
        return ServerDetails.create(self.server_type, self.version)

    def remember_scan_cursor(self, cursor_key: tuple[Any, int], resume_at: tuple[list[Any], int]) -> None:
        """Record where a SCAN-family cursor resumes, forgetting the oldest cursor once too many are held."""
        self.scan_cursors[cursor_key] = resume_at
        self.scan_cursors.move_to_end(cursor_key)
        while len(self.scan_cursors) > self.SCAN_CURSORS_LIMIT:
            self.scan_cursors.popitem(last=False)

    def forget_scan_snapshot(self, snapshot: list[Any]) -> None:
        """Drop the cursors of an iteration that has finished, so its snapshot does not outlive it."""
        finished = [cursor_key for cursor_key, (held, _) in self.scan_cursors.items() if held is snapshot]
        for cursor_key in finished:
            del self.scan_cursors[cursor_key]

    def get_next_client_id(self) -> int:
        with self.lock:
            client_id = self._next_client_id
            self._next_client_id += 1
        return client_id

    @staticmethod
    def get_server(key: str, version: VersionType, server_type: ServerType) -> FakeServer:
        if key not in FakeServer._servers_map:
            FakeServer._servers_map[key] = FakeServer(version=version, server_type=server_type)
        return FakeServer._servers_map[key]
