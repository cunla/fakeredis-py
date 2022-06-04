import fakeredis


def test_singleton():
    conn_generator = fakeredis.FakeRedisConnSingleton()
    conn1 = conn_generator(dict(), False)
    conn2 = conn_generator(dict(), False)
    assert conn1.setex('foo', 'bar', 100) is True
    assert conn2.get('foo') == b'bar'
