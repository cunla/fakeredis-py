from __future__ import annotations

import bisect
import itertools
import re
import time
from collections import Counter
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from typing import Any, AnyStr, NamedTuple

from fakeredis import _msgs as msgs
from fakeredis._commands import AfterAny, BeforeAny
from fakeredis._helpers import SimpleError, current_time

from ._base_type import BaseModel

# Both parts of a stream ID are unsigned 64-bit integers.
MAX_ID_PART = 2**64 - 1
_ID_RE = re.compile(rb"(\d+)(?:-(\d+|\*))?")


class StreamEntryKey(NamedTuple):
    ts: int
    seq: int

    def encode(self) -> bytes:
        return f"{self.ts}-{self.seq}".encode()

    @staticmethod
    def parse_str(entry_key: AnyStr) -> StreamEntryKey:
        return StreamEntryKey.parse_xadd_id(entry_key, allow_seq_star=False)[0]

    @staticmethod
    def parse_xadd_id(entry_key: AnyStr, allow_seq_star: bool) -> tuple[StreamEntryKey, bool]:
        """Parse `ms-seq` (or a bare `ms`, sequence 0), and with `allow_seq_star` XADD's `ms-*` too.

        Returns the ID and whether its sequence was given, which `ms-*` leaves for XADD to pick.
        """
        raw = entry_key.encode() if isinstance(entry_key, str) else entry_key
        match = _ID_RE.fullmatch(raw)
        if match is None or (match[2] == b"*" and not allow_seq_star):
            raise SimpleError(msgs.XADD_INVALID_ID)
        seq_given = match[2] != b"*"
        key = StreamEntryKey(int(match[1]), int(match[2]) if match[2] and seq_given else 0)
        if key.ts > MAX_ID_PART or key.seq > MAX_ID_PART:
            raise SimpleError(msgs.XADD_INVALID_ID)
        return key, seq_given


MIN_KEY = StreamEntryKey(0, 0)
MAX_KEY = StreamEntryKey(MAX_ID_PART, MAX_ID_PART)


def _lp_int_size(value: int) -> int:
    """Bytes a listpack spends on an integer element: its 1-9 byte encoding, plus one byte of back-length."""
    if 0 <= value <= 127:
        encoded = 1
    elif -4096 <= value <= 4095:
        encoded = 2
    elif -32768 <= value <= 32767:
        encoded = 3
    elif -8388608 <= value <= 8388607:
        encoded = 4
    elif -2147483648 <= value <= 2147483647:
        encoded = 5
    else:
        encoded = 9
    return encoded + 1


def _lp_str_size(value: bytes) -> int:
    """Bytes a listpack spends on a string element, which it stores as an integer when it reads as one."""
    digits = value[1:] if value[:1] == b"-" else value
    if value == b"0" or (len(value) < 21 and digits.isdigit() and digits[:1] != b"0"):
        as_int = int(value)
        if -(2**63) <= as_int < 2**63:
            return _lp_int_size(as_int)
    encoded = len(value) + (1 if len(value) < 64 else 2 if len(value) < 4096 else 5)
    if encoded <= 127:
        back_length = 1
    elif encoded <= 16383:
        back_length = 2
    elif encoded <= 2097151:
        back_length = 3
    elif encoded <= 268435455:
        back_length = 4
    else:
        back_length = 5
    return encoded + back_length


# The flag of an entry whose field names are its node's master entry's. (Flagging an entry deleted keeps it one byte.)
_ENTRY_SAMEFIELDS = 2
_LP_EMPTY_SIZE = 7  # listpack header and terminator
_LP_MAX_SIZE = 1 << 30


@dataclass
class _StreamNode:
    """One node of a real stream: a listpack that redis packs consecutive entries into.

    The entries themselves stay in XStream. A node records only what decides where the next node starts and what
    approximate (`~`) trimming may drop in one go: how many entries it holds, live and deleted, and its size in bytes.
    """

    master_id: StreamEntryKey  # the first entry added to the node; later ones are stored relative to it
    master_fields: list[bytes]
    last_id: StreamEntryKey  # the last entry added to the node, deleted or not
    live: int
    deleted: int
    lp_bytes: int

    def set_counts(self, live: int, deleted: int) -> None:
        """Rewrite the live/deleted counters at the head of the listpack, whose size depends on their values."""
        self.lp_bytes += (
            _lp_int_size(live) + _lp_int_size(deleted) - _lp_int_size(self.live) - _lp_int_size(self.deleted)
        )
        self.live, self.deleted = live, deleted


# Delivery count assigned by XNACK FATAL to mark a message as permanently failed (LLONG_MAX in redis)
MAX_DELIVERY_COUNT = 2**63 - 1


class PelEntry(NamedTuple):
    """Pending Entry List entry: tracks consumer ownership and delivery count

    A `time_read` of 0 marks an entry released by XNACK: it is unowned (empty consumer name) and immediately claimable
    regardless of idle time.
    """

    consumer_name: bytes
    time_read: int
    times_delivered: int


