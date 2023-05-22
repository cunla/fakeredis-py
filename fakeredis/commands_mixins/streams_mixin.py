import functools
from typing import List

import fakeredis._msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import Key, command, CommandItem
from fakeredis._helpers import SimpleError, casematch
from fakeredis._stream import XStream, StreamRangeTest


class StreamsCommandsMixin:
    @command(name="XADD", fixed=(Key(),), repeat=(bytes,), )
    def xadd(self, key, *args):
        (nomkstream, limit, maxlen, minid), left_args = extract_args(
            args, ('nomkstream', '+limit', '~+maxlen', '~minid'), error_on_unexpected=False)
        if nomkstream and key.value is None:
            return None
        id_str = left_args[0]
        elements = left_args[1:]
        if not elements or len(elements) % 2 != 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format('XADD'))
        stream = key.value or XStream()
        if self.version < 7 and id_str != b'*' and not StreamRangeTest.valid_key(id_str):
            raise SimpleError(msgs.XADD_INVALID_ID)
        id_str = stream.add(elements, id_str=id_str)
        if id_str is None:
            if not StreamRangeTest.valid_key(left_args[0]):
                raise SimpleError(msgs.XADD_INVALID_ID)
            raise SimpleError(msgs.XADD_ID_LOWER_THAN_LAST)
        if maxlen is not None or minid is not None:
            stream.trim(max_length=maxlen, start_entry_key=minid, limit=limit)
        key.update(stream)
        return id_str

    @command(name='XTRIM', fixed=(Key(XStream),), repeat=(bytes,), )
    def xtrim(self, key, *args):
        (limit, maxlen, minid), _ = extract_args(
            args, ('+limit', '~+maxlen', '~minid'))
        if maxlen is not None and minid is not None:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if maxlen is None and minid is None:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        stream = key.value or XStream()
        res = stream.trim(max_length=maxlen, start_entry_key=minid, limit=limit)
        key.update(stream)
        return res

    @command(name="XLEN", fixed=(Key(XStream),))
    def xlen(self, key):
        return len(key.value)

    def _xrange(self, key, _min, _max, reverse, count, ):
        if key.value is None:
            return None
        if count is None:
            count = len(key.value)
        res = key.value.irange(
            _min.value, _max.value,
            exclusive=(_min.exclusive, _max.exclusive),
            reverse=reverse)
        return res[:count]

    @command(name="XRANGE", fixed=(Key(XStream), StreamRangeTest, StreamRangeTest), repeat=(bytes,))
    def xrange(self, key, _min, _max, *args):
        (count,), _ = extract_args(args, ('+count',))
        return self._xrange(key, _min, _max, False, count)

    @command(name="XREVRANGE", fixed=(Key(XStream), StreamRangeTest, StreamRangeTest), repeat=(bytes,))
    def xrevrange(self, key, _min, _max, *args):
        (count,), _ = extract_args(args, ('+count',))
        return self._xrange(key, _max, _min, True, count)

    def _xread(self, stream_start_id_list: List, count: int, first_pass: bool):
        max_inf = StreamRangeTest.decode(b'+')
        res = list()
        for (item, start_id) in stream_start_id_list:
            stream_results = self._xrange(item, start_id, max_inf, False, count)
            if first_pass and (count is None or len(stream_results) < count):
                raise SimpleError(msgs.WRONGTYPE_MSG)
            if len(stream_results) > 0:
                res.append([item.key, stream_results])
        return res

    @staticmethod
    def _parse_start_id(key: CommandItem, s: bytes) -> StreamRangeTest:
        if s == b'$':
            return StreamRangeTest.decode(key.value.last_item_key(), exclusive=True)
        return StreamRangeTest.decode(s, exclusive=True)

    @command(name="XREAD", fixed=(bytes,), repeat=(bytes,))
    def xread(self, *args):
        (count, timeout,), left_args = extract_args(args, ('+count', '+block',), error_on_unexpected=False)
        if (len(left_args) < 3
                or not casematch(left_args[0], b'STREAMS')
                or len(left_args) % 2 != 1):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        left_args = left_args[1:]
        num_streams = int(len(left_args) / 2)

        stream_start_id_list = list()
        for i in range(num_streams):
            item = CommandItem(left_args[i], self._db, item=self._db.get(left_args[i]), default=None)
            start_id = self._parse_start_id(item, left_args[i + num_streams])
            stream_start_id_list.append((item, start_id,))
        if timeout is None:
            return self._xread(stream_start_id_list, count, False)
        else:
            return self._blocking(timeout, functools.partial(self._xread, stream_start_id_list, count))

    @command(name="XDEL", fixed=(Key(XStream),), repeat=(bytes,), )
    def xdel(self, key, *args):
        if len(args) == 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format('xdel'))
        res = key.value.delete(args)
        return res
