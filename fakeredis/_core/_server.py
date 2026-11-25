from __future__ import annotations

import logging
import os
import platform
import secrets
import struct
import threading
import time
import weakref
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from typing import Any, ClassVar

from fakeredis._core._database import Database
from fakeredis._typing import ServerType, VersionType
from fakeredis.model import AccessControlList, Hash

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


def _version_string(version: tuple[int, ...]) -> str:
    """`(7, 4)` -> `"7.4.0"`: servers always report at least major.minor.patch."""
    return ".".join(str(part) for part in (*version, 0, 0, 0)[: max(3, len(version))])


# Valkey keeps reporting the Redis version it forked from, whatever its own version.
_VALKEY_REDIS_VERSION: VersionType = (7, 2, 4)
# A fake Dragonfly or KiviDB server is built with the Redis version it emulates, so fakeredis has no product version to
# report for it. One is still given: clients tell these servers apart by whether it is there.
_UNKNOWN_PRODUCT_VERSION: VersionType = (0, 0, 0)


@dataclass(frozen=True)
class ServerDetails:
    """What a server says about itself in INFO SERVER: its type, the Redis version it reports, its own version, and
    the figures of this run. `to_dict` picks the fields the server type and version report.

    The identity fields mirror `ServerDetails` in `test/conftest.py`, which reads them from a real server.
    `FakeServer.details` builds them.
    """

    server_type: ServerType
    redis_version: VersionType
    valkey_version: VersionType | None = None
    dragonfly_version: VersionType | None = None
    kividb_version: VersionType | None = None
    os: str = ""
    arch_bits: int = 0
    process_id: int = 0
    run_id: str = ""
    server_time_usec: int = 0
    uptime_in_seconds: int = 0

    @property
    def server_version(self) -> VersionType:
        """The version a `FakeServer` is built with: Valkey's own version for Valkey, the Redis version for others."""
        return self.valkey_version if self.valkey_version is not None else self.redis_version

    def to_dict(self) -> dict[str, Any]:
        res: dict[str, Any] = {"redis_version": _version_string(self.redis_version)}
        if self.valkey_version is not None:
            res["server_name"] = "valkey"
            res["valkey_version"] = _version_string(self.valkey_version)
        if self.dragonfly_version is not None:
            res["dragonfly_version"] = f"df-v{_version_string(self.dragonfly_version)}"
        if self.kividb_version is not None:
            res["kividb_version"] = _version_string(self.kividb_version)
        # Valkey 8.0 renamed redis_mode to server_mode.
        valkey_8 = self.valkey_version is not None and self.valkey_version >= (8,)
        res["server_mode" if valkey_8 else "redis_mode"] = "standalone"
        res["os"] = self.os
        res["arch_bits"] = self.arch_bits
        res["process_id"] = self.process_id
        if self.server_type != "dragonfly":
            res["run_id"] = self.run_id
        if self.server_type in ("redis", "valkey"):
            res["server_time_usec"] = self.server_time_usec
        res["uptime_in_seconds"] = self.uptime_in_seconds
        res["uptime_in_days"] = self.uptime_in_seconds // 86400
        return res


@dataclass(frozen=True)
class DbDetails:
    server_type: ServerType
    server_version: VersionType
    db_num: int
    keys: int
    expires: int
    avg_ttl: int
    subexpiry: int

    def to_dict(self) -> dict[str, int]:
        res: dict[str, int] = {
            "keys": self.keys,
            "expires": self.expires,
            "avg_ttl": self.avg_ttl if self.server_type != "dragonfly" else -1,
        }
        if self.server_type == "redis" and self.server_version >= (7, 4):
            res["subexpiry"] = self.subexpiry
        elif self.server_type == "valkey" and self.server_version >= (9,):
            res["keys_with_volatile_items"] = self.subexpiry
        return res


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

    def info_server_fields(self) -> dict[str, Any]:
        """
        `version` is Valkey's own version for Valkey, and the Redis version emulated for every other server type.
        The fields of INFO SERVER, in the order they are printed.
        """
        now = time.time()
        details = ServerDetails(
            server_type=self.server_type,
            redis_version=_VALKEY_REDIS_VERSION if self.server_type == "valkey" else self.version,
            valkey_version=self.version if self.server_type == "valkey" else None,
            dragonfly_version=_UNKNOWN_PRODUCT_VERSION if self.server_type == "dragonfly" else None,
            kividb_version=_UNKNOWN_PRODUCT_VERSION if self.server_type == "kividb" else None,
            os=f"{platform.system()} {platform.release()} {platform.machine()}",
            arch_bits=struct.calcsize("P") * 8,
            process_id=os.getpid(),
            run_id=self.run_id,
            server_time_usec=int(now * 1_000_000),
            uptime_in_seconds=int(now - self.started_at),
        )
        return details.to_dict()

    def info_keyspace_fields(self) -> dict[str, dict[str, int]]:
        """`{"db0": {"keys": 2, "expires": 1, ...}, ...}`, one entry per database listed."""
        fields: dict[str, DbDetails] = {}
        indexes = set(self.dbs)
        if self.server_type == "dragonfly":
            indexes.add(0)  # Dragonfly lists db0 even when it is empty
        for index in sorted(indexes):
            db = self.dbs.get(index)
            items = [] if db is None else list(db.values())  # iterating sweeps out expired keys first
            if not items and not (self.server_type == "dragonfly" and index == 0):
                continue
            now = db.time if db is not None else 0.0
            ttls_ms = [(item.expireat - now) * 1000 for item in items if item.expireat is not None]
            fields[f"db{index}"] = DbDetails(
                db_num=index,
                keys=len(items),
                expires=len(ttls_ms),
                avg_ttl=int(sum(ttls_ms) / len(ttls_ms)) if ttls_ms else 0,
                subexpiry=sum(1 for item in items if isinstance(item.value, Hash) and item.value.has_volatile_fields()),
                server_type=self.server_type,
                server_version=self.version,
            )
        return {k: v.to_dict() for k, v in fields.items()}

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