class StreamRangeTest:
    """Argument converter for sorted set LEX endpoints."""

    def __init__(self, value: StreamEntryKey | BeforeAny | AfterAny, exclusive: bool):
        self.value = value
        self.exclusive = exclusive

    @staticmethod
    def valid_key(entry_key: AnyStr) -> bool:
        try:
            StreamEntryKey.parse_str(entry_key)
            return True
        except SimpleError:
            return False

    @classmethod
    def decode(cls, value: bytes, exclusive: bool = False, missing_seq: int = 0) -> StreamRangeTest:
        """Parse a range bound; one with no sequence number, a bare millisecond time, takes `missing_seq`.

        That is 0 for the start of a range, and the largest sequence number for its end, which then takes in every
        entry of that millisecond.
        """
        if value == b"-":
            return cls(BeforeAny(), True)
        elif value == b"+":
            return cls(AfterAny(), True)
        elif value[:1] == b"(":
            value, exclusive = value[1:], True
        key = StreamEntryKey.parse_str(value)
        if b"-" not in value:
            key = StreamEntryKey(key.ts, missing_seq)
        return cls(key, exclusive)


@dataclass
class StreamConsumerInfo:
    name: bytes
    pending: int
    last_attempt: int  # Impacted by XREADGROUP, XCLAIM, XAUTOCLAIM
    last_success: int  # Impacted by XREADGROUP, XCLAIM, XAUTOCLAIM

    def __init__(self, name: bytes) -> None:
        self.name = name
        self.pending = 0
        _time = current_time()
        self.last_attempt = _time
        self.last_success = _time

    def info(self, curr_time: int) -> dict[str, bytes | int]:
        return {
            "name": self.name,
            "pending": self.pending,
            "idle": curr_time - self.last_attempt,
            "inactive": curr_time - self.last_success,
        }


