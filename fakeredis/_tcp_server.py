import logging
from dataclasses import dataclass
from itertools import count
from socketserver import ThreadingTCPServer, StreamRequestHandler
from typing import BinaryIO, Dict, Tuple, Any

from redis.exceptions import NoScriptError, AuthenticationError

from fakeredis import FakeRedis
from fakeredis import FakeServer
from fakeredis._typing import VersionType, ServerType

LOGGER = logging.getLogger("fakeredis")
LOGGER.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)


def to_bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    return str(value).encode()


@dataclass
class Client:
    connection: FakeRedis
    client_address: int


@dataclass
class Reader:
    reader: BinaryIO

    def load(self) -> Any:
        line = self.reader.readline().strip()
        match line[0:1], line[1:]:
            case b"*", length:
                length = int(length)
                array = [None] * length
                for i in range(length):
                    array[i] = self.load()
                return array
            case b"$", length:
                bulk_string = self.reader.read(int(length) + 2).strip()
                if len(bulk_string) != int(length):
                    raise ValueError()
                return bulk_string
            case b":", value:
                return int(value)
            case b"+", value:
                return value
            case b"-", value:
                return Exception(value)
            case _:
                return None


@dataclass
class Writer:
    writer: BinaryIO
    EXCEPTION_MAP = {
        NoScriptError: "NOSCRIPT",
        AuthenticationError: "WRONGPASS",
    }

    def dump(self, value: Any, dump_bulk=False) -> None:
        if isinstance(value, int):
            self.writer.write(f":{value}\r\n".encode())
        elif isinstance(value, (str, bytes)):
            value = to_bytes(value)
            if value.startswith(b"-"):
                self.writer.write(value + b"\r\n")
            elif dump_bulk or b"\r" in value or b"\n" in value:
                self.writer.write(b"$" + str(len(value)).encode() + b"\r\n" + value + b"\r\n")
            else:
                self.writer.write(b"+" + value + b"\r\n")
        elif isinstance(value, (list, set)):
            self.writer.write(f"*{len(value)}\r\n".encode())
            for item in value:
                self.dump(item, dump_bulk=True)
        elif value is None:
            self.writer.write("$-1\r\n".encode())
        else:
            raise TypeError(value)


class TCPFakeRequestHandler(StreamRequestHandler):
    def setup(self) -> None:
        super().setup()
        if self.client_address in self.server.clients:
            self.current_client = self.server.clients[self.client_address]
        else:
            self.current_client = Client(
                connection=FakeRedis(server=self.server.fake_server),
                client_address=self.client_address,
            )
            self.reader = Reader(self.rfile)
            self.writer = Writer(self.wfile)
            self.server.clients[self.client_address] = self.current_client

    def handle(self):
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
                break

    def finish(self) -> None:
        del self.server.clients[self.current_client.client_address]
        super().finish()


class TcpFakeServer(ThreadingTCPServer):
    def __init__(
        self,
        server_address: Tuple[str | bytes | bytearray, int],
        bind_and_activate: bool = True,
        server_type: ServerType = "redis",
        server_version: VersionType = (8, 0),
    ):
        super().__init__(server_address, TCPFakeRequestHandler, bind_and_activate)
        self.allow_reuse_address = True
        self.fake_server = FakeServer(server_type=server_type, version=server_version, is_tcp_server=True)
        self.client_ids = count(0)
        self.clients: Dict[int, FakeRedis] = dict()


if __name__ == "__main__":
    server = TcpFakeServer(("localhost", 19000))
    server.serve_forever()
    server.server_close()
    server.shutdown()
