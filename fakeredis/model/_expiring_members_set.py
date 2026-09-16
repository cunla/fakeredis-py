from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any

from fakeredis._helpers import current_time
from fakeredis._typing import Self

from ._base_type import BaseModel


class ExpiringMembersSet(BaseModel):
    _model_type = b"set"

    def __init__(self, values: dict[bytes, int | None] | None = None, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._values: dict[bytes, int | None] = values or {}
        # Whether any member may carry a TTL, so reads on the common set with none can skip the expiry scan. It can be
        # left True after the last TTL is gone, but is never False while one remains.
        self._may_expire = any(v is not None for v in self._values.values())

    def _expire_members(self) -> None:
        if not self._may_expire:
            return
        now = current_time()
        removed = [k for k, when_ms in self._values.items() if when_ms is not None and when_ms < now]
        for k in removed:
            self._values.pop(k)
        self._may_expire = any(v is not None for v in self._values.values())

    def set_member_expireat(self, key: bytes, when_ms: int) -> int:
        now = current_time()
        if when_ms <= now:
            self._values.pop(key, None)
            return 2
        self._values[key] = when_ms
        self._may_expire = True
        return 1

    def clear_key_expireat(self, key: bytes) -> bool:
        """Remove the TTL of member `key`, keeping the member. Returns whether it had one."""
        self._expire_members()
        if self._values.get(key) is None:
            return False
        self._values[key] = None
        return True

    def get_key_expireat(self, key: bytes) -> int | None:
        self._expire_members()
        return self._values.get(key, None)

    def __contains__(self, key: bytes) -> bool:
        self._expire_members()
        return self._values.__contains__(key)

    def __delitem__(self, key: bytes) -> None:
        self._values.pop(key, None)

    def __len__(self) -> int:
        self._expire_members()
        return len(self._values)

    def __iter__(self) -> Iterator[bytes]:
        self._expire_members()
        now = current_time()
        return iter({k for k, when_ms in self._values.items() if when_ms is None or when_ms >= now})

    def __get__(self, instance: object, owner: None = None) -> set[bytes]:
        self._expire_members()
        return set(self._values.keys())

    def __sub__(self, other: Self) -> ExpiringMembersSet:
        self._expire_members()
        other._expire_members()
        return ExpiringMembersSet({k: v for k, v in self._values.items() if k not in other._values})

    def __and__(self, other: Self) -> ExpiringMembersSet:
        self._expire_members()
        other._expire_members()
        return ExpiringMembersSet({k: v for k, v in self._values.items() if k in other._values})

    def __or__(self, other: Self) -> ExpiringMembersSet:
        self._expire_members()
        other._expire_members()
        return ExpiringMembersSet(dict(self._values.items())).update(other)

    def update(self, other: Self | Iterable[bytes]) -> Self:
        self._expire_members()
        if isinstance(other, ExpiringMembersSet):
            self._values.update(other._values)
            self._may_expire = self._may_expire or other._may_expire
            return self
        for value in other:
            self._values[value] = None
        return self

    def discard(self, key: bytes) -> None:
        self._values.pop(key, None)

    def remove(self, key: bytes) -> None:
        self._values.pop(key)

    def add(self, key: bytes) -> None:
        self._values[key] = None

    def copy(self) -> ExpiringMembersSet:
        return ExpiringMembersSet(self._values.copy())