class StreamGroup:
    def __init__(
        self,
        stream: XStream,
        name: bytes,
        last_delivered_key: StreamEntryKey,
        entries_read: int | None = None,
    ):
        self.stream = stream
        self.name = name
        # How many of the stream's entries the group has read, or None when that is unknown.
        self.entries_read = entries_read
        # consumer_name -> #pending_messages
        self.consumers: dict[bytes, StreamConsumerInfo] = {}
        self.last_delivered_key = last_delivered_key
        # Pending entry List, see https://redis.io/commands/xreadgroup/
        # msg_id -> PelEntry(consumer_name, time_read, times_delivered)
        self.pel: dict[StreamEntryKey, PelEntry] = {}

    def set_id(self, last_delivered_key: StreamEntryKey, entries_read: int | None) -> None:
        """XGROUP SETID: the group goes on reading after `last_delivered_key`, and has read `entries_read` entries."""
        self.last_delivered_key = last_delivered_key
        self.entries_read = entries_read

    def _mark_delivered(self, key: StreamEntryKey) -> None:
        """Move the group past an entry XREADGROUP has just served, keeping its read counter the way redis does.

        The counter can only be advanced while nothing between the group and the end of the stream was deleted;
        otherwise it is worked out afresh, which may leave it unknown.
        """
        stream = self.stream
        if (
            self.entries_read is not None
            and self.last_delivered_key >= stream.first_id
            and not stream.has_tombstones_from(self.last_delivered_key)
        ):
            self.entries_read += 1
        elif stream.entries_added:
            self.entries_read = stream.estimate_entries_read(key)
        self.last_delivered_key = key

    def lag(self, trim_aware: bool) -> int | None:
        """How many entries the group has yet to read, or None when deletions make that unknowable.

        `trim_aware` adds the two shortcuts Redis 7.4 introduced: an empty stream leaves nothing to read, and a group
        whose last-delivered-id has been trimmed away has the whole stream left to read.
        """
        stream = self.stream
        if not stream.entries_added:
            return 0
        if trim_aware:
            if not len(stream):
                return 0
            if self.last_delivered_key < stream.first_id and stream.max_deleted_id < stream.first_id:
                return len(stream)
        if self.entries_read is not None and not stream.has_tombstones_from(self.last_delivered_key):
            return stream.entries_added - self.entries_read
        entries_read = stream.estimate_entries_read(self.last_delivered_key)
        return None if entries_read is None else stream.entries_added - entries_read

    def add_consumer(self, consumer_name: bytes) -> int:
        if consumer_name in self.consumers:
            return 0
        self.consumers[consumer_name] = StreamConsumerInfo(consumer_name)
        return 1

    def del_consumer(self, consumer_name: bytes) -> int:
        """Drop a consumer and the entries it still owns, returning how many were dropped.

        The count comes from the PEL rather than the cached `pending` counter: entries move between
        consumers, so the counter can disagree with who actually owns what.
        """
        if consumer_name not in self.consumers:
            return 0
        owned = [key for key, entry in self.pel.items() if entry.consumer_name == consumer_name]
        for key in owned:
            del self.pel[key]
        del self.consumers[consumer_name]
        return len(owned)

    def consumers_info(self) -> list[dict[str, bytes | int]]:
        return [self.consumers[k].info(current_time()) for k in self.consumers]

    def group_info(self, trim_aware_lag: bool) -> dict[bytes, Any]:
        res = {
            b"name": self.name,
            b"consumers": len(self.consumers),
            b"pending": len(self.pel),
            b"last-delivered-id": self.last_delivered_key.encode(),
            b"entries-read": self.entries_read,
            b"lag": self.lag(trim_aware_lag),
        }
        return res

    def group_read(
        self, consumer_name: bytes, start_id: bytes, count: int | None, noack: bool
    ) -> list[list[bytes | list[bytes] | None]]:
        _time = current_time()
        if consumer_name not in self.consumers:
            self.consumers[consumer_name] = StreamConsumerInfo(consumer_name)

        self.consumers[consumer_name].last_attempt = _time
        if start_id != b">":
            threshold = StreamEntryKey.parse_str(start_id)
            pel_keys = sorted(k for k, v in self.pel.items() if v.consumer_name == consumer_name and k > threshold)
            if count is not None:
                pel_keys = pel_keys[:count]
            for k in pel_keys:
                entry = self.pel[k]
                self.pel[k] = PelEntry(entry.consumer_name, entry.time_read, entry.times_delivered + 1)
            self.consumers[consumer_name].last_success = _time
            return [self.stream.format_record(k) if k in self.stream else [k.encode(), None] for k in pel_keys]  # type: ignore[misc]
        ids_read = self.stream.stream_read(self.last_delivered_key, count)
        if not noack:
            for k in ids_read:
                # Initialize with times_delivered=1 for new messages
                self.pel[k] = PelEntry(consumer_name, _time, 1)
            self.consumers[consumer_name].pending += len(ids_read)
        for k in ids_read:
            self._mark_delivered(k)
        self.consumers[consumer_name].last_success = _time
        return [self.stream.format_record(x) for x in ids_read]  # type: ignore[misc]

    def _calc_consumer_last_time(self) -> None:
        # pel values are PelEntry namedtuples
        # Extract just consumer_name and time_read for grouping
        new_last_success_map = {
            k: min(v, key=lambda x: x.time_read).time_read
            for k, v in itertools.groupby(self.pel.values(), key=lambda x: x.consumer_name)
        }
        for consumer, last_success in new_last_success_map.items():
            if consumer not in self.consumers:
                self.consumers[consumer] = StreamConsumerInfo(consumer)
            self.consumers[consumer].last_attempt = last_success
            self.consumers[consumer].last_success = last_success

    def nack_entries(
        self,
        ids: list[bytes],
        mode: bytes,
        retry_count: int | None = None,
        force: bool = False,
    ) -> int:
        """Release PEL entries back to the group without acknowledging them.

        mode: b'SILENT' (decrement counter), b'FAIL' (keep counter), b'FATAL' (set to max)
        """
        res = 0
        for id_bytes in ids:
            try:
                key = StreamEntryKey.parse_str(id_bytes)
            except Exception:
                continue

            if key not in self.pel:
                if force and key in self.stream:
                    if retry_count is not None:
                        times = retry_count
                    elif mode == b"FATAL":
                        times = MAX_DELIVERY_COUNT
                    else:
                        times = 0
                    self.pel[key] = PelEntry(b"", 0, times)
                    res += 1
                continue

            entry = self.pel[key]
            old_consumer = entry.consumer_name

            if retry_count is not None:
                new_times = retry_count
            elif mode == b"SILENT":
                new_times = max(0, entry.times_delivered - 1)
            elif mode == b"FATAL":
                new_times = MAX_DELIVERY_COUNT
            else:  # FAIL
                new_times = entry.times_delivered

            if old_consumer and old_consumer in self.consumers:
                self.consumers[old_consumer].pending -= 1

            self.pel[key] = PelEntry(b"", 0, new_times)
            res += 1

        return res

    def ack(self, args: tuple[bytes]) -> int:
        res = 0
        for k in args:
            try:
                parsed = StreamEntryKey.parse_str(k)
            except Exception:
                continue
            if parsed in self.pel:
                # An XNACK-released entry is pending but unowned, so there is nobody to charge the acknowledgement to.
                consumer = self.consumers.get(self.pel[parsed].consumer_name)
                if consumer is not None:
                    consumer.pending -= 1
                del self.pel[parsed]
                res += 1
        self._calc_consumer_last_time()
        return res

    def pending(
        self,
        idle: int | None,
        start: StreamRangeTest | None,
        end: StreamRangeTest | None,
        count: int | None,
        consumer: bytes | None,
    ) -> list[list[bytes | int]]:
        _time = current_time()
        relevant_ids = list(self.pel.keys())
        if consumer is not None:
            relevant_ids = [k for k in relevant_ids if self.pel[k].consumer_name == consumer]
        if idle is not None:
            relevant_ids = [k for k in relevant_ids if self.pel[k].time_read + idle < _time]
        if start is not None and end is not None:
            relevant_ids = [
                k
                for k in relevant_ids
                if (
                    ((start.value < k) or (start.value == k and not start.exclusive))
                    and ((end.value > k) or (end.value == k and not end.exclusive))
                )
            ]
        if count is not None:
            relevant_ids = sorted(relevant_ids)[:count]

        # Return all 4 fields: message_id, consumer, time_since_delivered, times_delivered
        # XNACK-released entries (time_read == 0) report an idle time of -1, as in real redis.
        return [
            [
                k.encode(),
                self.pel[k].consumer_name,
                (_time - self.pel[k].time_read) if self.pel[k].time_read else -1,
                self.pel[k].times_delivered,
            ]
            for k in relevant_ids
        ]

    def pending_summary(self) -> list[Any]:
        # XNACK-released entries are unowned and are not counted under any consumer.
        counter = Counter([self.pel[k].consumer_name for k in self.pel if self.pel[k].consumer_name])
        data = [
            len(self.pel),
            min(self.pel).encode() if len(self.pel) > 0 else None,
            max(self.pel).encode() if len(self.pel) > 0 else None,
            [[i, counter[i]] for i in counter],
        ]
        return data

    def _release_pending(self, consumer_name: bytes) -> None:
        """Drop one entry from a consumer's pending count, if it is still charged to one.

        An XNACK-released entry is unowned (empty consumer name), and XGROUP DELCONSUMER can remove
        a consumer that still owns entries, so the previous owner is not always a live consumer.
        """
        consumer = self.consumers.get(consumer_name)
        if consumer is not None:
            consumer.pending -= 1

    @staticmethod
    def _claimed_delivery_count(previous: int, justid: bool, retrycount: int | None) -> int:
        """Delivery counter a claim leaves behind, matching XCLAIM's option precedence.

        RETRYCOUNT wins over JUSTID, and redis reads a negative RETRYCOUNT as "not given"
        (`if (retrycount >= 0) ... else if (!justid)` in t_stream.c), so `XCLAIM ... RETRYCOUNT -1`
        must still auto-increment. A plain truthiness test would break RETRYCOUNT 0 instead.
        """
        if retrycount is not None and retrycount >= 0:
            return retrycount
        return previous if justid else previous + 1

    def claim(
        self,
        min_idle_ms: int,
        msgs: Sequence[bytes] | Sequence[StreamEntryKey],
        consumer_name: bytes,
        _time: int | None,
        force: bool,
        justid: bool = False,
        retrycount: int | None = None,
    ) -> tuple[list[StreamEntryKey], list[StreamEntryKey]]:
        curr_time = current_time()
        if _time is None:
            _time = curr_time
        if consumer_name not in self.consumers:
            self.consumers[consumer_name] = StreamConsumerInfo(consumer_name)
        self.consumers[consumer_name].last_attempt = curr_time
        claimed_msgs, deleted_msgs = [], []
        for msg in msgs:
            try:
                key = StreamEntryKey.parse_str(msg) if isinstance(msg, bytes) else msg
            except Exception:
                continue
            if key not in self.pel:
                if force:
                    # FORCE creates the entry with a delivery count of 1, then claims it as usual.
                    times_delivered = self._claimed_delivery_count(1, justid, retrycount)
                    self.pel[key] = PelEntry(consumer_name, _time, times_delivered)
                    if key in self.stream:
                        self.consumers[consumer_name].pending += 1
                        claimed_msgs.append(key)
                    else:
                        deleted_msgs.append(key)
                        del self.pel[key]
                continue
            if curr_time - self.pel[key].time_read < min_idle_ms:
                continue  # Not idle enough time to be claimed
            previous_owner = self.pel[key].consumer_name
            old_times_delivered = self.pel[key].times_delivered
            times_delivered = self._claimed_delivery_count(old_times_delivered, justid, retrycount)
            self.pel[key] = PelEntry(consumer_name, _time, times_delivered)
            if key in self.stream:
                if previous_owner != consumer_name:
                    self._release_pending(previous_owner)
                    self.consumers[consumer_name].pending += 1
                claimed_msgs.append(key)
            else:
                # The entry leaves the PEL altogether, so it is charged to nobody afterwards.
                self._release_pending(previous_owner)
                deleted_msgs.append(key)
                del self.pel[key]
        self._calc_consumer_last_time()
        return sorted(claimed_msgs), sorted(deleted_msgs)

    def claim_for_read(self, min_idle_ms: int, consumer_name: bytes, count: int | None) -> list[list[Any]]:
        """Claim idle pending entries for `XREADGROUP ... CLAIM min-idle-time` (Redis 8.4).

        Entries pending for at least min_idle_ms milliseconds are re-assigned to consumer_name, longest-idle first
        (XNACK-released entries have a delivery time of 0, so they come first). Each claimed entry is returned as [id,
        fields, idle-time, previous-delivery-count].
        """
        curr_time = current_time()
        if consumer_name not in self.consumers:
            self.consumers[consumer_name] = StreamConsumerInfo(consumer_name)
        candidates = sorted(
            (k for k, v in self.pel.items() if curr_time - v.time_read >= min_idle_ms),
            key=lambda k: (self.pel[k].time_read, k),
        )
        if count is not None:
            candidates = candidates[:count]
        res: list[list[Any]] = []
        for key in candidates:
            if key not in self.stream:
                continue  # Entries deleted from the stream are skipped but remain in the PEL
            entry = self.pel[key]
            if entry.consumer_name != consumer_name:
                if entry.consumer_name in self.consumers:
                    self.consumers[entry.consumer_name].pending -= 1
                self.consumers[consumer_name].pending += 1
            self.pel[key] = PelEntry(consumer_name, curr_time, entry.times_delivered + 1)
            record: list[Any] = list(self.stream.format_record(key))
            record.extend([curr_time - entry.time_read, entry.times_delivered])
            res.append(record)
        return res

    def read_pel_msgs(
        self, min_idle_ms: int, start: bytes, count: int
    ) -> tuple[list[StreamEntryKey], StreamEntryKey | None]:
        """Claimable PEL entries from `start`, plus the entry XAUTOCLAIM should resume its scan at.

        The second element is None once the scan has reached the end of the PEL. XAUTOCLAIM reports that as the 0-0
        cursor, which is what ends a caller's `while cursor != "0-0"` loop.
        """
        start_key = StreamEntryKey.parse_str(start)
        curr_time = current_time()
        msgs = sorted([k for k in self.pel if (curr_time - self.pel[k].time_read >= min_idle_ms) and k >= start_key])
        return msgs[:count], msgs[count] if len(msgs) > count else None


