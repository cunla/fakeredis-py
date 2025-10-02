import logging
from dataclasses import dataclass
from io import BufferedIOBase
from itertools import count
from socketserver import ThreadingTCPServer, StreamRequestHandler
from typing import Dict, Tuple, Any, Union

from redis.lock import Lock

from fakeredis import FakeRedis
from fakeredis import FakeServer
from fakeredis._typing import VersionType, ServerType

LOGGER = logging.getLogger("fakeredis")
LOGGER.setLevel(logging.DEBUG)

# logging.basicConfig(level=logging.DEBUG)


try:
    import lupa  # noqa: F401

    lua_scripts_supported = True
except ImportError:
    lua_scripts_supported = False


def to_bytes(value: Any) -> bytes:
    if isinstance(value, bytes):
        return value
    return str(value).encode()


@dataclass
class Client:
    connection: FakeRedis
    client_address: int


@dataclass
class Reader:
    reader: BufferedIOBase

    def load(self) -> Any:
        line = self.reader.readline().strip()
        prefix, rest = line[0:1], line[1:]
        if prefix == b"*":
            length = int(rest)
            array = [None] * length
            for i in range(length):
                array[i] = self.load()
            return array
        if prefix == b"$":
            bulk_string = self.reader.read(int(rest) + 2).strip()
            if len(bulk_string) != int(rest):
                raise ValueError()
            return bulk_string
        if prefix == b":":
            return int(rest)
        if prefix == b"+":
            return rest
        if prefix == b"-":
            return Exception(rest)
        return None


@dataclass
class Writer:
    writer: BufferedIOBase

    def dump(self, value: Any, dump_bulk: bool = False) -> None:
        if isinstance(value, int):
            self.writer.write(f":{value}\r\n".encode())
        elif isinstance(value, (str, bytes)):
            value = to_bytes(value)
            if dump_bulk or b"\r" in value or b"\n" in value:
                self.writer.write(b"$" + str(len(value)).encode() + b"\r\n" + value + b"\r\n")
            else:
                self.writer.write(b"+" + value + b"\r\n")
        elif isinstance(value, (list, set)):
            self.writer.write(f"*{len(value)}\r\n".encode())
            for item in value:
                self.dump(item, dump_bulk=True)
        elif value is None:
            self.writer.write("$-1\r\n".encode())
        elif isinstance(value, Exception):
            self.writer.write(f"-{value.args[0]}\r\n".encode())


class TCPFakeRequestHandler(StreamRequestHandler):
    server: "TcpFakeServer"  # type: ignore

    def setup(self) -> None:
        super().setup()
        if self.client_address in self.server.clients:
            self.current_client = self.server.clients[self.client_address]
        else:
            self.current_client = Client(
                connection=FakeRedis(server=self.server.fake_server),
                client_address=self.client_address,
            )
            if lua_scripts_supported:
                self.current_client.connection.script_load(Lock.LUA_RELEASE_SCRIPT)
                self.current_client.connection.script_load(Lock.LUA_EXTEND_SCRIPT)
                self.current_client.connection.script_load(Lock.LUA_REACQUIRE_SCRIPT)
            self.reader = Reader(self.rfile)
            self.writer = Writer(self.wfile)
            self.server.clients[self.client_address] = self.current_client

    def handle(self) -> None:
        LOGGER.debug(f"+++ {self.client_address[0]} connected")
        while True:
            try:
                self.data = self.reader.load()
                LOGGER.debug(f">>> {self.client_address[0]}: {self.data}")
                if len(self.data) == 1 and self.data[0].upper() == b"SHUTDOWN":
                    LOGGER.debug(f"*** {self.client_address[0]} requested shutdown")
                    break
                res = self.current_client.connection.execute_command(*self.data)
                LOGGER.debug(f"<<< {self.client_address[0]}: {res}")
                self.writer.dump(res)
            except Exception as e:
                LOGGER.debug(f"!!! {self.client_address[0]}: {e}")
                self.writer.dump(e)
                break

    def finish(self) -> None:
        self.server.clients[self.current_client.client_address].connection.close()
        del self.server.clients[self.current_client.client_address]
        super().finish()


class TcpFakeServer(ThreadingTCPServer):
    def __init__(
        self,
        server_address: Tuple[Union[str, bytes, bytearray], int],
        bind_and_activate: bool = True,
        server_type: ServerType = "redis",
        server_version: VersionType = (8, 0),
    ):
        self.daemon_threads = True
        super().__init__(server_address, TCPFakeRequestHandler, bind_and_activate)
        self.daemon_threads = True
        self.allow_reuse_address = True
        self.fake_server = FakeServer(server_type=server_type, version=server_version)
        self.client_ids = count(0)
        self.clients: Dict[int, Client] = dict()


if __name__ == "__main__":
    server = TcpFakeServer(("localhost", 19000))
    server.serve_forever()
    server.server_close()
    server.shutdown()
