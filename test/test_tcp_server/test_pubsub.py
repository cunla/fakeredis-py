import threading
import time
from queue import Queue
from typing import Tuple

import pytest
import redis

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.tcp_server,
    ]
)


def test_pubsub(tcp_server_address: Tuple[str, int]):
    def _listen(pubsub, q):
        count = 0
        for message in pubsub.listen():
            q.put(message)
            count += 1
            if count == 4:
                pubsub.close()

    channel = "ch1"
    patterns = ["ch1*", "ch[1]", "ch?"]

    with redis.Redis(host=tcp_server_address[0], port=tcp_server_address[1]) as r:
        pubsub = r.pubsub(ignore_subscribe_messages=True)
        pubsub.subscribe(channel)
        pubsub.psubscribe(*patterns)
        time.sleep(1)

        q = Queue()
        t = threading.Thread(target=_listen, args=(pubsub, q))
        t.start()
        msg = "hello world"
        r.publish(channel, msg)
        t.join()

        msg1 = q.get()
        msg2 = q.get()
        msg3 = q.get()
        msg4 = q.get()

        bpatterns = [pattern.encode() for pattern in patterns]
        bpatterns.append(channel.encode())
        msg = msg.encode()
        assert msg1["data"] == msg
        assert msg1["channel"] in bpatterns
        assert msg2["data"] == msg
        assert msg2["channel"] in bpatterns
        assert msg3["data"] == msg
        assert msg3["channel"] in bpatterns
        assert msg4["data"] == msg
        assert msg4["channel"] in bpatterns
