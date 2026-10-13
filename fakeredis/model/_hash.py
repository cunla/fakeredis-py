from __future__ import annotations

import heapq
from collections.abc import Iterable, Iterator
from typing import Any, AnyStr

from fakeredis._helpers import asbytes, current_time

from ._base_type import BaseModel


class Hash(BaseModel):
    _model_type = b"hash"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._expirations: dict[bytes, int] = {}
        self._values: dict[bytes, bytes] = {}
        # (expiry, field) for every TTL ever set, soonest first, so a read only looks at the fields that are due
        # rather than at all of them. Entries are not removed when a TTL is cleared or replaced: `_expirations` is the
        # truth, and an entry that no longer matches it is skipped when it surfaces.
        self._expiry_heap: list[tuple[int, bytes]] = []
        # Fields that expired lazily, pending an `hexpired` subkey notification.
        self._expired_fields: list[bytes] = []

    def _expire_keys(self) -> None:
        # Every read lands here, and most hashes never set a field TTL.
        heap = self._expiry_heap
        if not heap:
            return
        now = current_time()
        while heap and heap[0][0] < now:
            _, k = heapq.heappop(heap)
            exp = self._expirations.get(k)
            if exp is not None and exp < now:
                self._values.pop(k, None)
                del self._expirations[k]
                self._expired_fields.append(k)

    def _schedule_expiry(self, key: bytes, when_ms: int) -> None:
        heap = self._expiry_heap
        # Refreshing the same TTLs over and over leaves stale entries behind; rebuild once they outnumber the live ones.
        if len(heap) > 2 * len(self._expirations) + 16:
            heap[:] = [(exp, k) for k, exp in self._expirations.items()]
            heapq.heapify(heap)
        heapq.heappush(heap, (when_ms, key))

    def take_expired_fields(self) -> list[bytes]:
        """Return fields that expired since the last call, clearing the buffer."""
        res, self._expired_fields = self._expired_fields, []
        return res

    def set_key_expireat(self, key: AnyStr, when_ms: int) -> int:
        now = current_time()
        key_bytes = asbytes(key)
        if when_ms <= now:
            self._values.pop(key_bytes, None)
            self._expirations.pop(key_bytes, None)
            return 2
        self._expirations[key_bytes] = when_ms
        self._schedule_expiry(key_bytes, when_ms)
        return 1

    def clear_key_expireat(self, key: AnyStr) -> bool:
        return self._expirations.pop(asbytes(key), None) is not None

    def get_key_expireat(self, key: AnyStr) -> int | None:
        self._expire_keys()
        return self._expirations.get(asbytes(key), None)

    def __getitem__(self, key: AnyStr) -> Any:
        self._expire_keys()
        return self._values.get(asbytes(key))

    def __contains__(self, key: AnyStr) -> bool:
        self._expire_keys()
        return self._values.__contains__(asbytes(key))

    def __setitem__(self, key: AnyStr, value: Any) -> None:
        key_bytes = asbytes(key)
        self._expirations.pop(key_bytes, None)
        self._values[key_bytes] = value

    def __delitem__(self, key: AnyStr) -> None:
        key_bytes = asbytes(key)
        self._values.pop(key_bytes, None)
        self._expirations.pop(key_bytes, None)

    def __len__(self) -> int:
        self._expire_keys()
        return len(self._values)

    def __iter__(self) -> Iterator[bytes]:
        self._expire_keys()
        yield from self._values.keys()

    def get(self, key: AnyStr, default: Any = None) -> Any:
        self._expire_keys()
        return self._values.get(asbytes(key), default)

    # Fields are stored as bytes (every write goes through `asbytes`), and so are values, so the accessors below only
    # copy. They still return lists rather than views: callers delete fields while iterating over the result.
    def keys(self) -> Iterable[bytes]:
        self._expire_keys()
        return list(self._values)

    def values(self) -> Iterable[Any]:
        self._expire_keys()
        return list(self._values.values())

    def items(self) -> Iterable[tuple[bytes, Any]]:
        self._expire_keys()
        return list(self._values.items())

    def update(self, values: dict[bytes, Any], clear_expiration: bool) -> None:
        self._expire_keys()
        if clear_expiration:
            for k, v in values.items():
                self.clear_key_expireat(k)
        for k, v in values.items():
            self._values[asbytes(k)] = v

    def getall(self) -> dict[bytes, bytes]:
        self._expire_keys()
        return self._values.copy()

    def pop(self, key: AnyStr, d: Any = None) -> Any:
        self._expire_keys()
        return self._values.pop(asbytes(key), d)
