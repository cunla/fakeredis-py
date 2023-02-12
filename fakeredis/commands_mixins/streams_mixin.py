import fakeredis._msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import Key, command, StreamRangeTest
from fakeredis._helpers import SimpleError
from fakeredis._stream import XStream


class StreamsCommandsMixin:
    @command(name="XADD", fixed=(Key(),), repeat=(bytes,), )
    def xadd(self, key, *args):
        # TODO: MAXLEN, MINID, LIMIT
        (nomkstream, limit, maxlen, minid), left_args = extract_args(
            args, ('nomkstream', '+limit', '~+maxlen', '~minid'), error_on_unexpected=False)
        if nomkstream and key.value is None:
            return None
        id_str = left_args[0]
        elements = left_args[1:]
        if not elements or len(elements) % 2 != 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format('XADD'))
        stream = key.value or XStream()
        if self.version < 7 and id_str != b'*' and StreamRangeTest.parse_id(id_str) == (-1, -1):
            raise SimpleError(msgs.XADD_INVALID_ID)
        id_str = stream.add(elements, id_str=id_str)
        if id_str is None:
            if StreamRangeTest.parse_id(left_args[0]) == (-1, -1):
                raise SimpleError(msgs.XADD_INVALID_ID)
            raise SimpleError(msgs.XADD_ID_LOWER_THAN_LAST)
        if maxlen is not None:
            stream.trim(maxlen)
        if minid is not None:
            ind = stream.find_index(minid)
            stream.trim(len(stream) - ind)
        key.update(stream)
        return id_str

    @command(name="XLEN", fixed=(Key(XStream),))
    def xlen(self, key):
        if key.value is None:
            return 0
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
