from __future__ import annotations

import logging
import threading
import time
import weakref
from collections import defaultdict
from collections.abc import Sequence
from typing import Any, ClassVar

import redis

from fakeredis._helpers import Database, FakeSelector
from fakeredis._typing import ServerType, VersionType
from fakeredis.model import AccessControlList, ClientInfo

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


def _version_to_str(v: VersionType) -> str:
    if isinstance(v, tuple):
        return ".".join(str(x) for x in v)
    return str(v)


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
        :param server_type: The type of server (redis, dragonfly, valkey)
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
        if server_type not in ("redis", "dragonfly", "valkey"):
            raise ValueError(f"Unsupported server type: {server_type}")
        self.server_type: ServerType = server_type
        self.config: dict[bytes, bytes] = config or {}
        self.acl: AccessControlList = AccessControlList()
        self.clients: dict[str, dict[str, Any]] = {}
        self._next_client_id = 1
        # CLIENT PAUSE state. Recorded so CLIENT PAUSE/UNPAUSE validate and round-trip,
        # but command processing is never actually suspended (see CLIENT PAUSE docs).
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


class FakeBaseConnectionMixin:
    def __init__(
        self,
        *args: Any,
        version: VersionType = (7, 0),
        server_type: ServerType = "redis",
        server: FakeServer | None = None,
        client_class: type[redis.Redis] = redis.Redis,
        lua_modules: set[str] | None = None,
        writer: Any = None,
        connected: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Initializes the class and sets up the required attributes and configurations for the server and client interaction.

        """
        self.client_name: str | None = None
        self.server_key: str
        self._sock = None
        self._selector: FakeSelector | None = None
        self._server = server
        self._client_class = client_class
        self._lua_modules = lua_modules
        self._writer = writer
        if self._server is None:
            if "path" in kwargs:
                self.server_key = kwargs.pop("path")
            else:
                host, port = kwargs.get("host"), kwargs.get("port")
                self.server_key = f"{host}:{port}"
            self.server_key += f":{server_type}:v{_version_to_str(version)[0]}"
            self._server = FakeServer.get_server(self.server_key, server_type=server_type, version=version)
            self._server.connected = connected
        client_info_arg = kwargs.pop("client_info", {})
        super().__init__(*args, **kwargs)
        protocol = getattr(self, "protocol", 2)

        client_info = {
            "id": self._server.get_next_client_id(),
            "addr": "127.0.0.1:0",
            "laddr": "127.0.0.1:6379",
            "fd": 8,
            "name": "",
            "idle": 0,
            "flags": "N",
            "db": 0,
            "sub": 0,
            "psub": 0,
            "ssub": 0,
            "multi": -1,
            "qbuf": 48,
            "qbuf_free": 16842,
            "argv_mem": 25,
            "multi_mem": 0,
            "rbs": 1024,
            "rbp": 0,
            "obl": 0,
            "oll": 0,
            "omem": 0,
            "tot_mem": 18737,
            "events": "r",
            "cmd": "auth",
            "redir": -1,
            "resp": protocol,
        }
        client_info.update(client_info_arg)
        self._client_info = ClientInfo(**client_info)

    def _decode(self, response: Any) -> Any:
        if isinstance(response, list):
            return [self._decode(item) for item in response]
        elif isinstance(response, dict):
            return {self._decode(k): self._decode(v) for k, v in response.items()}
        elif isinstance(response, bytes):
            return self.encoder.decode(response)  # type: ignore[attr-defined]
        else:
            return response

    def _add_to_local_cache(self, command: Sequence[str], response: Any, keys: list[Any]) -> None:
        return None

    def repr_pieces(self) -> list[tuple[str, Any]]:
        pieces = [("server", self._server), ("db", self.db)]  # type: ignore[attr-defined]
        if self.client_name:
            pieces.append(("client_name", self.client_name))
        return pieces

    def __str__(self) -> str:
        return self.server_key