class XStream(BaseModel):
    """Class representing stream.

    The stream contains entries with keys (timestamp, sequence) and field->value pairs.
    This implementation has them as a sorted list of tuples, the first value in the tuple is the key (timestamp,
    sequence).

    The structure of _values list is: [
       ((timestamp, sequence), [field1, value1, field2, value2, ...]),
       ((timestamp, sequence), [field1, value1, field2, value2, ...]),
    ]
    """

    _model_type = b"stream"

    def __init__(self) -> None:
        self._ids: list[StreamEntryKey] = []
        self._values_dict: dict[StreamEntryKey, list[bytes]] = {}
        self._nodes: list[_StreamNode] = []
        self._groups: dict[bytes, StreamGroup] = {}
        self._max_deleted_id = MIN_KEY
        self._entries_added = 0
        self._last_id = MIN_KEY  # the last ID XADD handed out, even if that entry is gone since
        self._idmp_duration: int = 100
        self._idmp_max_size: int = 100
        self._idmp_map: dict[bytes, dict[bytes, StreamEntryKey]] = {}  # producer_id -> idempotent_id -> entry_key
        self._iids_added: int = 0
        self._iids_duplicates: int = 0

    def set_idmp_duration(self, duration: int) -> None:
        if duration is not None and 1 <= duration <= 86400:
            self._idmp_duration = duration

    def set_idmp_max_size(self, max_size: int) -> None:
        if max_size is not None and 1 <= max_size <= 10000:
            self._idmp_max_size = max_size

    def group_get(self, group_name: bytes) -> StreamGroup | None:
        return self._groups.get(group_name, None)

    def group_add(self, name: bytes, last_delivered_key: StreamEntryKey, entries_read: int | None) -> None:
        """Add a consumer group that reads the entries after `last_delivered_key`.

        :param name: Group name
        :param last_delivered_key: The group reads the entries after this one.
        :param entries_read: How many entries the group has read, None if unknown.
        """
        self._groups[name] = StreamGroup(self, name, last_delivered_key, entries_read)

    def group_delete(self, group_name: bytes) -> int:
        if group_name in self._groups:
            del self._groups[group_name]
            return 1
        return 0

    def groups_info(self, trim_aware_lag: bool) -> list[dict[bytes, Any]]:
        return [group.group_info(trim_aware_lag) for group in self._groups.values()]

    def stream_info(self, full: bool, trim_aware_lag: bool) -> list[Any]:
        iids_tracked = sum([len(v) for v in self._idmp_map.values()])

        res: dict[bytes, Any] = {
            b"length": len(self._ids),
            b"groups": len(self._groups),
            b"first-entry": self.format_record(self._ids[0]) if len(self._ids) > 0 else None,
            b"last-generated-id": self._last_id.encode(),
            b"radix-tree-keys": len(self._nodes),
            b"radix-tree-nodes": len(self._ids),
            b"last-entry": self.format_record(self._ids[-1]) if len(self._ids) > 0 else None,
            b"max-deleted-entry-id": self._max_deleted_id.encode(),
            b"entries-added": self._entries_added,
            b"recorded-first-entry-id": self._ids[0].encode() if len(self._ids) > 0 else b"0-0",
            b"idmp-duration": self._idmp_duration,
            b"idmp-maxsize": self._idmp_max_size,
            b"pids-tracked": len(self._idmp_map),
            b"iids-tracked": iids_tracked,
            b"iids-added": self._iids_added,
            b"iids-duplicates": self._iids_duplicates,
        }
        if full:
            res[b"entries"] = [self.format_record(i) for i in self._ids]
            res[b"groups"] = self.groups_info(trim_aware_lag)
        return list(itertools.chain(*res.items()))

    @property
    def first_id(self) -> StreamEntryKey:
        return self._ids[0] if self._ids else MIN_KEY

    @property
    def last_id(self) -> StreamEntryKey:
        return self._last_id

    @property
    def max_deleted_id(self) -> StreamEntryKey:
        return self._max_deleted_id

    @property
    def entries_added(self) -> int:
        return self._entries_added

    def has_tombstones_from(self, start: StreamEntryKey) -> bool:
        """Whether an entry at or after `start` has been deleted (not trimmed) from a stream that is not empty."""
        return bool(self._ids) and self._max_deleted_id != MIN_KEY and start <= self._max_deleted_id

    def estimate_entries_read(self, key: StreamEntryKey) -> int | None:
        """How many entries the stream had taken in up to and including `key`, or None when that cannot be known.

        Deletions leave holes that make the count unknowable, except before the first entry, since everything
        before it is gone anyway.
        """
        if not self._entries_added:
            return 0
        if not self._ids and key <= self._last_id:
            return self._entries_added
        if key != MIN_KEY and key < self._max_deleted_id:
            return None
        if key == self._last_id:
            return self._entries_added
        if key > self._last_id:
            return None
        first = self.first_id
        if self._max_deleted_id == MIN_KEY or self._max_deleted_id < first:
            if key < first:
                return self._entries_added - len(self._ids)
            if key == first:
                return self._entries_added - len(self._ids) + 1
        return None

    def _node_of(self, key: StreamEntryKey) -> int:
        """Index of the node holding `key`: the last one whose master entry is not after it."""
        return bisect.bisect_right([node.master_id for node in self._nodes], key) - 1

    def _node_span(self, node_index: int) -> tuple[int, int]:
        """The slice of `_ids` holding the live entries of a node."""
        start = bisect.bisect_left(self._ids, self._nodes[node_index].master_id)
        if node_index + 1 == len(self._nodes):
            return start, len(self._ids)
        return start, bisect.bisect_left(self._ids, self._nodes[node_index + 1].master_id, start)

    def _delete_at(self, ind: int) -> None:
        """Delete the entry at `ind` as XDEL does: flagged deleted in its node, which goes once nothing live is left."""
        key = self._ids.pop(ind)
        del self._values_dict[key]
        self._max_deleted_id = max(key, self._max_deleted_id)
        node_index = self._node_of(key)
        node = self._nodes[node_index]
        if node.live == 1:
            del self._nodes[node_index]
        else:
            node.set_counts(node.live - 1, node.deleted + 1)

    def delete(self, lst: list[AnyStr]) -> int:
        """Delete items from stream

        :param lst: List of IDs to delete, in the form of `timestamp-sequence`.
        :returns: Number of items deleted
        """
        res = 0
        for item in lst:
            ind, found = self.find_index_key_as_str(item)
            if found:
                self._delete_at(ind)
                res += 1
        return res

    def delete_ex(self, ids: list[bytes], mode: bytes) -> list[int]:
        """Extended delete with consumer-group reference control.

        mode: b'KEEPREF' preserve PEL refs, b'DELREF' remove all PEL refs,
              b'ACKED' only delete if not in any group's PEL
        Returns per-ID: -1 not found, 1 deleted, 2 skipped (ACKED mode)
        """
        results = []
        for id_bytes in ids:
            ind, found = self.find_index_key_as_str(id_bytes)
            if not found:
                results.append(-1)
                continue

            entry_key = self._ids[ind]

            if mode == b"ACKED" and self._is_referenced(entry_key):
                results.append(2)
                continue

            self._delete_at(ind)

            if mode == b"DELREF":
                self._drop_references(entry_key)

            results.append(1)

        return results

    def _is_referenced(self, entry_key: StreamEntryKey) -> bool:
        """Whether some consumer group still references the entry, which keeps ACKED from deleting it.

        A group references an entry it has not delivered yet, as well as one still in its PEL.
        """
        return any(entry_key > g.last_delivered_key or entry_key in g.pel for g in self._groups.values())

    def _drop_references(self, entry_key: StreamEntryKey) -> None:
        """Remove the entry from every consumer group's PEL, as DELREF does."""
        for g in self._groups.values():
            if entry_key in g.pel:
                cn = g.pel[entry_key].consumer_name
                if cn and cn in g.consumers:
                    g.consumers[cn].pending -= 1
                del g.pel[entry_key]

    def ackdel(self, group: StreamGroup, ids: list[bytes], mode: bytes) -> list[int]:
        """Atomically acknowledge in group and conditionally delete.

        Returns per-ID: -1 not found, 1 acked+deleted, 2 acked but not deleted (ACKED mode)
        """
        results = []
        for id_bytes in ids:
            ind, found = self.find_index_key_as_str(id_bytes)
            if not found:
                results.append(-1)
                continue

            entry_key = self._ids[ind]
            if entry_key not in group.pel:
                results.append(-1)
                continue
            group.ack((id_bytes,))

            if mode == b"ACKED" and self._is_referenced(entry_key):
                results.append(2)
                continue

            self._delete_at(ind)

            if mode == b"DELREF":
                self._drop_references(entry_key)

            results.append(1)

        return results

    def record_idmp(self, pid: bytes, iid: bytes, stream_id: bytes) -> None:
        """Record pid/iid -> stream_id mapping for XIDMPRECORD.

        Raises SimpleError if the pid/iid pair already maps to a different stream ID, or if stream_id does not exist in
        the stream.
        """
        entry_key = StreamEntryKey.parse_str(stream_id)
        if entry_key not in self._values_dict:
            raise SimpleError("ERR The specified stream ID was deleted or doesn't exist")

        if pid in self._idmp_map and iid in self._idmp_map[pid]:
            existing = self._idmp_map[pid][iid]
            if existing != entry_key:
                raise SimpleError("ERR The specified IDMP producer-id/idempotent-id pair maps to a different stream ID")
            return  # idempotent – already recorded

        if pid not in self._idmp_map:
            self._idmp_map[pid] = {}
        self._idmp_map[pid][iid] = entry_key

    def idmp_lookup(self, producer_id: bytes, idempotent_id: bytes) -> StreamEntryKey | None:
        """The entry a producer already added under an idempotent ID, counted as a duplicate, or None if new."""
        existing = self._idmp_map.get(producer_id, {}).get(idempotent_id)
        if existing is not None:
            self._iids_duplicates += 1
        return existing

    def idmp_record(self, producer_id: bytes, idempotent_id: bytes, key: StreamEntryKey) -> None:
        self._idmp_map.setdefault(producer_id, {})[idempotent_id] = key
        self._iids_added += 1

    def next_id(self, requested: StreamEntryKey | None, seq_given: bool = True) -> StreamEntryKey | None:
        """The ID XADD gives a new entry, or None if it would not come after the last ID the stream handed out.

        :param requested: The ID asked for, None for `*` (the current time).
        :param seq_given: False for `ms-*`, which continues the last ID's sequence within the same millisecond.
        """
        last = self._last_id
        if requested is None:
            now = int(1000 * time.time())
            if now > last.ts:
                return StreamEntryKey(now, 0)
            if last.seq < MAX_ID_PART:
                return StreamEntryKey(last.ts, last.seq + 1)
            return StreamEntryKey(last.ts + 1, 0) if last.ts < MAX_ID_PART else None
        if not seq_given and requested.ts == last.ts:
            if last.seq == MAX_ID_PART:
                return None
            requested = StreamEntryKey(last.ts, last.seq + 1)
        return requested if requested > last else None

    def add(
        self, fields: Sequence[bytes], key: StreamEntryKey, node_max_entries: int = 100, node_max_bytes: int = 4096
    ) -> None:
        """Append an entry whose ID comes from `next_id`.

        :param fields: [field1, value1, field2, value2, ...]
        :param key: The entry's ID.
        :param node_max_entries: `stream-node-max-entries`: how many entries, live or deleted, a node holds (0 for no
            limit).
        :param node_max_bytes: `stream-node-max-bytes`: the size a node takes no more entries at (0 for no limit).
        """
        names, values = list(fields[0::2]), fields[1::2]
        node = self._nodes[-1] if self._nodes else None
        if node is not None:
            max_bytes = node_max_bytes if 0 < node_max_bytes <= _LP_MAX_SIZE else _LP_MAX_SIZE
            if node.lp_bytes + sum(map(len, fields)) >= max_bytes or (
                node_max_entries and node.live + node.deleted >= node_max_entries
            ):
                node = None
        if node is None:
            # The master entry: live and deleted counts, the field names and their count, and a terminating 0.
            header = _lp_int_size(0) * 3 + _lp_int_size(len(names)) + sum(map(_lp_str_size, names))
            node = _StreamNode(key, names, key, 0, 0, _LP_EMPTY_SIZE + header)
            self._nodes.append(node)
        # An entry is stored as: flags, its ID relative to the node's master entry, the field names and their count
        # (only when they differ from the master entry's), the values, and how many elements all that took.
        same_fields = names == node.master_fields
        entry_size = (
            _lp_int_size(_ENTRY_SAMEFIELDS if same_fields else 0)
            + _lp_int_size(key.ts - node.master_id.ts)
            + _lp_int_size(key.seq - node.master_id.seq)
            + sum(map(_lp_str_size, values))
            + _lp_int_size(len(names) + 3 if same_fields else 2 * len(names) + 4)
        )
        if not same_fields:
            entry_size += _lp_int_size(len(names)) + sum(map(_lp_str_size, names))
        node.lp_bytes += entry_size
        node.set_counts(node.live + 1, node.deleted)
        node.last_id = key

        self._ids.append(key)
        self._values_dict[key] = list(fields)
        self._entries_added += 1
        self._last_id = key

    def __bool__(self) -> bool:
        return True

    def __len__(self) -> int:
        return len(self._ids)

    def __iter__(self) -> Generator[list[bytes | list[bytes]], Any, None]:
        def gen() -> Generator[list[bytes | list[bytes]], Any, None]:
            for k in self._ids:
                yield self.format_record(k)

        return gen()

    def __getitem__(self, key: bytes) -> StreamEntryKey | list[bytes]:
        return self._values_dict[StreamEntryKey.parse_str(key)]

    def __contains__(self, key: StreamEntryKey) -> bool:
        return key in self._values_dict

    def find_index(self, entry_key: StreamEntryKey, from_left: bool = True) -> tuple[int, bool]:
        """Find the closest index to entry_key_str in the stream
        :param entry_key: Key for the entry.
        :param from_left: If not found exact match, return index of last smaller element
        :returns: A tuple
            (index of entry with the closest (from the left) key to entry_key_str,
             whether the entry key is equal)
        """
        if len(self._ids) == 0:
            return 0, False
        if from_left:
            ind = bisect.bisect_left(self._ids, entry_key)
            check_idx = ind
        else:
            ind = bisect.bisect_right(self._ids, entry_key)
            check_idx = ind - 1
        return ind, (check_idx < len(self._ids) and self._ids[check_idx] == entry_key)

    def find_index_key_as_str(self, entry_key_str: AnyStr) -> tuple[int, bool]:
        """Find the closest index to entry_key_str in the stream
        :param entry_key_str: key for the entry, formatted as 'timestamp-sequence.'
        :returns: A tuple
            (index of entry with the closest (from the left) key to entry_key_str,
             whether the entry key is equal)
        """
        if entry_key_str == b"$":
            return max(len(self._ids) - 1, 0), True
        ts_seq = StreamEntryKey.parse_str(entry_key_str)
        return self.find_index(ts_seq)

    def trim(
        self,
        maxlen: int | None = None,
        minid: StreamEntryKey | None = None,
        approx: bool = False,
        limit: int = 0,
        ref_policy: bytes = b"KEEPREF",
    ) -> int:
        """Trim the stream from its head, a node at a time, as redis' streamTrim does.

        :param maxlen: Trim the stream down to this many entries.
        :param minid: Or trim the entries before this ID.
        :param approx: `~`: KEEPREF then trims whole nodes only, and stops at the first one it cannot drop entirely.
        :param limit: Stop before a node that would take the number of trimmed entries past this (0 for no limit).
        :param ref_policy: What happens to consumer group references to trimmed entries: b"KEEPREF" leaves them in
            the PELs, b"DELREF" removes them, and b"ACKED" trims only entries no group references - skipping, not
            stopping at, the ones some group does.
        :returns: The number of entries trimmed.
        """
        trimmed = 0
        node_index = 0
        while node_index < len(self._nodes):
            if maxlen is not None and len(self._ids) <= maxlen:
                break
            node = self._nodes[node_index]
            if limit and trimmed + node.live > limit:
                break
            start, end = self._node_span(node_index)
            if maxlen is not None:
                whole_node = len(self._ids) - node.live >= maxlen
            else:
                whole_node = minid is not None and node.last_id < minid
            if whole_node and ref_policy == b"KEEPREF":
                for key in self._ids[start:end]:
                    del self._values_dict[key]
                del self._ids[start:end]
                del self._nodes[node_index]
                trimmed += node.live
                continue
            if approx and ref_policy == b"KEEPREF":
                break

            removed: list[StreamEntryKey] = []
            for key in self._ids[start:end]:
                if maxlen is not None and len(self._ids) - len(removed) <= maxlen:
                    break
                if minid is not None and key >= minid:
                    break
                if ref_policy == b"ACKED" and self._is_referenced(key):
                    continue
                if ref_policy == b"DELREF":
                    self._drop_references(key)
                removed.append(key)
            gone = set(removed)
            self._ids[start:end] = [key for key in self._ids[start:end] if key not in gone]
            for key in removed:
                del self._values_dict[key]
            trimmed += len(removed)
            if whole_node and len(removed) == node.live:
                del self._nodes[node_index]
                continue
            node.set_counts(node.live - len(removed), node.deleted + len(removed))
            if not whole_node:
                break
            node_index += 1
        return trimmed

    def irange(self, start: StreamRangeTest, stop: StreamRangeTest, reverse: bool = False) -> list[Any]:
        """Returns a range of the stream values from start to stop.

        :param start: Start key
        :param stop: Stop key
        :param reverse: Should the range be in reverse order?
        :returns: The range between start and stop
        """

        def _find_index(elem: StreamRangeTest, from_left: bool = True) -> int:
            if isinstance(elem.value, BeforeAny):
                return 0
            if isinstance(elem.value, AfterAny):
                return len(self._ids)
            ind, found = self.find_index(elem.value, from_left)
            if found and elem.exclusive:
                ind += 1 if from_left else -1
            return ind

        start_ind = _find_index(start)
        stop_ind = _find_index(stop, from_left=False)
        matches = [self.format_record(self._ids[x]) for x in range(start_ind, stop_ind)]
        if reverse:
            return list(reversed(matches))
        return matches

    def last_item_key(self) -> bytes:
        return self._ids[-1].encode() if len(self._ids) > 0 else b"0-0"

    def stream_read(self, start_key: StreamEntryKey, count: int | None) -> list[StreamEntryKey]:
        start_ind, found = self.find_index(start_key)
        if found:
            start_ind += 1
        if start_ind >= len(self):
            return []
        end_ind = len(self) if count is None or start_ind + count >= len(self) else start_ind + count
        return self._ids[start_ind:end_ind]

    def format_record(self, key: StreamEntryKey) -> list[bytes | list[bytes]]:
        # results: Dict[bytes, bytes] = dict(zip(*[iter(self._values_dict[key])] * 2))
        results = self._values_dict[key]
        return [key.encode(), results]
