import bisect
import time
from collections import namedtuple
from typing import List, Union, Tuple, Optional

from fakeredis._commands import BeforeAny, AfterAny

StreamEntryKey = namedtuple('StreamEntryKey', ['ts', 'seq'])
StreamEntry = namedtuple('StreamEntry', ['key', 'fields'])


class StreamRangeTest:
    """Argument converter for sorted set LEX endpoints."""

    def __init__(self, value: Union[StreamEntryKey, BeforeAny, AfterAny], exclusive: bool):
        self.value = value
        self.exclusive = exclusive

    @staticmethod
    def parse_id(id_str: Union[bytes, str]) -> StreamEntryKey:
        if isinstance(id_str, bytes):
            id_str = id_str.decode()
        try:
            timestamp, sequence = (int(x) for x in id_str.split('-'))
        except ValueError:
            return -1, -1
        return StreamEntryKey(timestamp, sequence)

    @classmethod
    def decode(cls, value: bytes, exclusive=False):
        if value == b'-':
            return cls(BeforeAny(), True)
        elif value == b'+':
            return cls(AfterAny(), True)
        elif value[:1] == b'(':
            return cls(cls.parse_id(value[1:]), True)
        return cls(cls.parse_id(value), exclusive)


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

    def delete(self, lst: List[str]) -> int:
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

    def add(self, fields: List, id_str: str = '*') -> Union[None, bytes]:
        """Add entry to a stream.

        If the id_str can not be added (because its timestamp is before the last entry, etc.),
        nothing is added.

        :param fields: list of fields to add, must [key1, value1, key2, value2, ... ]
        :param id_str:
            key for the entry, formatted as 'timestamp-sequence'
            If id_str is '*', the timestamp will be calculated as current time and the sequence based
            on the last entry key of the stream.
            If id_str is 'ts-*', and the timestamp is greater or equal than the last entry timestamp,
            then the sequence will be calculated accordingly.
        :returns:
            The key of the added entry.
            None if nothing was added.
        :raises AssertionError: if len(fields) is not even.
        """
        assert len(fields) % 2 == 0
        if isinstance(id_str, bytes):
            id_str = id_str.decode()

        if id_str is None or id_str == '*':
            ts, seq = int(1000 * time.time()), 0
            if (len(self._values) > 0
                    and self._values[-1].key.ts == ts
                    and self._values[-1].key.seq >= seq):
                seq = self._values[-1][0].seq + 1
            ts_seq = StreamEntryKey(ts, seq)
        elif id_str[-1] == '*':  # id_str has `timestamp-*` structure
            split = id_str.split('-')
            if len(split) != 2:
                return None
            ts, seq = int(split[0]), split[1]
            if len(self._values) > 0 and ts == self._values[-1].key.ts:
                seq = self._values[-1].key.seq + 1
            else:
                seq = 0
            ts_seq = StreamEntryKey(ts, seq)
        else:
            ts_seq = StreamRangeTest.parse_id(id_str)

        if len(self._values) > 0 and self._values[-1][0] > ts_seq:
            return None
        entry = StreamEntry(ts_seq, list(fields))
        self._values.append(entry)
        return XStream._encode_id(entry)

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        def gen():
            for record in self._values:
                yield self._format_record(record)

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
        ts_seq = StreamRangeTest.parse_id(entry_key_str)
        ind = bisect.bisect_left(list(map(lambda x: x.key, self._values)), ts_seq)
        return ind, self._values[ind].key == ts_seq

    @staticmethod
    def _encode_id(entry: StreamEntry):
        return f'{entry.key.ts}-{entry.key.seq}'.encode()

    @staticmethod
    def _format_record(entry: StreamEntry):
        results = list(entry.fields)
        return [XStream._encode_id(entry), results]

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

        matches = map(self._format_record, filter(match, self._values))
        if reverse:
            return list(reversed(tuple(matches)))
        return list(matches)

    def last_item_key(self):
        XStream._encode_id(self._values[-1])
