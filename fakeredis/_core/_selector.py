from __future__ import annotations

import time
from typing import Any


class FakeSelector:
    def __init__(self, sock: Any):
        self.sock = sock

    def _has_response(self) -> bool:
        responses = self.sock.responses
        return responses is not None and responses.qsize() > 0

    def check_can_read(self, timeout: float | None) -> bool:
        if self._has_response():
            return True
        if timeout is not None and timeout <= 0:
            return False

        # Wait on the socket's `response_ready` event (set by put_response) rather than polling the queue. The event is
        # only cleared here, never by whatever drains the queue, so "set" does NOT imply "queue non-empty". Re-checking
        # the queue right after clear() is therefore mandatory: it absorbs a stale set, and it catches a response queued
        # between the first check and the wait.
        ready = self.sock.response_ready
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            ready.clear()
            if self._has_response():
                return True
            if self.sock.responses is None:  # closed
                return False
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                return False
            if not ready.wait(remaining):
                # The wait itself timed out. Returning here, rather than re-reading the clock, keeps a frozen
                # time.monotonic (freezegun, time-machine) from turning a timeout into an endless wait.
                return self._has_response()

    @staticmethod
    def check_is_ready_for_command(_: Any) -> bool:
        return True
