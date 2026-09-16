import threading
import time
from unittest import mock

import pytest
import redis

from fakeredis import FakeServer
from fakeredis._fakesocket import FakeSocket
from fakeredis._helpers import FakeSelector

pytestmark = [pytest.mark.fake]


@pytest.fixture
def sock() -> FakeSocket:
    return FakeSocket(FakeServer(), db=0, client_class=redis.Redis)


def test_zero_timeout_does_not_wait(sock: FakeSocket):
    selector = FakeSelector(sock)
    assert selector.check_can_read(0) is False
    sock.put_response(b"x")
    assert selector.check_can_read(0) is True


def test_times_out(sock: FakeSocket):
    start = time.monotonic()
    assert FakeSelector(sock).check_can_read(0.05) is False
    assert time.monotonic() - start >= 0.05


def test_wakes_when_a_response_is_queued(sock: FakeSocket):
    timer = threading.Timer(0.02, sock.put_response, args=(b"x",))
    start = time.monotonic()
    timer.start()
    assert FakeSelector(sock).check_can_read(10) is True
    assert time.monotonic() - start < 5
    timer.join()


def test_stale_event_is_not_readable(sock: FakeSocket):
    # Draining the queue does not clear the event, so the selector must not trust the event alone.
    sock.put_response(b"x")
    sock.responses.get_nowait()
    assert FakeSelector(sock).check_can_read(0.02) is False


def test_wakes_when_the_socket_closes(sock: FakeSocket):
    timer = threading.Timer(0.02, sock.close)
    start = time.monotonic()
    timer.start()
    assert FakeSelector(sock).check_can_read(10) is False
    assert time.monotonic() - start < 5
    timer.join()


@pytest.mark.timeout(10)
def test_times_out_with_a_frozen_clock(sock: FakeSocket):
    with mock.patch("time.monotonic", return_value=1000.0):
        assert FakeSelector(sock).check_can_read(0.05) is False
