import time

import pytest
from redis.client import PubSub

from fakeredis._typing import ClientType

# Dragonfly implements only the `Ex` event class (expired keyevents), enabled with the `--notify_keyspace_events=Ex`
# startup flag; `CONFIG SET notify-keyspace-events` always fails there.
pytestmark = pytest.mark.unsupported_server_types("dragonfly")


def wait_for_message(pubsub: PubSub, timeout: float = 0.5, ignore_subscribe_messages: bool = False):
    now = time.time()
    timeout = now + timeout
    while now < timeout:
        message = pubsub.get_message(ignore_subscribe_messages=ignore_subscribe_messages)
        if message is not None:
            return message
        time.sleep(0.01)
        now = time.time()
    return None


def test_keyspace_notifications_keyspace(r: ClientType):
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


def test_keyspace_notifications_event(r: ClientType):
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
