"""Tests for hash-field subkey notifications (redis 8.8).

Subkey notifications are controlled by the `notify-keyspace-events` config: the `h` class flag
enables hash-command events, and each of the S/T/I/V flags enables one subkey channel type.
"""

import time
from typing import List, Tuple

import pytest

from fakeredis._typing import ClientType

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.supported_server_versions(min_redis_ver="8.7.2"),
        pytest.mark.unsupported_server_types("dragonfly", "valkey"),
    ]
)


def collect_messages(pubsub, timeout=1.0) -> List[Tuple[bytes, bytes]]:
    """Collect (channel, data) of pmessages until no message arrives within a short poll window."""
    deadline = time.time() + timeout
    messages = []
    while time.time() < deadline:
        message = pubsub.get_message(ignore_subscribe_messages=True)
        if message is None:
            if messages:
                break
            time.sleep(0.01)
            continue
        if message["type"] == "pmessage":
            messages.append((message["channel"], message["data"]))
    return messages


@pytest.fixture
def pubsub(r: ClientType):
    r.config_set("notify-keyspace-events", "STIVh")
    p = r.pubsub()
    p.psubscribe("__subkey*")
    message = p.get_message(timeout=1.0)
    assert message["type"] == "psubscribe"
    yield p
    r.config_set("notify-keyspace-events", "")
    p.close()


def test_subkey_hset(r: ClientType, pubsub):
    r.hset("hash", mapping={"field1": "v1", "field2": "v2"})
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hset|6:field1,6:field2") in messages
    assert (b"__subkeyevent@2__:hset", b"4:hash|6:field1,6:field2") in messages
    assert (b"__subkeyspaceitem@2__:hash\nfield1", b"hset") in messages
    assert (b"__subkeyspaceitem@2__:hash\nfield2", b"hset") in messages
    assert (b"__subkeyspaceevent@2__:hset|hash", b"6:field1,6:field2") in messages


def test_subkey_hdel(r: ClientType, pubsub):
    r.hset("hash", mapping={"field1": "v1", "field2": "v2"})
    collect_messages(pubsub)
    r.hdel("hash", "field1", "missing")
    messages = collect_messages(pubsub)
    # Only actually-deleted fields are included
    assert (b"__subkeyspace@2__:hash", b"hdel|6:field1") in messages
    assert (b"__subkeyspaceevent@2__:hdel|hash", b"6:field1") in messages


def test_subkey_hsetnx(r: ClientType, pubsub):
    r.hsetnx("hash", "field", "v1")
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hset|5:field") in messages
    # HSETNX on an existing field does not fire an event
    r.hsetnx("hash", "field", "v2")
    assert collect_messages(pubsub, timeout=0.3) == []


def test_subkey_hincrby(r: ClientType, pubsub):
    r.hincrby("hash", "counter", 5)
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hincrby|7:counter") in messages
    r.hincrbyfloat("hash", "fcounter", 1.5)
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hincrbyfloat|8:fcounter") in messages


def test_subkey_hexpire_and_hpersist(r: ClientType, pubsub):
    r.hset("hash", mapping={"field1": "v1", "field2": "v2"})
    collect_messages(pubsub)
    r.hexpire("hash", 100, "field1", "field2")
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hexpire|6:field1,6:field2") in messages
    r.hpersist("hash", "field1")
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hpersist|6:field1") in messages
    # HPERSIST on a field without a TTL does not fire an event
    r.hpersist("hash", "field1")
    assert collect_messages(pubsub, timeout=0.3) == []


def test_subkey_hexpire_past_deletes(r: ClientType, pubsub):
    r.hset("hash", mapping={"field1": "v1", "field2": "v2"})
    collect_messages(pubsub)
    # Expiration in the past deletes the field immediately, firing hdel
    r.hexpire("hash", 0, "field1")
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hdel|6:field1") in messages


def test_subkey_hexpired(r: ClientType, pubsub):
    r.hset("hash", "field", "v1")
    r.hpexpire("hash", 30, "field")
    collect_messages(pubsub)
    time.sleep(0.15)
    r.hget("hash", "field")
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hexpired|5:field") in messages
    assert (b"__subkeyspaceitem@2__:hash\nfield", b"hexpired") in messages


def test_subkey_hsetex(r: ClientType, pubsub):
    r.execute_command("HSETEX", "hash", "EX", 100, "FIELDS", 1, "field", "v1")
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hset|5:field") in messages
    assert (b"__subkeyspace@2__:hash", b"hexpire|5:field") in messages


def test_subkey_hgetdel(r: ClientType, pubsub):
    r.hset("hash", "field", "v1")
    collect_messages(pubsub)
    r.execute_command("HGETDEL", "hash", "FIELDS", 1, "field")
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hdel|5:field") in messages


def test_subkey_binary_safe_payload(r: ClientType, pubsub):
    r.hset("hash", mapping={b"fi|eld": b"v"})
    messages = collect_messages(pubsub)
    assert (b"__subkeyspace@2__:hash", b"hset|6:fi|eld") in messages


def test_subkey_single_channel_flag(r: ClientType):
    # Only the subkeyspace channel is enabled
    r.config_set("notify-keyspace-events", "Sh")
    p = r.pubsub()
    p.psubscribe("__subkey*")
    assert p.get_message(timeout=1.0)["type"] == "psubscribe"
    r.hset("hash", "field", "v1")
    messages = collect_messages(p)
    assert messages == [(b"__subkeyspace@2__:hash", b"hset|5:field")]
    r.config_set("notify-keyspace-events", "")
    p.close()


def test_subkey_disabled_without_flags(r: ClientType):
    r.config_set("notify-keyspace-events", "")
    p = r.pubsub()
    p.psubscribe("__subkey*")
    assert p.get_message(timeout=1.0)["type"] == "psubscribe"
    r.hset("hash", "field", "v1")
    assert collect_messages(p, timeout=0.3) == []
    # The channel flags alone are not enough: the hash class flag `h` is required as well
    r.config_set("notify-keyspace-events", "STIV")
    r.hset("hash", "field2", "v2")
    assert collect_messages(p, timeout=0.3) == []
    r.config_set("notify-keyspace-events", "")
    p.close()
