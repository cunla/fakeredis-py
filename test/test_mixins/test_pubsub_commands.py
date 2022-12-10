import threading
from queue import Queue
from time import sleep

import pytest
import redis

import fakeredis
from .. import testtools
from ..testtools import raw_command


def test_ping_pubsub(r):
    p = r.pubsub()
    p.subscribe('channel')
    p.parse_response()  # Consume the subscribe command reply
    p.ping()
    assert p.parse_response() == [b'pong', b'']
    p.ping('test')
    assert p.parse_response() == [b'pong', b'test']


@pytest.mark.slow
def test_pubsub_subscribe(r):
    pubsub = r.pubsub()
    pubsub.subscribe("channel")
    sleep(1)
    expected_message = {'type': 'subscribe', 'pattern': None,
                        'channel': b'channel', 'data': 1}
    message = pubsub.get_message()
    keys = list(pubsub.channels.keys())

    key = keys[0]
    key = (key if type(key) == bytes
           else bytes(key, encoding='utf-8'))

    assert len(keys) == 1
    assert key == b'channel'
    assert message == expected_message


@pytest.mark.slow
def test_pubsub_psubscribe(r):
    pubsub = r.pubsub()
    pubsub.psubscribe("channel.*")
    sleep(1)
    expected_message = {'type': 'psubscribe', 'pattern': None,
                        'channel': b'channel.*', 'data': 1}

    message = pubsub.get_message()
    keys = list(pubsub.patterns.keys())
    assert len(keys) == 1
    assert message == expected_message


@pytest.mark.slow
def test_pubsub_unsubscribe(r):
    pubsub = r.pubsub()
    pubsub.subscribe('channel-1', 'channel-2', 'channel-3')
    sleep(1)
    expected_message = {'type': 'unsubscribe', 'pattern': None,
                        'channel': b'channel-1', 'data': 2}
    pubsub.get_message()
    pubsub.get_message()
    pubsub.get_message()

    # unsubscribe from one
    pubsub.unsubscribe('channel-1')
    sleep(1)
    message = pubsub.get_message()
    keys = list(pubsub.channels.keys())
    assert message == expected_message
    assert len(keys) == 2

    # unsubscribe from multiple
    pubsub.unsubscribe()
    sleep(1)
    pubsub.get_message()
    pubsub.get_message()
    keys = list(pubsub.channels.keys())
    assert message == expected_message
    assert len(keys) == 0


@pytest.mark.slow
def test_pubsub_punsubscribe(r):
    pubsub = r.pubsub()
    pubsub.psubscribe('channel-1.*', 'channel-2.*', 'channel-3.*')
    sleep(1)
    expected_message = {'type': 'punsubscribe', 'pattern': None,
                        'channel': b'channel-1.*', 'data': 2}
    pubsub.get_message()
    pubsub.get_message()
    pubsub.get_message()

    # unsubscribe from one
    pubsub.punsubscribe('channel-1.*')
    sleep(1)
    message = pubsub.get_message()
    keys = list(pubsub.patterns.keys())
    assert message == expected_message
    assert len(keys) == 2

    # unsubscribe from multiple
    pubsub.punsubscribe()
    sleep(1)
    pubsub.get_message()
    pubsub.get_message()
    keys = list(pubsub.patterns.keys())
    assert len(keys) == 0


@pytest.mark.slow
def test_pubsub_listen(r):
    def _listen(pubsub, q):
        count = 0
        for message in pubsub.listen():
            q.put(message)
            count += 1
            if count == 4:
                pubsub.close()

    channel = 'ch1'
    patterns = ['ch1*', 'ch[1]', 'ch?']
    pubsub = r.pubsub()
    pubsub.subscribe(channel)
    pubsub.psubscribe(*patterns)
    sleep(1)
    msg1 = pubsub.get_message()
    msg2 = pubsub.get_message()
    msg3 = pubsub.get_message()
    msg4 = pubsub.get_message()
    assert msg1['type'] == 'subscribe'
    assert msg2['type'] == 'psubscribe'
    assert msg3['type'] == 'psubscribe'
    assert msg4['type'] == 'psubscribe'

    q = Queue()
    t = threading.Thread(target=_listen, args=(pubsub, q))
    t.start()
    msg = 'hello world'
    r.publish(channel, msg)
    t.join()

    msg1 = q.get()
    msg2 = q.get()
    msg3 = q.get()
    msg4 = q.get()

    bpatterns = [pattern.encode() for pattern in patterns]
    bpatterns.append(channel.encode())
    msg = msg.encode()
    assert msg1['data'] == msg
    assert msg1['channel'] in bpatterns
    assert msg2['data'] == msg
    assert msg2['channel'] in bpatterns
    assert msg3['data'] == msg
    assert msg3['channel'] in bpatterns
    assert msg4['data'] == msg
    assert msg4['channel'] in bpatterns


@pytest.mark.slow
def test_pubsub_listen_handler(r):
    def _handler(message):
        calls.append(message)

    channel = 'ch1'
    patterns = {'ch?': _handler}
    calls = []

    pubsub = r.pubsub()
    pubsub.subscribe(ch1=_handler)
    pubsub.psubscribe(**patterns)
    sleep(1)
    msg1 = pubsub.get_message()
    msg2 = pubsub.get_message()
    assert msg1['type'] == 'subscribe'
    assert msg2['type'] == 'psubscribe'
    msg = 'hello world'
    r.publish(channel, msg)
    sleep(1)
    for i in range(2):
        msg = pubsub.get_message()
        assert msg is None  # get_message returns None when handler is used
    pubsub.close()
    calls.sort(key=lambda call: call['type'])
    assert calls == [
        {'pattern': None, 'channel': b'ch1', 'data': b'hello world', 'type': 'message'},
        {'pattern': b'ch?', 'channel': b'ch1', 'data': b'hello world', 'type': 'pmessage'}
    ]


