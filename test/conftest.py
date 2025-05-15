from typing import Callable, Tuple, Optional, Type, Any, Generator, Dict

import pytest
import pytest_asyncio
import redis

import fakeredis
from fakeredis._server import _create_version
from test.testtools import REDIS_PY_VERSION

ServerDetails = Type[Tuple[str, Tuple[int, ...]]]


def _check_lua_module_supported() -> bool:
    redis = fakeredis.FakeRedis(lua_modules={"cjson"})
    try:
        redis.eval("return cjson.encode({})", 0)
        return True
    except Exception:
        return False


@pytest_asyncio.fixture(scope="session")
def real_server_details() -> ServerDetails:
    """Returns server's version or exit if server is not running"""
    client = None
    try:
        client = redis.Redis("localhost", port=6390, db=2)
        client_info = client.info()
        server_type = "dragonfly" if "dragonfly_version" in client_info else "redis"
        if "server_name" in client_info:
            server_type = client_info["server_name"]
        server_version = client_info["redis_version"] if server_type != "dragonfly" else (7, 0)
        server_version = _create_version(server_version) or (7,)
        return server_type, server_version
    except redis.ConnectionError as e:
        pytest.exit(f"Real server is not running {e}")
        return "redis", (6,)
    finally:
        if hasattr(client, "close"):
            client.close()  # Absent in older versions of redis-py


@pytest_asyncio.fixture(name="fake_server")
def _fake_server(request, real_server_details: Tuple[str, Tuple[int, ...]]) -> fakeredis.FakeServer:
    server_type, server_version = real_server_details
    server = fakeredis.FakeServer(server_type=server_type, version=server_version)
    server.connected = request.node.get_closest_marker("disconnected") is None
    return server


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


def _marker_version_value(request, marker_name: str):
    marker_value = request.node.get_closest_marker(marker_name)
    if marker_value is None:
        return (0,) if marker_name == "min_server" else (100,)
    return _create_version(marker_value.args[0])


@pytest_asyncio.fixture(
    name="create_connection",
    params=[
        pytest.param("StrictRedis2", marks=pytest.mark.real),
        pytest.param("FakeStrictRedis2", marks=pytest.mark.fake),
        pytest.param("StrictRedis3", marks=pytest.mark.real),
        pytest.param("FakeStrictRedis3", marks=pytest.mark.fake),
    ],
)
def _create_connection(request, real_server_details: ServerDetails) -> Callable[[Dict[str, Any]], redis.Redis]:
    cls_name, protocol = request.param[:-1], int(request.param[-1])
    if REDIS_PY_VERSION.major < 5 and protocol == 3:
        pytest.skip("redis-py 4.x does not support RESP3")
    server_type, server_version = real_server_details
    if not cls_name.startswith("Fake") and not server_version:
        pytest.skip("Redis is not running")
    resp2only = request.node.get_closest_marker("resp2_only")
    if resp2only and protocol == 3:
        pytest.skip("Test is for RESP2 only")
    resp3only = request.node.get_closest_marker("resp3_only")
    if resp3only and protocol == 2:
        pytest.skip("Test is for RESP3 only")
    unsupported_server_types = request.node.get_closest_marker("unsupported_server_types")
    if unsupported_server_types and server_type in unsupported_server_types.args:
        pytest.skip(f"Server type {server_type} is not supported")
    min_server = _marker_version_value(request, "min_server")
    max_server = _marker_version_value(request, "max_server")
    if server_version < min_server:
        pytest.skip(f"Redis server {min_server} or more required but {server_version} found")
    if server_version > max_server:
        pytest.skip(f"Redis server {max_server} or less required but {server_version} found")
    decode_responses = request.node.get_closest_marker("decode_responses") is not None
    lua_modules_marker = request.node.get_closest_marker("load_lua_modules")
    lua_modules = set(lua_modules_marker.args) if lua_modules_marker else None
    if lua_modules and not _check_lua_module_supported():
        pytest.skip("LUA modules not supported by fakeredis")

    def factory(**kwargs: Any) -> redis.Redis:
        if REDIS_PY_VERSION.major >= 5:
            kwargs["protocol"] = protocol
        if cls_name.startswith("Fake"):
            fake_server = request.getfixturevalue("fake_server")
            cls = getattr(fakeredis, cls_name)
            return cls(decode_responses=decode_responses, server=fake_server, lua_modules=lua_modules, **kwargs)
        # Real
        cls = getattr(redis, cls_name)
        return cls("localhost", port=6390, decode_responses=decode_responses, **kwargs)

    return factory


@pytest_asyncio.fixture(
    name="async_redis",
    params=[pytest.param("fake", marks=pytest.mark.fake), pytest.param("real", marks=pytest.mark.real)],
)
async def _req_aioredis2(request, real_server_details: ServerDetails) -> redis.asyncio.Redis:
    server_type, server_version = real_server_details
    if request.param != "fake" and not server_version:
        pytest.skip("Redis is not running")

    decode_responses = bool(request.node.get_closest_marker("decode_responses"))
    unsupported_server_types = request.node.get_closest_marker("unsupported_server_types")
    if unsupported_server_types and server_type in unsupported_server_types.args:
        pytest.skip(f"Server type {server_type} is not supported")
    min_server_marker = _marker_version_value(request, "min_server")
    max_server_marker = _marker_version_value(request, "max_server")
    if server_version < min_server_marker:
        pytest.skip(f"Redis server {min_server_marker} or more required but {server_version} found")
    if server_version > max_server_marker:
        pytest.skip(f"Redis server {max_server_marker} or less required but {server_version} found")
    lua_modules_marker = request.node.get_closest_marker("load_lua_modules")
    lua_modules = set(lua_modules_marker.args) if lua_modules_marker else None
    if lua_modules and not _check_lua_module_supported():
        pytest.skip("LUA modules not supported by fakeredis")
    fake_server: Optional[fakeredis.FakeServer]
    if request.param == "fake":
        fake_server = request.getfixturevalue("fake_server")
        ret = fakeredis.FakeAsyncRedis(server=fake_server, lua_modules=lua_modules, decode_responses=decode_responses)
    else:
        ret = redis.asyncio.Redis(host="localhost", port=6390, db=2, decode_responses=decode_responses)
        fake_server = None
    if not fake_server or fake_server.connected:
        await ret.flushall()

    yield ret

    if not fake_server or fake_server.connected:
        await ret.flushall()
    await ret.connection_pool.disconnect()
