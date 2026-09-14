from __future__ import annotations

from fakeredis._commands import Float
from fakeredis._helpers import SimpleError

try:
    import fcntl

    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
import logging
import os
import select
import threading
from dataclasses import dataclass
from io import BufferedIOBase
from itertools import count
from socketserver import StreamRequestHandler, ThreadingTCPServer
from typing import Any

import redis
from redis.connection import DefaultParser

from fakeredis import FakeRedisConnection, FakeServer
from fakeredis._typing import ServerType, VersionType

LOGGER = logging.getLogger("fakeredis")
# LOGGER.setLevel(logging.DEBUG)

# logging.basicConfig(level=logging.DEBUG)

try:
    import lupa  # noqa: F401

    lua_scripts_supported = True
except ImportError:
    lua_scripts_supported = False


# The handler loop interleaves two event sources: inbound data on the TCP socket and replies the server pushes without a
# client request (pub/sub messages, blocking-command wakeups). This is the socket poll timeout, so it also bounds how
# long a pushed reply waits before being written out.
_POLL_INTERVAL = 0.01

# The connection behind each TCP client must start in RESP2, as a fresh connection to a real server does, and switch only
# when the TCP client sends HELLO itself. redis-py 5+ would otherwise negotiate its own default (RESP3 since redis-py 8)
# before the client says anything. redis-py 4 has no `protocol` argument and never negotiates.
_INTERNAL_CONNECTION_KWARGS: dict[str, Any] = {"protocol": 2} if int(redis.__version__.split(".")[0]) >= 5 else {}


def to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    return str(value).encode()


_EXCEPTION_PREFIX_MAP: dict[type[Exception], str] = {
    v: k for k, v in DefaultParser.EXCEPTION_CLASSES.items() if isinstance(v, type) and issubclass(v, Exception)
}


def _get_exception_prefix(e: Exception) -> str:
    for k, v in _EXCEPTION_PREFIX_MAP.items():
        if isinstance(e, k):
            return v
    return "ERR"


def _bulk(data: bytes) -> bytes:
    return b"$%d\r\n%s\r\n" % (len(data), data)


def encode_reply(value: Any, protocol: int, nested: bool = False) -> bytes:
    """Serialize one reply as RESP2 (`protocol=2`) or RESP3 (`protocol=3`).

    `value` is what the fake socket produced for a client speaking `protocol`, so its shape is already right (a RESP2
    client gets a map flattened to a list, for instance). What differs is how the types RESP2 has no encoding for are
    written: null, double, boolean, big number, map and set. SimpleString has been unwrapped by then, so a top-level
    string goes out as a simple string whenever it can be one.
    """
    if value is None:
        return b"_\r\n" if protocol == 3 else b"$-1\r\n"
    if isinstance(value, Exception):
        if isinstance(value, SimpleError):
            message = value.args[0]
        else:
            message = f"{_get_exception_prefix(value)} {value.args[0]}"
        return f"-{message}\r\n".encode()
    if isinstance(value, bool):  # before int, which bool subclasses
        if protocol == 3:
            return b"#t\r\n" if value else b"#f\r\n"
        return b":1\r\n" if value else b":0\r\n"
    if isinstance(value, int):
        if -(2**63) <= value <= 2**63 - 1:
            return b":%d\r\n" % value
        return b"(%d\r\n" % value if protocol == 3 else _bulk(b"%d" % value)
    if isinstance(value, float):
        if protocol == 3:
            return f",{value:.17g}\r\n".encode()
        return _bulk(Float.encode(value, humanfriendly=False))
    if isinstance(value, (bytes, str)):
        data = to_bytes(value)
        if nested or b"\r" in data or b"\n" in data:
            return _bulk(data)
        return b"+" + data + b"\r\n"
    if isinstance(value, dict):
        items = [item for pair in value.items() for item in pair]
        header = b"%%%d\r\n" % len(value) if protocol == 3 else b"*%d\r\n" % len(items)
        return header + b"".join(encode_reply(item, protocol, nested=True) for item in items)
    if isinstance(value, (set, frozenset)):
        header = b"~%d\r\n" if protocol == 3 else b"*%d\r\n"
        return header % len(value) + b"".join(encode_reply(item, protocol, nested=True) for item in value)
    if isinstance(value, (list, tuple)):
        return b"*%d\r\n" % len(value) + b"".join(encode_reply(item, protocol, nested=True) for item in value)
    raise TypeError(f"Cannot encode a reply of type {type(value).__name__}")


