import pytest
import time
from redis.client import PubSub

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

def test_keyspace_notifications():
    import fakeredis
    
    server = fakeredis.FakeServer()
    r = fakeredis.FakeRedis(server=server)
    
    # Enable keyspace notifications in redis
    r.config_set('notify-keyspace-events', 'KEA')
    
    p = r.pubsub()
    p.psubscribe('__keyspace@0__:*')
    p.psubscribe('__keyevent@0__:*')
    
    msg1 = wait_for_message(p)
    msg2 = wait_for_message(p)
    assert msg1['type'] == 'psubscribe'
    assert msg2['type'] == 'psubscribe'
    
    r.set('foo', 'bar')
    
    msgs = []
    msg = wait_for_message(p, timeout=1.0)
    while msg is not None:
        msgs.append(msg)
        msg = wait_for_message(p, timeout=0.1)
        
    assert len(msgs) >= 2
    
    keyspace_msg = next((m for m in msgs if m['channel'] == b'__keyspace@0__:foo'), None)
    keyevent_msg = next((m for m in msgs if m['channel'] == b'__keyevent@0__:set'), None)
    
    assert keyspace_msg is not None
    assert keyspace_msg['data'] == b'set'
    
    assert keyevent_msg is not None
    assert keyevent_msg['data'] == b'foo'
