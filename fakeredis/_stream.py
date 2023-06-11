import bisect
import time
from dataclasses import dataclass
from typing import List, Union, Tuple, Optional, NamedTuple, Dict

from fakeredis._commands import BeforeAny, AfterAny


class StreamEntryKey(NamedTuple):
    ts: int
    seq: int

    def encode(self) -> bytes:
        return f'{self.ts}-{self.seq}'.encode()

    @staticmethod
    def parse_str(entry_key_str: Union[bytes, str]) -> 'StreamEntryKey':
        if isinstance(entry_key_str, bytes):
            entry_key_str = entry_key_str.decode()
        s = entry_key_str.split('-')
        (timestamp, sequence) = (int(s[0]), 0) if len(s) == 1 else (int(s[0]), int(s[1]))
        return StreamEntryKey(timestamp, sequence)


class StreamEntry(NamedTuple):
    key: StreamEntryKey
    fields: List

    def format_record(self):
        results = list(self.fields)
        return [self.key.encode(), results]


current_time = lambda: int(time.time() * 1000)


@dataclass
class StreamConsumerInfo(object):
    name: bytes
    pending: int = 0
    last_attempt: int = current_time()
    last_success: int = current_time()

    def info(self) -> List[bytes]:
        curr_time = current_time()
        return [
            b'name', self.name,
            b'pending', self.pending,
            b'idle', curr_time - self.last_attempt,
            b'inactive', curr_time - self.last_success,
        ]


class StreamGroup(object):
    def __init__(self, stream: 'XStream', name: bytes, start_index: int, entries_read: int = None):
        self.stream = stream
        self.name = name
        self.start_index = start_index
        self.entries_read = entries_read
        # consumer_name -> #pending_messages
        self.consumers: Dict[bytes, StreamConsumerInfo] = dict()
        self.last_delivered_index = start_index
        self.last_ack_index = start_index

    def set_id(self, last_delivered_str: bytes, entries_read: Union[int, None]) -> None:
        """Set last_delivered_id for group
        """
        self.start_index, _ = self.stream.find_index_key_as_str(last_delivered_str)
        self.entries_read = entries_read

    def add_consumer(self, consumer_name: bytes) -> int:
        if consumer_name in self.consumers:
            return 0
        self.consumers[consumer_name] = StreamConsumerInfo()
        return 1

    def del_consumer(self, consumer_name: bytes) -> int:
        if consumer_name not in self.consumers:
            return 0
        res = self.consumers[consumer_name].pending
        del self.consumers[consumer_name]
        return res

    def consumers_info(self):
        return [self.consumers[k].info() for k in self.consumers]


class StreamRangeTest:
    """Argument converter for sorted set LEX endpoints."""

    def __init__(self, value: Union[StreamEntryKey, BeforeAny, AfterAny], exclusive: bool):
        self.value = value
        self.exclusive = exclusive

    @staticmethod
    def valid_key(entry_key: Union[bytes, str]) -> bool:
        try:
            StreamEntryKey.parse_str(entry_key)
            return True
        except ValueError:
            return False

    @classmethod
    def decode(cls, value: bytes, exclusive=False):
        if value == b'-':
            return cls(BeforeAny(), True)
        elif value == b'+':
            return cls(AfterAny(), True)
        elif value[:1] == b'(':
            return cls(StreamEntryKey.parse_str(value[1:]), True)
        return cls(StreamEntryKey.parse_str(value), exclusive)


