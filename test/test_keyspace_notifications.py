import time

import pytest
import redis
from redis.client import PubSub

# Dragonfly implements only the `Ex` event class (expired keyevents), enabled with the `--notify_keyspace_events=Ex`
# startup flag; `CONFIG SET notify-keyspace-events` always fails there.
pytestmark = pytest.mark.unsupported_server_types("dragonfly")


def wait_for_message(pubsub: PubSub, timeout=0.5, ignore_subscribe_messages=False):
    now = time.time()
    timeout = now + timeout
    while now < timeout:
        message = pubsub.get_message(ignore_subscribe_messages=ignore_subscribe_messages)
        if message is not None:
            return message
        time.sleep(0.01)
        now = time.time()
    return None


def test_keyspace_notifications_keyspace(r: redis.Redis):
    # Enable keyspace notifications in redis
    r.config_set("notify-keyspace-events", "KEA")

    p = r.pubsub()
    p.psubscribe("__keyspace@*__:*")

    msg1 = wait_for_message(p)

    assert msg1["type"] == "psubscribe"

    r.set("foo", "bar")

    msgs = []
    msg = wait_for_message(p, timeout=1.0)
    while msg is not None:
        msgs.append(msg)
        msg = wait_for_message(p, timeout=0.1)

    assert len(msgs) >= 1
    keyspace_msg = next((m for m in msgs if m["channel"] == b"__keyspace@2__:foo"), None)

    assert keyspace_msg is not None
    assert keyspace_msg["data"] == b"set"


def test_keyspace_notifications_event(r: redis.Redis):
    # Enable keyspace notifications in redis
    r.config_set("notify-keyspace-events", "KEA")

    p = r.pubsub()
    p.psubscribe("__keyevent@*__:*")

    msg1 = wait_for_message(p)
    assert msg1["type"] == "psubscribe"

    r.set("foo", "bar")

    msgs = []
    msg = wait_for_message(p, timeout=1.0)
    while msg is not None:
        msgs.append(msg)
        msg = wait_for_message(p, timeout=0.1)

    assert len(msgs) >= 1

    # We are using db=2 based on conftest.py
    keyevent_msg = next((m for m in msgs if m["channel"] == b"__keyevent@2__:set"), None)

    assert keyevent_msg is not None
    assert keyevent_msg["data"] == b"foo"


@pytest.mark.supported_server_versions(min_redis_ver="8.10")
@pytest.mark.unsupported_server_types("valkey", "dragonfly", "kividb")
def test_keyspace_notifications_himport_set(r: redis.Redis):
    r.config_set("notify-keyspace-events", "KEA")
    p = r.pubsub()
    p.psubscribe("__key*@*__:*")
    assert wait_for_message(p)["type"] == "psubscribe"

    r.execute_command("HIMPORT", "PREPARE", "fs", "a")
    r.execute_command("HIMPORT", "SET", "foo", "fs", "1")

    msgs = []
    msg = wait_for_message(p, timeout=1.0)
    while msg is not None:
        msgs.append((msg["channel"], msg["data"]))
        msg = wait_for_message(p, timeout=0.1)
    # It is reported as the `hset` it amounts to.
    assert msgs == [(b"__keyspace@2__:foo", b"hset"), (b"__keyevent@2__:hset", b"foo")]
