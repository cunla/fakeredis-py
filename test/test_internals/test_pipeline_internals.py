from __future__ import annotations

import pytest

import fakeredis


@pytest.mark.fake
def test_get_within_pipeline_w_host():
    r = fakeredis.FakeRedis("localhost")
    r.set("test", "foo")
    r.set("test2", "foo2")
    expected_keys = set(r.keys())
    with r.pipeline() as p:
        assert set(r.keys()) == expected_keys
        p.watch("test")
        assert set(r.keys()) == expected_keys


@pytest.mark.fake
def test_get_within_pipeline_no_args():
    r = fakeredis.FakeRedis()
    r.set("test", "foo")
    r.set("test2", "foo2")
    expected_keys = set(r.keys())
    with r.pipeline() as p:
        assert set(r.keys()) == expected_keys
        p.watch("test")
        assert set(r.keys()) == expected_keys


@pytest.mark.fake
def test_socket_cleanup_watch(fake_server):
    r1 = fakeredis.FakeStrictRedis(server=fake_server)
    r2 = fakeredis.FakeStrictRedis(server=fake_server)
    pipeline = r1.pipeline(transaction=False)
    # This needs some poking into redis-py internals to ensure that we reach
    # FakeSocket._cleanup. We need to close the socket while there is still
    # a watch in place, but not allow it to be garbage collected (hence we
    # set 'sock' even though it is unused).
    with pipeline:
        pipeline.watch("test")
        sock = pipeline.connection._sock  # noqa: F841
        pipeline.connection.disconnect()
    r2.set("test", "foo")
