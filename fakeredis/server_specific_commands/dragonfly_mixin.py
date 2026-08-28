from __future__ import annotations

from typing import Any, Callable

from fakeredis import _msgs as msgs
from fakeredis._commands import CommandItem, Int, Key, command
from fakeredis._helpers import Database, SimpleError, current_time
from fakeredis.model import ExpiringMembersSet

_INT64_MAX = 2**63 - 1
_UINT64_MAX = 2**64 - 1
_NS_PER_SECOND = 1_000_000_000
_NS_PER_MS = 1_000_000
_MS_PER_SECOND = 1_000

# Dragonfly specific error messages
THROTTLE_ZERO_RATES_MSG = "ERR zero rates are not supported"


def _trunc_div(numerator: int, denominator: int) -> int:
    """Integer division truncating towards zero, as C does (Python floors instead)."""
    quotient = abs(numerator) // abs(denominator)
    return quotient if (numerator < 0) == (denominator < 0) else -quotient


def _ns_to_ms(value_ns: int) -> int:
    return _trunc_div(value_ns + _NS_PER_MS - 1, _NS_PER_MS)


def _ms_to_seconds(value_ms: int) -> int:
    seconds = _trunc_div(value_ms, _MS_PER_SECOND)
    return seconds + 1 if value_ms > 0 else seconds


class DragonflyCommandsMixin:
    _expireat: Callable[[CommandItem, int], int]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._db: Database

    @command(name="SADDEX", fixed=(Key(ExpiringMembersSet), Int, bytes), repeat=(bytes,), server_types=("dragonfly",))
    def saddex(self, key: CommandItem, seconds: int, *members: bytes) -> int:
        val = key.value
        old_size = len(val)
        expire_at_ms = current_time() + seconds * 1000
        # The expiry is applied to every listed member, including ones already in the set (their existing TTL is
        # refreshed), but only newly added members are counted.
        for member in members:
            val.set_member_expireat(member, expire_at_ms)
        key.updated()
        return len(val) - old_size

    @command(name="CL.THROTTLE", fixed=(Key(bytes), Int, Int, Int), repeat=(Int,), server_types=("dragonfly",))
    def cl_throttle(self, key: CommandItem, max_burst: int, count: int, period: int, *args: int) -> list[int]:
        # Dragonfly reads the numeric arguments as unsigned 64-bit integers and ignores anything given after the
        # optional `quantity`.
        quantity = args[0] if args else 1
        if min(max_burst, count, period, quantity) < 0 or max_burst > _INT64_MAX - 1:
            raise SimpleError(msgs.INVALID_INT_MSG)
        limit = max_burst + 1
        if count == 0 or period > _UINT64_MAX // _NS_PER_SECOND or period * _NS_PER_SECOND // count > _INT64_MAX:
            raise SimpleError(msgs.INVALID_INT_MSG)
        emission_interval_ns = period * _NS_PER_SECOND // count
        if emission_interval_ns == 0:
            raise SimpleError(THROTTLE_ZERO_RATES_MSG)
        if emission_interval_ns > _INT64_MAX // limit or (
            quantity != 0 and emission_interval_ns > _INT64_MAX // quantity
        ):
            raise SimpleError(msgs.INVALID_INT_MSG)

        # Generic cell rate algorithm (GCRA), a leaky bucket over a rolling time window: the key holds `tat`, the
        # theoretical arrival time of the next conforming request, in nanoseconds.
        delay_variation_tolerance_ns = emission_interval_ns * limit  # total size of the bucket
        increment_ns = emission_interval_ns * quantity  # cost of this request
        now_ns = int(self._db.time * _NS_PER_SECOND)
        tat_ns = Int.decode(key.value) if key.value is not None else now_ns
        new_tat_ns = max(tat_ns, now_ns) + increment_ns
        if new_tat_ns > _INT64_MAX:
            raise SimpleError(msgs.INVALID_INT_MSG)
        # The cutoff point before which a request is rejected (throttled) and at or after which a request is accepted.
        allow_at_ns = new_tat_ns - delay_variation_tolerance_ns
        limited = now_ns < allow_at_ns

        retry_after_ms = -_MS_PER_SECOND
        if limited:
            if increment_ns <= delay_variation_tolerance_ns:
                retry_after_ms = _ns_to_ms(allow_at_ns - now_ns)
            ttl_ns = tat_ns - now_ns
        else:
            ttl_ns = new_tat_ns - now_ns
            key.update(Int.encode(new_tat_ns))
            # The key holds nanoseconds but expires on a millisecond granularity, so its expiry is rounded up to avoid
            # dropping `tat` while it is still relevant.
            key.expireat = _ns_to_ms(new_tat_ns) / _MS_PER_SECOND

        next_ns = delay_variation_tolerance_ns - ttl_ns
        remaining = _trunc_div(next_ns, emission_interval_ns) if next_ns > -emission_interval_ns else 0
        return [
            1 if limited else 0,
            limit,
            remaining,
            _ms_to_seconds(retry_after_ms),
            _ms_to_seconds(_ns_to_ms(ttl_ns)),
        ]
