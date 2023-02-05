import bisect
import time
from typing import List, Union, Tuple

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
        if id_str != b'*':
            ts_seq = StreamRangeTest.parse_id(id_str)
        else:
            ts, seq = int(time.time() + 1), 1
            if (len(self._values) > 0
                    and self._values[-1][0][0] == ts
                    and self._values[-1][0][1] >= seq):
                seq = self._values[-1][0][1] + 1
            ts_seq = (ts, seq)

        if len(self._values) > 0 and self._values[-1][0] > ts_seq:
            return None
        new_val = (ts_seq, list(fields))
        self._values.append(new_val)
        return f'{ts_seq[0]}-{ts_seq[1]}'.encode()

    def __len__(self):
        return len(self._values)

    def __iter__(self):
        def gen():
            for val in self._values:
                ts_seq = val[0]
                yield f"{ts_seq[0]}-{ts_seq[1]}"

        return gen()

    def find_index(self, id_str: str):
        ts_seq = StreamRangeTest.parse_id(id_str)
        return bisect.bisect_left(self._values, ts_seq, key=lambda x: x[0])

    @staticmethod
    def _format_record(record):
        return [f'{record[0][0]}-{record[0][1]}'.encode(), list(record[1:])]

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
            matches = reversed(list(matches))
        return list(matches)


if __name__ == '__main__':
    stream = XStream()
    stream.add([0, 0, 1, 1, 2, 2, 3, 3], '0-1')
    stream.add([1, 1, 2, 2, 3, 3, 4, 4], '1-2')
    stream.add([2, 2, 3, 3, 4, 4], '1-3')
    stream.add([3, 3, 4, 4], '2-1')
    stream.add([3, 3, 4, 4], '2-2')
    stream.add([3, 3, 4, 4], '3-1')
    for i in stream:
        print(i)
    assert stream.find_index('1-2') == 1
    assert stream.find_index('0-1') == 0
    assert stream.find_index('2-1') == 3
    assert stream.find_index('1-4') == 3
    lst = stream.irange('0-2', '3-0')
    for i in lst:
        print(i)
