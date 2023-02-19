import bisect
import time
from typing import List, Union, Tuple, Optional

from fakeredis._commands import StreamRangeTest


class XStream:
    def __init__(self):
        # Values:
        # [
        #    ((timestamp,sequence), [field1, value1, field2, value2, ...])
        #    ((timestamp,sequence), [field1, value1, field2, value2, ...])
        # ]
        self._values = list()

    def add(self, fields: List, id_str: str = '*') -> Union[None, bytes]:
        assert len(fields) % 2 == 0
        if isinstance(id_str, bytes):
            id_str = id_str.decode()

        if id_str is None or id_str == '*':
            ts, seq = int(time.time() + 1), 0
            if (len(self._values) > 0
                    and self._values[-1][0][0] == ts
                    and self._values[-1][0][1] >= seq):
                seq = self._values[-1][0][1] + 1
            ts_seq = (ts, seq)
        elif id_str[-1] == '*':
            split = id_str.split('-')
            if len(split) != 2:
                return None
            ts, seq = int(split[0]), split[1]
            if len(self._values) > 0 and ts == self._values[-1][0][0]:
                seq = self._values[-1][0][1] + 1
            else:
                seq = 0
            ts_seq = (ts, seq)
        else:
            ts_seq = StreamRangeTest.parse_id(id_str)

        if len(self._values) > 0 and self._values[-1][0] > ts_seq:
            return None
        new_val = (ts_seq, list(fields))
        self._values.append(new_val)
        return f'{ts_seq[0]}-{ts_seq[1]}'.encode()

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        def gen():
            for record in self._values:
                yield self._format_record(record)

        return gen()

    def find_index(self, id_str: str) -> Tuple[int, bool]:
        ts_seq = StreamRangeTest.parse_id(id_str)
        ind = bisect.bisect_left(list(map(lambda x: x[0], self._values)), ts_seq)
        return ind, self._values[ind][0] == ts_seq

    @staticmethod
    def _format_record(record):
        return [f'{record[0][0]}-{record[0][1]}'.encode(), list(record[1:])]

    def trim(self,
             maxlen: Optional[int] = None,
             minid: Optional[str] = None,
             limit: Optional[int] = None) -> int:
        if maxlen is not None and minid is not None:
            raise
        start_ind = None
        if maxlen is not None:
            start_ind = len(self._values) - maxlen
        elif minid is not None:
            ind, exact = self.find_index(minid)
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
        def match(record):
            result = stop > record[0] > start
            result = result or (not exclusive[0] and record[0] == start)
            result = result or (not exclusive[1] and record[0] == stop)
            return result

        matches = map(self._format_record, filter(match, self._values))
        if reverse:
            return list(reversed(tuple(matches)))
        return list(matches)