@dataclass
class Writer:
    client_address: tuple[str, int]
    writer: BufferedIOBase
    request_handler: TCPFakeRequestHandler

    def write(self, value: bytes) -> None:
        LOGGER.debug(f"<<< {self.client_address}: {value!r}")
        self.writer.write(value)

    def dump(self, value: Any) -> None:
        """Send a reply in the protocol the connection negotiated: RESP2 until a HELLO switches it."""
        self.write(encode_reply(value, self.request_handler.protocol_version))
        self.writer.flush()


class TCPFakeRequestHandler(StreamRequestHandler):
    server: TcpFakeServer

    def setup(self) -> None:
        super().setup()
        fd = self.rfile.fileno()
        if HAS_FCNTL:
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        self.writer = Writer(self.client_address, self.wfile, self)
        if self.client_address in self.server.clients:
            self.current_client = self.server.clients[self.client_address]
        else:
            self.current_client = FakeRedisConnection(
                server=self.server.fake_server,
                writer=self.writer,
                client_info={
                    "laddr": self.connection.getsockname(),
                    "addr": self.connection.getpeername(),
                    "fd": self.connection.fileno(),
                },
                **_INTERNAL_CONNECTION_KWARGS,
            )

            self.server.clients[self.client_address] = self.current_client

    @property
    def protocol_version(self) -> int:
        """The RESP version this connection has negotiated with HELLO."""
        return self.current_client.get_socket()._client_info.protocol_version

    def handle(self) -> None:
        LOGGER.debug(f"+++ {self.client_address[0]} connected")
        while not self.server._shutdown_event.is_set():
            try:
                if self.current_client.can_read():
                    response = self.current_client.read_response()
                    self.writer.dump(response)
                    continue

                data = self.rfile.readline()
                if data == b"":
                    # The socket is non-blocking, so an empty read means either "nothing available yet" or "the peer
                    # closed". readline() only touches the socket once its buffer is drained, so select() on the raw
                    # socket is authoritative at this point: readable yet yielding no bytes is EOF. For the same reason
                    # readline() must not be gated behind select(): an earlier read can leave whole commands sitting in
                    # the buffer while the socket itself has nothing further to report.
                    readable, _, _ = select.select([self.connection], [], [], _POLL_INTERVAL)
                    if not readable:
                        continue
                    # Data may have arrived between the empty read and select(): either this read produces it, or it
                    # confirms the peer is gone.
                    data = self.rfile.readline()
                    if data == b"":
                        break
                self.current_client.get_socket().sendall(data)

            except ConnectionError as e:
                # The peer reset the connection; there is no socket left to report to.
                LOGGER.debug(f"!!! {self.client_address[0]} reset: {e}")
                break
            except Exception as e:
                LOGGER.debug(f"!!! {self.client_address[0]}: {e}")
                self.writer.dump(e)
                break

    def finish(self) -> None:
        self.current_client.disconnect()  # type: ignore[no-untyped-call]
        LOGGER.debug(f"--- {self.client_address[0]} disconnected")
        self.rfile.close()
        self.wfile.close()
        del self.server.clients[self.client_address]
        super().finish()


class TcpFakeServer(ThreadingTCPServer):
    def __init__(
        self,
        server_address: tuple[str | bytes | bytearray, int],
        bind_and_activate: bool = True,
        server_type: ServerType = "redis",
        server_version: VersionType = (8, 0),
    ):
        self.allow_reuse_address = True
        self.daemon_threads = False
        self._shutdown_event = threading.Event()
        super().__init__(server_address, TCPFakeRequestHandler, bind_and_activate)
        self.fake_server = FakeServer(server_type=server_type, version=server_version)
        self.client_ids = count(0)
        self.clients: dict[int, FakeRedisConnection] = {}

    def shutdown(self) -> None:
        self._shutdown_event.set()
        super().shutdown()


TCP_SERVER_TEST_PORT = 19000
if __name__ == "__main__":
    server = TcpFakeServer(("localhost", TCP_SERVER_TEST_PORT))
    server.serve_forever()
    server.server_close()
    server.shutdown()
