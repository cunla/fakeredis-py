import pytest

from fakeredis import FakeServer
from fakeredis._core import ServerDetails


@pytest.mark.parametrize(
    "server_type,version,expected",
    [
        ("redis", (8, 10), ServerDetails("redis", (8, 10))),
        ("valkey", (9, 1), ServerDetails("valkey", (7, 2, 4), valkey_version=(9, 1))),
        ("dragonfly", (7, 4), ServerDetails("dragonfly", (7, 4), dragonfly_version=(0, 0, 0))),
        ("kividb", (8, 10), ServerDetails("kividb", (8, 10), kividb_version=(0, 0, 0))),
    ],
)
def test_server_details(server_type, version, expected):
    server = FakeServer(server_type=server_type, version=version)
    assert server.details == expected
    assert server.details.server_version == version
