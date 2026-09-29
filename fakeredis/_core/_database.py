from __future__ import annotations

import threading
import weakref
from collections import defaultdict
from collections.abc import Iterator, MutableMapping
from typing import Any, Callable


class Database(MutableMapping):  # type: ignore
    def __init__(self, lock: threading.Lock | None, *args: Any, **kwargs: Any) -> None:
        self._dict: dict[bytes, Any] = dict(*args, **kwargs)
        self.time = 0.0
        # key to the set of connections
        self._watches: dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.condition = threading.Condition(lock)
        self._change_callbacks: set[Callable[[], None]] = set()

    def swap(self, other: Database) -> None:
        self._dict, other._dict = other._dict, self._dict
        self.time, other.time = other.time, self.time

    def notify_watch(self, key: bytes) -> None:
        for sock in self._watches.get(key, set()):
            sock.notify_watch()
        self.wake_all()

    def wake_all(self) -> None:
        """Wake every client blocked on this database, without reporting a key change.

        Used by CLIENT UNBLOCK: woken clients re-check their own state and go back to sleep unless they were the target.
        """
        self.condition.notify_all()
        for callback in self._change_callbacks:
            callback()

    def has_watch(self, key: bytes) -> bool:
        """Whether any client is watching `key`."""
        return bool(self._watches.get(key))

    def add_watch(self, key: bytes, sock: Any) -> None:
        self._watches[key].add(sock)

    def remove_watch(self, key: bytes, sock: Any) -> None:
        watches = self._watches[key]
        watches.discard(sock)
        if not watches:
            del self._watches[key]

    def add_change_callback(self, callback: Callable[[], None]) -> None:
        self._change_callbacks.add(callback)

    def remove_change_callback(self, callback: Callable[[], None]) -> None:
        self._change_callbacks.remove(callback)

    def clear(self) -> None:
        for key in self:
            self.notify_watch(key)
        self._dict.clear()

    def expired(self, item: Any) -> bool:
        return item.expireat is not None and item.expireat < self.time

    def _remove_expired(self) -> None:
        for key in list(self._dict):
            item = self._dict[key]
            if self.expired(item):
                del self._dict[key]

    def __getitem__(self, key: bytes) -> Any:
        item = self._dict[key]
        if self.expired(item):
            del self._dict[key]
            raise KeyError(key)
        return item

    def __setitem__(self, key: bytes, value: Any) -> None:
        self._dict[key] = value

    def __delitem__(self, key: bytes) -> None:
        del self._dict[key]

    def __iter__(self) -> Iterator[bytes]:
        self._remove_expired()
        return iter(self._dict)

    def __len__(self) -> int:
        self._remove_expired()
        return len(self._dict)

    # Databases use identity semantics: they are mutable and are keyed by index on the server, never compared by
    # content.
    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: object) -> bool:
        return self is other
