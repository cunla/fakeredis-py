import fakeredis


def test_singleton():
    conn_generator = fakeredis.FakeRedisConnSingleton()
    conn1 = conn_generator(dict(), False)
    conn2 = conn_generator(dict(), False)
    assert conn1.set('foo', 'bar') is True
    assert conn2.get('foo') == b'bar'