@pytest.mark.slow
def test_pubsub_ignore_sub_messages_listen(r):
    def _listen(pubsub, q):
        count = 0
        for message in pubsub.listen():
            q.put(message)
            count += 1
            if count == 4:
                pubsub.close()

    channel = 'ch1'
    patterns = ['ch1*', 'ch[1]', 'ch?']
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe(channel)
    pubsub.psubscribe(*patterns)
    sleep(1)

    q = Queue()
    t = threading.Thread(target=_listen, args=(pubsub, q))
    t.start()
    msg = 'hello world'
    r.publish(channel, msg)
    t.join()

    msg1 = q.get()
    msg2 = q.get()
    msg3 = q.get()
    msg4 = q.get()

    bpatterns = [pattern.encode() for pattern in patterns]
    bpatterns.append(channel.encode())
    msg = msg.encode()
    assert msg1['data'] == msg
    assert msg1['channel'] in bpatterns
    assert msg2['data'] == msg
    assert msg2['channel'] in bpatterns
    assert msg3['data'] == msg
    assert msg3['channel'] in bpatterns
    assert msg4['data'] == msg
    assert msg4['channel'] in bpatterns


@pytest.mark.slow
def test_pubsub_binary(r):
    def _listen(pubsub, q):
        for message in pubsub.listen():
            q.put(message)
            pubsub.close()

    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe('channel\r\n\xff')
    sleep(1)

    q = Queue()
    t = threading.Thread(target=_listen, args=(pubsub, q))
    t.start()
    msg = b'\x00hello world\r\n\xff'
    r.publish('channel\r\n\xff', msg)
    t.join()

    received = q.get()
    assert received['data'] == msg


@pytest.mark.slow
def test_pubsub_run_in_thread(r):
    q = Queue()

    pubsub = r.pubsub()
    pubsub.subscribe(channel=q.put)
    pubsub_thread = pubsub.run_in_thread()

    msg = b"Hello World"
    r.publish("channel", msg)

    retrieved = q.get()
    assert retrieved["data"] == msg

    pubsub_thread.stop()
    # Newer versions of redis wait for an unsubscribe message, which sometimes comes early
    # https://github.com/andymccurdy/redis-py/issues/1150
    if pubsub.channels:
        pubsub.channels = {}
    pubsub_thread.join()
    assert not pubsub_thread.is_alive()

    pubsub.subscribe(channel=None)
    with pytest.raises(redis.exceptions.PubSubError):
        pubsub_thread = pubsub.run_in_thread()

    pubsub.unsubscribe("channel")

    pubsub.psubscribe(channel=None)
    with pytest.raises(redis.exceptions.PubSubError):
        pubsub_thread = pubsub.run_in_thread()


@pytest.mark.slow
@pytest.mark.parametrize(
    "timeout_value",
    [
        1,
        pytest.param(
            None,
            marks=testtools.run_test_if_redispy_ver('above', '3.2')
        )
    ]
)
def test_pubsub_timeout(r, timeout_value):
    def publish():
        sleep(0.1)
        r.publish('channel', 'hello')

    p = r.pubsub()
    p.subscribe('channel')
    p.parse_response()  # Drains the subscribe command message
    publish_thread = threading.Thread(target=publish)
    publish_thread.start()
    message = p.get_message(timeout=timeout_value)
    assert message == {
        'type': 'message', 'pattern': None,
        'channel': b'channel', 'data': b'hello'
    }
    publish_thread.join()

    if timeout_value is not None:
        # For infinite timeout case don't wait for the message that will never appear.
        message = p.get_message(timeout=timeout_value)
        assert message is None


@pytest.mark.fake
def test_socket_cleanup_pubsub(fake_server):
    r1 = fakeredis.FakeStrictRedis(server=fake_server)
    r2 = fakeredis.FakeStrictRedis(server=fake_server)
    ps = r1.pubsub()
    with ps:
        ps.subscribe('test')
        ps.psubscribe('test*')
    r2.publish('test', 'foo')


def test_pubsub_no_subcommands(r):
    with pytest.raises(redis.ResponseError):
        raw_command(r, "PUBSUB")


def test_pubsub_help(r):
    assert raw_command(r, "PUBSUB HELP") == [
        b'PUBSUB <subcommand> [<arg> [value] [opt] ...]. Subcommands are:',
        b'CHANNELS [<pattern>]',
        b"    Return the currently active channels matching a <pattern> (default: '*')"
        b'.',
        b'NUMPAT',
        b'    Return number of subscriptions to patterns.',
        b'NUMSUB [<channel> ...]',
        b'    Return the number of subscribers for the specified channels, excluding',
        b'    pattern subscriptions(default: no channels).',
        b'SHARDCHANNELS [<pattern>]',
        b'    Return the currently active shard level channels matching a <pattern> (d'
        b"efault: '*').",
        b'SHARDNUMSUB [<shardchannel> ...]',
        b'    Return the number of subscribers for the specified shard level channel(s'
        b')',
        b'HELP',
        b'    Prints this help.'
    ]
