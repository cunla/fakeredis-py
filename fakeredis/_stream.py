import bisect
import time
from typing import List, Union, Tuple, Optional, NamedTuple

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

    def delete(self, lst: List[Union[str, bytes]]) -> int:
        """Delete items from stream

        :param lst: list of IDs to delete, in the form of `timestamp-sequence`.
        :returns: Number of items deleted
        """
        res = 0
        for item in lst:
            ind, found = self.find_index(item)
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

    def find_index(self, entry_key_str: str) -> Tuple[int, bool]:
        """Find the closest index to entry_key_str in the stream
        :param entry_key_str: key for the entry, formatted as 'timestamp-sequence'.
        :returns: A tuple of
            ( index of entry with the closest (from the left) key to entry_key_str,
              Whether the entry key is equal )
        """
        if len(self._values) == 0:
            return 0, False
        ts_seq = StreamEntryKey.parse_str(entry_key_str)
        ind = bisect.bisect_left(list(map(lambda x: x.key, self._values)), ts_seq)
        return ind, self._values[ind].key == ts_seq

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
            ind, exact = self.find_index(start_entry_key)
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
        return self._values[-1].key.encode()
