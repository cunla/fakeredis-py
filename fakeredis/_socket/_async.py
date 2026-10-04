from __future__ import annotations

import asyncio
import threading
from typing import Any, Callable

import redis.asyncio as redis_async

from fakeredis._helpers import NoResponse, SimpleError
from fakeredis._socket._fakesocket import FakeSocket
from fakeredis._typing import async_timeout


class AsyncFakeSocket(FakeSocket):
    _connection_error_class = redis_async.ConnectionError

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.responses: asyncio.Queue = asyncio.Queue()  # type:ignore
        # Set whenever a response is enqueued so can_read() can wait on it instead of polling the queue (see can_read).
        self._response_available: asyncio.Event = asyncio.Event()
        self._event_loop = asyncio.get_running_loop()
        self._loop_thread_ident = threading.get_ident()

    def put_response(self, msg: Any) -> None:
        if not self.responses:
            return
        self.responses.put_nowait(msg)
        if threading.get_ident() == self._loop_thread_ident:
            self._response_available.set()
        else:
            # Called from another thread, e.g. a sync client publishing to a channel this socket subscribes to on a
            # shared FakeServer: a plain set() would not wake this socket's sleeping event loop, so the wakeup must be
            # marshalled through it.
            try:
                self._event_loop.call_soon_threadsafe(self._response_available.set)
            except RuntimeError:  # the loop is already closed
                pass

    async def _async_blocking(
        self,
        timeout: float | None,
        func: Callable[[bool], Any],
        event: asyncio.Event,
        callback: Callable[[], None],
        shape: Callable[[Any], Any] | None = None,
    ) -> None:
        def empty() -> Any:
            """The reply for an empty outcome -- a timeout, or an unblock with TIMEOUT -- shaped when it happens."""
            return None if shape is None else self._decode_result(shape(None))

        result: Any = None
        try:
            async with async_timeout(timeout if timeout else None):
                while True:
                    await event.wait()
                    event.clear()
                    # This is a coroutine outside the normal control flow that locks the server, so we have to take our
                    # own lock.
                    with self._server.lock:
                        if self._unblock_reason is not None:
                            try:
                                self._take_unblock_reason()
                                result = empty()
                            except SimpleError as exc:
                                result = self._decode_result(exc)
                            break
                        ret = func(False)
                        if ret is not None:
                            result = self._decode_result(ret if shape is None else shape(ret))
                            break
        except asyncio.TimeoutError:
            with self._server.lock:
                result = empty()
        finally:
            with self._server.lock:
                self._db.remove_change_callback(callback)
                self._blocked = False
                self._unblock_reason = None
            self.put_response(result)
            self.resume()

    def _blocking(
        self,
        timeout: float | None,
        func: Callable[[bool], None],
        shape: Callable[[Any], Any] | None = None,
    ) -> Any:
        # A command only ever blocks from inside the client's running event loop.
        loop = asyncio.get_running_loop()
        ret = func(True)
        if ret is not None or self._in_transaction:
            return ret if shape is None else shape(ret)
        event = asyncio.Event()

        def callback() -> None:
            loop.call_soon_threadsafe(event.set)

        self._db.add_change_callback(callback)
        self._blocked = True
        self.pause()
        # `shape` travels with the task: the reply is put on the queue from there, past the point where the command that
        # blocked could still touch it.
        loop.create_task(self._async_blocking(timeout, func, event, callback, shape))
        return NoResponse()