class XStream:
    """Class representing stream.

    The stream contains entries with keys (timestamp, sequence) and field->value pairs.
    This implementation has them as a sorted list of tuples, the first value in the tuple
    is the key (timestamp, sequence).

    Structure of _values list:
    [
       ((timestamp,sequence), [field1, value1, field2, value2, ...])
       ((timestamp,sequence), [field1, value1, field2, value2, ...])
    ]
    """

    def __init__(self):
        self._values: List[StreamEntry] = list()
        self._groups: Dict[bytes, StreamGroup] = dict()

    def group_get(self, group_name: bytes) -> StreamGroup:
        return self._groups.get(group_name, None)

    def group_add(self, name: bytes, start_key_str: bytes, entries_read: Union[int, None]) -> None:
        """Add a group listening to stream

        :param name: group name
        :param start_key_str: start_key in `timestamp-sequence` format, or $ listen from last.
        :param entries_read: number of entries read.
        """
        start_index, found = self.find_index_key_as_str(start_key_str)
        start_index -= (0 if found else -1)
        self._groups[name] = StreamGroup(self, name, start_index, entries_read)

    def group_delete(self, group_name: bytes) -> int:
        if group_name in self._groups:
            del self._groups[group_name]
            return 1
        return 0

    def groups_info(self):
        res = []
        for group in self._groups.values():
            last_delivered_id = self._values[min(group.last_delivered_index, len(self._values) - 1)].key.encode()
            group_res = [
                b'name', group.name,
                b'consumers', len(group.consumers),
                b'pending', group.last_delivered_index - group.last_ack_index,
                b'last-delivered-id', last_delivered_id,
                b'entries-read', group.entries_read,
                b'lag', len(self._values) - 1 - group.last_delivered_index,
            ]
            res.append(group_res)
        return res

    def delete(self, lst: List[Union[str, bytes]]) -> int:
        """Delete items from stream

        :param lst: list of IDs to delete, in the form of `timestamp-sequence`.
        :returns: Number of items deleted
        """
        res = 0
        for item in lst:
            ind, found = self.find_index_key_as_str(item)
            if found:
                del self._values[ind]
                res += 1
        return res

    def add(self, fields: List, entry_key: str = '*') -> Union[None, bytes]:
        """Add entry to a stream.

        If the entry_key can not be added (because its timestamp is before the last entry, etc.),
        nothing is added.

        :param fields: list of fields to add, must [key1, value1, key2, value2, ... ]
        :param entry_key:
            key for the entry, formatted as 'timestamp-sequence'
            If entry_key is '*', the timestamp will be calculated as current time and the sequence based
            on the last entry key of the stream.
            If entry_key is 'ts-*', and the timestamp is greater or equal than the last entry timestamp,
            then the sequence will be calculated accordingly.
        :returns:
            The key of the added entry.
            None if nothing was added.
        :raises AssertionError: if len(fields) is not even.
        """
        assert len(fields) % 2 == 0
        if isinstance(entry_key, bytes):
            entry_key = entry_key.decode()

        if entry_key is None or entry_key == '*':
            ts, seq = int(1000 * time.time()), 0
            if (len(self._values) > 0
                    and self._values[-1].key.ts == ts
                    and self._values[-1].key.seq >= seq):
                seq = self._values[-1][0].seq + 1
            ts_seq = StreamEntryKey(ts, seq)
        elif entry_key[-1] == '*':  # entry_key has `timestamp-*` structure
            split = entry_key.split('-')
            if len(split) != 2:
                return None
            ts, seq = int(split[0]), split[1]
            if len(self._values) > 0 and ts == self._values[-1].key.ts:
                seq = self._values[-1].key.seq + 1
            else:
                seq = 0
            ts_seq = StreamEntryKey(ts, seq)
        else:
            ts_seq = StreamEntryKey.parse_str(entry_key)

        if len(self._values) > 0 and self._values[-1].key > ts_seq:
            return None
        entry = StreamEntry(ts_seq, list(fields))
        self._values.append(entry)
        return entry.key.encode()

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        def gen():
            for record in self._values:
                yield record.format_record()

        return gen()

    def find_index(self, entry_key: StreamEntryKey) -> Tuple[int, bool]:
        """Find the closest index to entry_key_str in the stream
        :param entry_key: key for the entry.
        :returns: A tuple of
            ( index of entry with the closest (from the left) key to entry_key_str,
              Whether the entry key is equal )
        """
        if len(self._values) == 0:
            return 0, False
        ind = bisect.bisect_left(list(map(lambda x: x.key, self._values)), entry_key)
        return ind, self._values[ind].key == entry_key

    def find_index_key_as_str(self, entry_key_str: Union[str, bytes]) -> Tuple[int, bool]:
        """Find the closest index to entry_key_str in the stream
        :param entry_key_str: key for the entry, formatted as 'timestamp-sequence'.
        :returns: A tuple of
            ( index of entry with the closest (from the left) key to entry_key_str,
              Whether the entry key is equal )
        """
        if entry_key_str == b'$':
            return len(self._values) - 1, True
        ts_seq = StreamEntryKey.parse_str(entry_key_str)
        return self.find_index(ts_seq)

    def trim(self,
             max_length: Optional[int] = None,
             start_entry_key: Optional[str] = None,
             limit: Optional[int] = None) -> int:
        """Trim a stream

        :param max_length: max length of resulting stream after trimming (number of last values to keep)
        :param start_entry_key: min entry-key to keep, can not be given together with max_length.
        :param limit: number of entries to keep from minid.
        :returns: The resulting stream after trimming.
        :raises ValueError: When both max_length and start_entry_key are passed.
        """
        if max_length is not None and start_entry_key is not None:
            raise ValueError('Can not use both max_length and start_entry_key')
        start_ind = None
        if max_length is not None:
            start_ind = len(self._values) - max_length
        elif start_entry_key is not None:
            ind, exact = self.find_index_key_as_str(start_entry_key)
            start_ind = ind
        res = max(start_ind, 0)
        if limit is not None:
            res = min(start_ind, limit)
        self._values = self._values[res:]
        return res

    def irange(self,
               start, stop,
               exclusive: Tuple[bool, bool] = (True, True),
               reverse=False):
        """Returns a range of the stream from start to stop.

        :param start: start key
        :param stop: stop key
        :param exclusive: whether start/stop should be excluded
        :param reverse: Should the range be in reverse order?
        :returns: the range between start and stop
        """

        def match(record: StreamEntry):
            result = stop > record.key > start  # Between
            result = result or (not exclusive[0] and record.key == start)  # equal to start and inclusive
            result = result or (not exclusive[1] and record.key == stop)  # equal to stop and inclusive
            return result

        matches = map(lambda x: x.format_record(), filter(match, self._values))
        if reverse:
            return list(reversed(tuple(matches)))
        return list(matches)

    def last_item_key(self) -> bytes:
        return self._values[-1].key.encode() if len(self._values) > 0 else '0-0'.encode()
