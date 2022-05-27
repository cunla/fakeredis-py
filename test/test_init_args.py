import pytest

import fakeredis
import testtools


@pytest.mark.fake
class TestInitArgs:
    def test_singleton(self):
        shared_server = fakeredis.FakeServer()
        r1 = fakeredis.FakeStrictRedis()
        r2 = fakeredis.FakeStrictRedis()
        r3 = fakeredis.FakeStrictRedis(server=shared_server)
        r4 = fakeredis.FakeStrictRedis(server=shared_server)

        r1.set('foo', 'bar')
        r3.set('bar', 'baz')

        assert 'foo' in r1
        assert 'foo' not in r2
        assert 'foo' not in r3

        assert 'bar' in r3
        assert 'bar' in r4
        assert 'bar' not in r1

    def test_from_url(self):
        db = fakeredis.FakeStrictRedis.from_url(
            'redis://localhost:6379/0')
        db.set('foo', 'bar')
        assert db.get('foo') == b'bar'

    def test_from_url_user(self):
        db = fakeredis.FakeStrictRedis.from_url(
            'redis://user@localhost:6379/0')
        db.set('foo', 'bar')
        assert db.get('foo') == b'bar'

    def test_from_url_user_password(self):
        db = fakeredis.FakeStrictRedis.from_url(
            'redis://user:password@localhost:6379/0')
        db.set('foo', 'bar')
        assert db.get('foo') == b'bar'

    def test_from_url_with_db_arg(self):
        db = fakeredis.FakeStrictRedis.from_url(
            'redis://localhost:6379/0')
        db1 = fakeredis.FakeStrictRedis.from_url(
            'redis://localhost:6379/1')
        db2 = fakeredis.FakeStrictRedis.from_url(
            'redis://localhost:6379/',
            db=2)
        db.set('foo', 'foo0')
        db1.set('foo', 'foo1')
        db2.set('foo', 'foo2')
        assert db.get('foo') == b'foo0'
        assert db1.get('foo') == b'foo1'
        assert db2.get('foo') == b'foo2'

    def test_from_url_db_value_error(self):
        # In case of ValueError, should default to 0, or be absent in redis-py 4.0
        db = fakeredis.FakeStrictRedis.from_url(
            'redis://localhost:6379/a')
        assert db.connection_pool.connection_kwargs.get('db', 0) == 0

    def test_can_pass_through_extra_args(self):
        db = fakeredis.FakeStrictRedis.from_url(
            'redis://localhost:6379/0',
            decode_responses=True)
        db.set('foo', 'bar')
        assert db.get('foo') == 'bar'

    @testtools.run_test_if_redis_ver('above', '3')
    def test_can_allow_extra_args(self):
        db = fakeredis.FakeStrictRedis.from_url(
            'redis://localhost:6379/0',
            socket_connect_timeout=11, socket_timeout=12, socket_keepalive=True,
            socket_keepalive_options={60: 30}, socket_type=1,
            retry_on_timeout=True,
        )
        fake_conn = db.connection_pool.make_connection()
        assert fake_conn.socket_connect_timeout == 11
        assert fake_conn.socket_timeout == 12
        assert fake_conn.socket_keepalive is True
        assert fake_conn.socket_keepalive_options == {60: 30}
        assert fake_conn.socket_type == 1
        assert fake_conn.retry_on_timeout is True

        # Make fallback logic match redis-py
        db = fakeredis.FakeStrictRedis.from_url(
            'redis://localhost:6379/0',
            socket_connect_timeout=None, socket_timeout=30
        )
        fake_conn = db.connection_pool.make_connection()
        assert fake_conn.socket_connect_timeout == fake_conn.socket_timeout
        assert fake_conn.socket_keepalive_options == {}

    def test_repr(self):
        # repr is human-readable, so we only test that it doesn't crash,
        # and that it contains the db number.
        db = fakeredis.FakeStrictRedis.from_url('redis://localhost:6379/11')
        rep = repr(db)
        assert 'db=11' in rep

    def test_from_unix_socket(self):
        db = fakeredis.FakeStrictRedis.from_url('unix://a/b/c')
        db.set('foo', 'bar')
        assert db.get('foo') == b'bar'
