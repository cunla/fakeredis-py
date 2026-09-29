from __future__ import annotations

import logging
import threading
import time
import weakref
from collections import defaultdict
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
