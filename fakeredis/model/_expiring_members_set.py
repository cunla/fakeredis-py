from __future__ import annotations

import random
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
        # The members as a list, so SPOP and SRANDMEMBER can pick one by index instead of copying the set each time.
        # Built on first use and dropped (None) by any change it cannot follow cheaply: a new member is appended and a
        # random pop removes its own slot, but removing an arbitrary member would mean searching the list.
        self._members: list[bytes] | None = None

    def _expire_members(self) -> None:
        if not self._may_expire:
            return
        now = current_time()
        removed = [k for k, when_ms in self._values.items() if when_ms is not None and when_ms < now]
        for k in removed:
            self._values.pop(k)
        if removed:
            self._members = None
        self._may_expire = any(v is not None for v in self._values.values())

    def set_member_expireat(self, key: bytes, when_ms: int) -> int:
        now = current_time()
        if when_ms <= now:
            self.discard(key)
            return 2
        if key not in self._values:
            self._members = None
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
        self.discard(key)

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
            self._members = None
            self._values.update(other._values)
            self._may_expire = self._may_expire or other._may_expire
            return self
        if self._members is not None:
            self._members.extend(dict.fromkeys(value for value in other if value not in self._values))
        for value in other:
            self._values[value] = None
        return self

    def discard(self, key: bytes) -> None:
        if self._values.pop(key, self) is not self:
            self._members = None

    def remove(self, key: bytes) -> None:
        self._values.pop(key)
        self._members = None

    def add(self, key: bytes) -> None:
        if self._members is not None and key not in self._values:
            self._members.append(key)
        self._values[key] = None

    def _member_list(self) -> list[bytes]:
        self._expire_members()
        if self._members is None:
            self._members = list(self._values)
        return self._members

    def random_members(self, count: int, distinct: bool = True) -> list[bytes]:
        """Pick `count` random members: different ones (at most all of them) if `distinct`, else with repeats."""
        members = self._member_list()
        if not members:
            return []
        if distinct:
            return random.sample(members, min(count, len(members)))
        return random.choices(members, k=count)

    def pop_random(self) -> bytes:
        """Remove and return a random member. The set must not be empty."""
        members = self._member_list()
        index = random.randrange(len(members))
        # Fill the slot from the end rather than shifting everything after it.
        members[index], members[-1] = members[-1], members[index]
        member = members.pop()
        del self._values[member]
        return member

    def copy(self) -> ExpiringMembersSet:
        return ExpiringMembersSet(self._values.copy())
