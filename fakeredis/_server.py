import logging
import threading
import time
import weakref
from collections import defaultdict
from typing import Dict, Tuple, Any, List, Optional, Union

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal


from fakeredis._helpers import Database, FakeSelector

LOGGER = logging.getLogger("fakeredis")

VersionType = Union[Tuple[int, ...], int, str]

ServerType = Literal["redis", "dragonfly", "valkey"]


def _create_version(v: VersionType) -> Tuple[int, ...]:
    if isinstance(v, tuple):
        return v
    if isinstance(v, int):
        return (v,)
    if isinstance(v, str):
        v_split = v.split(".")
        return tuple(int(x) for x in v_split)
    return v


class FakeServer:
    _servers_map: Dict[str, "FakeServer"] = dict()

    def __init__(self, version: VersionType = (7,), server_type: ServerType = "redis") -> None:
        self.lock = threading.Lock()
        self.dbs: Dict[int, Database] = defaultdict(lambda: Database(self.lock))
        # Maps channel/pattern to a weak set of sockets
        self.subscribers: Dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.psubscribers: Dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.ssubscribers: Dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.lastsave: int = int(time.time())
        self.connected = True
        # List of weakrefs to sockets that are being closed lazily
        self.closed_sockets: List[Any] = []
        self.version: Tuple[int, ...] = _create_version(version)
        if server_type not in ("redis", "dragonfly", "valkey"):
            raise ValueError(f"Unsupported server type: {server_type}")
        self.server_type: str = server_type

    @staticmethod
    def get_server(key: str, version: VersionType, server_type: str) -> "FakeServer":
        return FakeServer._servers_map.setdefault(key, FakeServer(version=version, server_type=server_type))


class FakeBaseConnectionMixin(object):
    def __init__(self, *args: Any, version: VersionType = (7, 0), server_type: str = "redis", **kwargs: Any) -> None:
        self.client_name: Optional[str] = None
        self.server_key: str
        self._sock = None
        self._selector: Optional[FakeSelector] = None
        self._server = kwargs.pop("server", None)
        self._lua_modules = kwargs.pop("lua_modules", set())
        path = kwargs.pop("path", None)
        connected = kwargs.pop("connected", True)
        if self._server is None:
            if path:
                self.server_key = path
            else:
                host, port = kwargs.get("host"), kwargs.get("port")
                self.server_key = f"{host}:{port}"
            self.server_key += f":{server_type}:v{version}"
            self._server = FakeServer.get_server(self.server_key, server_type=server_type, version=version)
            self._server.connected = connected
        super().__init__(*args, **kwargs)
