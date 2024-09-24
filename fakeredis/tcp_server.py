from dataclasses import dataclass
from itertools import count
from socket import socket
from socketserver import ThreadingTCPServer, StreamRequestHandler
from typing import BinaryIO, AnyStr, Dict, Tuple

from redis import ResponseError

from fakeredis import FakeRedis
from fakeredis import FakeServer


def to_bytes(value) -> bytes:
    if isinstance(value, bytes):
        return value
    return str(value).encode()


@dataclass
class Client:
    connection: FakeRedis
    client_id: int


@dataclass
class RespLoader:
    reader: BinaryIO

    def load_array(self, length: int):
        array = [None] * length
        for i in range(length):
            array[i] = self.load()
        return array

    def load(self):
        line = self.reader.readline().strip()
        match line[0:1], line[1:]:
            case b"*", length:
                return self.load_array(int(length))
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
class RespDumper:
    writer: BinaryIO

    def dump_bulk_string(self, value: AnyStr):
        if isinstance(value, str):
            value = value.encode()
        self.writer.write(b"$" + str(len(value)).encode() + b"\r\n" + value + b"\r\n")

    def dump_string(self, value: AnyStr):
        if isinstance(value, str):
            value = value.encode()
        self.writer.write(b"+" + value + b"\r\n")

    def dump_array(self, value: list):
        self.writer.write(f"*{len(value)}\r\n".encode())
        for item in value:
            self.dump(item, dump_bulk=True)

    def dump(self, value, dump_bulk=False):
        if isinstance(value, int):
            self.writer.write(f":{value}\r\n".encode())
        elif isinstance(value, str) or isinstance(value, bytes):
            if isinstance(value, str):
                value = value.encode()
            if dump_bulk or b"\r" in value or b"\n" in value:
                self.dump_bulk_string(value)
            else:
                self.dump_string(value)
        elif isinstance(value, list):
            self.dump_array(value)
        elif isinstance(value, set):
            self.dump_array(list(value))
        elif isinstance(value, dict):
            result = []
            for k, v in value.items():
                result += [k, v]
            self.dump_array(result)
        elif value is None:
            self.writer.write("$-1\r\n".encode())
        elif isinstance(value, Exception):
            self.writer.write(f"-{value.args[0]}\r\n".encode())


class TCPFakeRequestHandler(StreamRequestHandler):
    def __init__(self, request, client_address, server: "TcpFakeServer"):
        super().__init__(request, client_address, server)
        self.current_client = client_address
        self.request: socket

    def setup(self) -> None:
        super().setup()
        current_client_id = next(self.server.client_ids)
        self.current_client = Client(
            connection=FakeRedis(server=self.server.server),
            client_id=current_client_id,
        )
        self.reader = RespLoader(self.rfile)
        self.writer = RespDumper(self.wfile)
        self.server.clients[current_client_id] = self.current_client

    def handle(self):
        # self.rfile is a file-like object created by the handler;
        # we can now use e.g. readline() instead of raw recv() calls
        self.data = self.reader.load()

        print(f">>> {self.client_address[0]}: {self.data}")

        try:
            res = self.current_client.connection.execute_command(*self.data)
        except ResponseError as e:
            res = e

        print(f"<<< {self.client_address[0]}: {res}")
        self.writer.dump(res)

    def finish(self) -> None:
        del self.server.clients[self.current_client.client_id]
        super().finish()


class TcpFakeServer(ThreadingTCPServer):
    def __init__(self, server_address: Tuple[str | bytes | bytearray, int], bind_and_activate: bool = True):
        super().__init__(server_address, TCPFakeRequestHandler, bind_and_activate)
        self.server = FakeServer(version=(7, 4))
        self.client_ids = count(0)
        self.clients: Dict[int, FakeRedis] = dict()


if __name__ == "__main__":
    server = TcpFakeServer(("localhost", 6379))
    server.serve_forever()
