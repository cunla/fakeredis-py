import fakeredis


def test_singleton():
    conn_generator = fakeredis.FakeRedisConnSingleton()
    conn1 = conn_generator(dict(), False)
    conn2 = conn_generator(dict(), False)
    assert conn1.set('foo', 'bar') is True
    assert conn2.get('foo') == b'bar'


def test_asyncioio_is_used():
    """Redis 4.2+ has support for asyncio and should be preferred over aioredis"""
    from fakeredis import aioredis
    assert not hasattr(aioredis, "__version__")
