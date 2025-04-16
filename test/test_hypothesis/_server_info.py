from typing import Tuple, Union

import pytest
import redis

from fakeredis._server import _create_version


def server_info() -> Tuple[str, Union[None, Tuple[int, ...]]]:
    """Returns server's version or None if server is not running"""
    client = None
    try:
        client = redis.Redis("localhost", port=6390, db=2)
        client_info = client.info()
        server_type = "dragonfly" if "dragonfly_version" in client_info else "redis"
        server_version = client_info["redis_version"] if server_type != "dragonfly" else (7, 0)
        server_version = _create_version(server_version) or (7,)
        return server_type, server_version
    except redis.ConnectionError as e:
        print(e)
        pytest.exit("Redis is not running")
        return "redis", (6,)
    finally:
        if hasattr(client, "close"):
            client.close()  # Absent in older versions of redis-py


server_type, redis_ver = server_info()
floats_kwargs = dict()

if server_type == "dragonfly":
    floats_kwargs = dict(allow_nan=False, allow_subnormal=False, allow_infinity=False)
