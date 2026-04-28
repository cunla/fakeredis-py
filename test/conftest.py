import time
from dataclasses import dataclass
from threading import Thread
from typing import Callable, Tuple, Optional, Any, Generator, Dict, Type, Union

import pytest
import pytest_asyncio
import redis
import valkey

import fakeredis
from fakeredis._server import _create_version
from fakeredis._tcp_server import TCP_SERVER_TEST_PORT, TcpFakeServer
from fakeredis._typing import ServerType, VersionType, ClientType, AsyncClientType
from test.testtools import REDIS_PY_VERSION


@dataclass
class ServerDetails:
    server_type: ServerType
    redis_version: VersionType
    valkey_version: Optional[VersionType]
    dragonfly_version: Optional[VersionType]

    @property
    def server_version(self) -> VersionType:
        if self.server_type == "dragonfly":
            return self.dragonfly_version or self.redis_version
        elif self.server_type == "valkey":
            return self.valkey_version or self.redis_version
        return self.redis_version


def _check_lua_module_supported() -> bool:
    redis = fakeredis.FakeRedis(lua_modules={"cjson"})
    try:
        redis.eval("return cjson.encode({})", 0)
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def real_server_address() -> Tuple[str, int]:
    """Returns real server address"""
    return "localhost", 6390


@pytest.fixture(scope="session")
def real_server_details(real_server_address: Tuple[str, int]) -> ServerDetails:
    """Returns server's version or exit if server is not running"""
    client = None
    try:
        client = redis.Redis(real_server_address[0], port=real_server_address[1], db=2)
        client_info = client.info()
        server_type: ServerType = "dragonfly" if "dragonfly_version" in client_info else "redis"
        if "server_name" in client_info:
            server_type = client_info["server_name"]
        redis_version = _create_version(client_info["redis_version"]) or (7,)
        valkey_version = _create_version(client_info["valkey_version"]) if "valkey_version" in client_info else None
        dragonfly_version = (
            _create_version(client_info["dragonfly_version"][4:]) if "dragonfly_version" in client_info else None
        )
        return ServerDetails(server_type, redis_version, valkey_version, dragonfly_version)
    except redis.ConnectionError as e:
        pytest.exit(f"Real server is not running {e}")
        return "redis", (6,)
    finally:
        if hasattr(client, "close"):
            client.close()  # Absent in older versions of redis-py


@pytest_asyncio.fixture(name="fake_server")
def _fake_server(request, real_server_details: ServerDetails) -> fakeredis.FakeServer:
    server = fakeredis.FakeServer(
        server_type=real_server_details.server_type, version=real_server_details.server_version
    )
    server.connected = request.node.get_closest_marker("disconnected") is None
    return server


@pytest_asyncio.fixture(name="tcp_server_address")
def _tcp_fake_server() -> Generator[tuple[str, int], Any, None]:
    server_address = ("127.0.0.1", TCP_SERVER_TEST_PORT)
    server = TcpFakeServer(server_address)
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    yield server_address
    server.server_close()
    server.shutdown()
    t.join()


@pytest_asyncio.fixture
def r(request, create_connection: Callable[[..., Any], redis.Redis]) -> Generator[redis.Redis, Any, None]:
    rconn = create_connection(db=2)
    connected = request.node.get_closest_marker("disconnected") is None
    if connected:
        rconn.flushall()
    yield rconn
    if connected:
        rconn.flushall()
    if hasattr(r, "close"):
        rconn.close()  # Older versions of redis-py don't have this method


def _validate_server_versions(request, real_server_details: ServerDetails) -> None:
    server_type, redis_version = real_server_details.server_type, real_server_details.redis_version
    unsupported_server_types = request.node.get_closest_marker("unsupported_server_types")
    if unsupported_server_types and server_type in unsupported_server_types.args:
        pytest.skip(f"Server type {server_type} is not supported")
    marker = request.node.get_closest_marker("supported_redis_versions")
    min_redis_ver = _create_version(marker.kwargs["min_ver"]) if marker and "min_ver" in marker.kwargs else (0,)
    max_redis_ver = _create_version(marker.kwargs["max_ver"]) if marker and "max_ver" in marker.kwargs else (100,)

    if redis_version < min_redis_ver:
        pytest.skip(f"Redis server {min_redis_ver} or more required but {redis_version} found")
    if redis_version > max_redis_ver:
        pytest.skip(f"Redis server {max_redis_ver} or less required but {redis_version} found")


# Map from (server_type is valkey, fake flag, async flag) -> client class

