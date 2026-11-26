import os
from time import sleep

import pytest

from fakeredis import FakeRedis, FakeServer
from fakeredis._core._server import DbDetails, ServerDetails

# The INFO SERVER fields that say which server this is. Each server type and version reports some of them.
_IDENTITY_FIELDS = {"redis_version", "server_name", "valkey_version", "dragonfly_version", "kividb_version"}
_MODE_FIELDS = {"redis_mode", "server_mode"}


@pytest.mark.parametrize(
    "server_type,version,identity",
    [
        ("redis", (8, 10), {"redis_version": "8.10.0", "redis_mode": "standalone"}),
        ("redis", (6, 2, 17), {"redis_version": "6.2.17", "redis_mode": "standalone"}),
        (
            "valkey",
            (9, 1),
            {"redis_version": "7.2.4", "server_name": "valkey", "valkey_version": "9.1.0", "server_mode": "standalone"},
        ),
        (
            # Valkey 8.0 renamed redis_mode to server_mode.
            "valkey",
            (7, 2),
            {"redis_version": "7.2.4", "server_name": "valkey", "valkey_version": "7.2.0", "redis_mode": "standalone"},
        ),
        ("dragonfly", (7, 4), {"redis_version": "7.4.0", "dragonfly_version": "df-v0.0.0", "redis_mode": "standalone"}),
        ("kividb", (8, 10), {"redis_version": "8.10.0", "kividb_version": "0.0.0", "redis_mode": "standalone"}),
    ],
)
def test_info_server_fields_identity(server_type, version, identity):
    fields = FakeServer(server_type=server_type, version=version).info_server_fields()
    assert {key: fields[key] for key in identity} == identity
    assert (_IDENTITY_FIELDS | _MODE_FIELDS).isdisjoint(fields.keys() - identity.keys())


@pytest.mark.parametrize("server_type", ["redis", "valkey", "dragonfly", "kividb"])
def test_info_server_fields_of_the_run(server_type):
    server = FakeServer(server_type=server_type, version=(9,) if server_type == "valkey" else (7, 4))
    fields = server.info_server_fields()
    assert fields["process_id"] == os.getpid()
    assert fields["arch_bits"] in (32, 64)
    assert fields["os"]
    assert 0 <= fields["uptime_in_seconds"] <= 5
    assert fields["uptime_in_days"] == 0
    # Dragonfly sends no run_id, and only Redis and Valkey send server_time_usec.
    assert fields.get("run_id") == (None if server_type == "dragonfly" else server.run_id)
    assert ("server_time_usec" in fields) == (server_type in ("redis", "valkey"))
    assert server.info_server_fields().get("run_id") == fields.get("run_id")  # one id for the life of the server


def test_server_details_uptime_in_days():
    fields = ServerDetails("redis", (8,), uptime_in_seconds=2 * 86_400 + 5).to_dict()
    assert (fields["uptime_in_seconds"], fields["uptime_in_days"]) == (2 * 86_400 + 5, 2)


@pytest.mark.parametrize(
    "details,server_version",
    [
        (ServerDetails("redis", (8, 10)), (8, 10)),
        (ServerDetails("valkey", (7, 2, 4), valkey_version=(9, 1)), (9, 1)),
        (ServerDetails("dragonfly", (7, 4), dragonfly_version=(0, 0, 0)), (7, 4)),
    ],
)
def test_server_details_server_version(details, server_version):
    assert details.server_version == server_version


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


def test_info_keyspace_fields():
    server = FakeServer(version=(7, 4))
    r = FakeRedis(server=server)
    r.set("persistent", "v")
    r.set("volatile", "v", ex=100)
    FakeRedis(server=server, db=3).set("other", "v")
    fields = server.info_keyspace_fields()
    assert set(fields) == {"db0", "db3"}
    assert {stat: fields["db0"][stat] for stat in ("keys", "expires", "subexpiry")} == {
        "keys": 2,
        "expires": 1,
        "subexpiry": 0,
    }
    assert 99_000 <= fields["db0"]["avg_ttl"] <= 100_000
    assert fields["db3"] == {"keys": 1, "expires": 0, "avg_ttl": 0, "subexpiry": 0}


def test_info_keyspace_fields_skips_expired_keys():
    server = FakeServer()
    r = FakeRedis(server=server)
    r.set("gone", "v", px=1)
    r.set("kept", "v")
    sleep(0.01)
    r.ping()  # every command moves the databases' clocks forward
    assert server.info_keyspace_fields()["db0"]["keys"] == 1


@pytest.mark.parametrize(
    "server_type,version,field",
    [("redis", (7, 4), "subexpiry"), ("valkey", (9,), "keys_with_volatile_items")],
)
def test_info_keyspace_fields_counts_hashes_with_field_ttls(server_type, version, field):
    server = FakeServer(server_type=server_type, version=version)
    r = FakeRedis(server=server)
    r.hset("with_ttl", mapping={"f1": "v", "f2": "v"})
    r.hset("without_ttl", "f", "v")
    r.execute_command("HEXPIRE", "with_ttl", 100, "FIELDS", 1, "f1")
    assert server.info_keyspace_fields()["db0"][field] == 1


def test_info_keyspace_fields_empty():
    assert FakeServer().info_keyspace_fields() == {}
    # Dragonfly lists db0 even when nothing was ever stored.
    assert FakeServer(server_type="dragonfly").info_keyspace_fields() == {
        "db0": {"keys": 0, "expires": 0, "avg_ttl": -1}
    }
