from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import redis

from fakeredis._core import FakeSelector, FakeServer
from fakeredis._core._server import _create_version
from fakeredis._typing import ServerType, VersionType
from fakeredis.model import ClientInfo


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
            self.server_key += f":{server_type}:v{_create_version(version)[0]}"
            self._server = FakeServer.get_server(self.server_key, server_type=server_type, version=version)
            self._server.connected = connected
        client_info_arg = kwargs.pop("client_info", {})
        super().__init__(*args, **kwargs)
        protocol = getattr(self, "protocol", 2)

        # The client id is assigned by the socket, one per (re)connection, as redis does.
        client_info = {
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