CLIENT_CLASS_MAP: Dict[Tuple[bool, bool, bool], Union[Type[ClientType], Type[AsyncClientType]]] = {
    (True, True, False): fakeredis.FakeValkey,
    (True, False, False): valkey.StrictValkey,
    (False, True, False): fakeredis.FakeStrictRedis,
    (False, False, False): redis.StrictRedis,
    (True, True, True): fakeredis.FakeAsyncValkey,
    (True, False, True): valkey.asyncio.StrictValkey,
    (False, True, True): fakeredis.FakeAsyncRedis,
    (False, False, True): redis.asyncio.StrictRedis,
}


def _get_class(
    cls_type: str, real_server_details: ServerDetails, async_client: bool
) -> Union[Type[ClientType], Type[AsyncClientType]]:
    is_valkey = real_server_details.server_type == "valkey"
    is_fake = cls_type.lower().startswith("fake")
    res = CLIENT_CLASS_MAP[is_valkey, is_fake, async_client]
    return res


@pytest_asyncio.fixture(
    name="create_connection",
    params=[
        pytest.param("Strict2", marks=pytest.mark.real),
        pytest.param("FakeStrict2", marks=pytest.mark.fake),
        pytest.param("Strict3", marks=pytest.mark.real),
        pytest.param("FakeStrict3", marks=pytest.mark.fake),
    ],
)
def _create_connection(request, real_server_details: ServerDetails) -> Callable[[Dict[str, Any]], ClientType]:
    cls_type, protocol = request.param[:-1], int(request.param[-1])
    if REDIS_PY_VERSION.major < 5 and protocol == 3:
        pytest.skip("redis-py 4.x does not support RESP3")

    if not cls_type.startswith("Fake") and not real_server_details.redis_version:
        pytest.skip("Real server is not running")
    resp2only = request.node.get_closest_marker("resp2_only")
    if resp2only and protocol == 3:
        pytest.skip("Test is for RESP2 only")
    resp3only = request.node.get_closest_marker("resp3_only")
    if resp3only and protocol == 2:
        pytest.skip("Test is for RESP3 only")

    _validate_server_versions(request, real_server_details)
    decode_responses = request.node.get_closest_marker("decode_responses") is not None
    lua_modules_marker = request.node.get_closest_marker("load_lua_modules")
    lua_modules = set(lua_modules_marker.args) if lua_modules_marker else None
    if lua_modules and not _check_lua_module_supported():
        pytest.skip("LUA modules not supported by fakeredis")

    def factory(**kwargs: Any) -> redis.Redis:
        if REDIS_PY_VERSION.major >= 5:
            kwargs["protocol"] = protocol
        cls = _get_class(cls_type, real_server_details, False)
        if cls_type.startswith("Fake"):
            fake_server = request.getfixturevalue("fake_server")
            return cls(decode_responses=decode_responses, server=fake_server, lua_modules=lua_modules, **kwargs)
        else:
            return cls("localhost", port=6390, decode_responses=decode_responses, **kwargs)

    return factory


@pytest_asyncio.fixture(
    name="async_redis",
    params=[
        pytest.param(("fake", 2), marks=pytest.mark.fake),
        pytest.param(("fake", 3), marks=pytest.mark.fake),
        pytest.param(("real", 2), marks=pytest.mark.real),
        pytest.param(("real", 3), marks=pytest.mark.real),
    ],
    ids=lambda x: f"{x[0]}_resp{x[1]}",
)
async def _req_aioredis2(request, real_server_details: ServerDetails) -> AsyncClientType:
    param_type, protocol = request.param[0], int(request.param[1])
    if param_type != "fake" and not real_server_details.server_version:
        pytest.skip("Real server is not running")
    if REDIS_PY_VERSION.major < 5 and protocol == 3:
        pytest.skip("redis-py 4.x does not support RESP3")
    decode_responses = bool(request.node.get_closest_marker("decode_responses"))
    _validate_server_versions(request, real_server_details)
    lua_modules_marker = request.node.get_closest_marker("load_lua_modules")
    lua_modules = set(lua_modules_marker.args) if lua_modules_marker else None
    if lua_modules and not _check_lua_module_supported():
        pytest.skip("LUA modules not supported by fakeredis")
    fake_server: Optional[fakeredis.FakeServer]
    cls = _get_class(param_type, real_server_details, True)
    if param_type == "fake":
        fake_server = request.getfixturevalue("fake_server")
        ret = cls(server=fake_server, lua_modules=lua_modules, decode_responses=decode_responses, protocol=protocol)
    else:
        ret = cls(host="localhost", port=6390, db=2, decode_responses=decode_responses, protocol=protocol)
        fake_server = None
    if not fake_server or fake_server.connected:
        await ret.flushall()

    yield ret

    if not fake_server or fake_server.connected:
        await ret.flushall()
    await ret.connection_pool.disconnect()
