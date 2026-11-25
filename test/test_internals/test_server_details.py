import pytest

from fakeredis import FakeServer
from fakeredis._core import ServerDetails
from fakeredis._core._server import DbDetails, InfoServer


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


def _info_server(server_type, version) -> InfoServer:
    return InfoServer(
        details=ServerDetails.create(server_type, version),
        os="Linux",
        arch_bits=64,
        process_id=1,
        run_id="0" * 40,
        server_time_usec=1,
        uptime_in_seconds=90_000,
    )


@pytest.mark.parametrize(
    "server_type,version,identity",
    [
        ("redis", (8, 10), {"redis_version": "8.10.0", "redis_mode": "standalone"}),
        (
            "valkey",
            (9, 1),
            {"redis_version": "7.2.4", "server_name": "valkey", "valkey_version": "9.1.0", "server_mode": "standalone"},
        ),
        (
            "valkey",
            (7, 2),
            {"redis_version": "7.2.4", "server_name": "valkey", "valkey_version": "7.2.0", "redis_mode": "standalone"},
        ),
        ("dragonfly", (7, 4), {"redis_version": "7.4.0", "dragonfly_version": "df-v0.0.0", "redis_mode": "standalone"}),
        ("kividb", (8, 10), {"redis_version": "8.10.0", "kividb_version": "0.0.0", "redis_mode": "standalone"}),
    ],
)
def test_info_server_to_dict(server_type, version, identity):
    fields = _info_server(server_type, version).to_dict()
    assert {key: fields[key] for key in identity} == identity
    assert ("run_id" in fields) == (server_type != "dragonfly")
    assert ("server_time_usec" in fields) == (server_type in ("redis", "valkey"))
    assert fields["uptime_in_days"] == 1


@pytest.mark.parametrize(
    "server_type,version,expected",
    [
        ("redis", (7, 4), {"keys": 3, "expires": 2, "avg_ttl": 500, "subexpiry": 1}),
        ("redis", (7, 2), {"keys": 3, "expires": 2, "avg_ttl": 500}),
        ("valkey", (9, 1), {"keys": 3, "expires": 2, "avg_ttl": 500, "keys_with_volatile_items": 1}),
        ("valkey", (8, 1), {"keys": 3, "expires": 2, "avg_ttl": 500}),
        ("dragonfly", (7, 4), {"keys": 3, "expires": 2, "avg_ttl": -1}),
        ("kividb", (8, 10), {"keys": 3, "expires": 2, "avg_ttl": 500}),
    ],
)
def test_db_details_to_dict(server_type, version, expected):
    details = DbDetails(server_type, version, db_num=0, keys=3, expires=2, avg_ttl=500, subexpiry=1)
    assert details.to_dict() == expected  # db_num names the line (db0:...), it is not one of its fields
