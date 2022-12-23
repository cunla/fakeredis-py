from fakeredis import _msgs as msgs
from fakeredis._commands import (command, Key, Int, BitOffset, BitValue, fix_range_string)
from fakeredis._helpers import SimpleError, casematch


class BitmapCommandsMixin:
    # BITMAP commands
    # TODO: bitfield, bitfield_ro, bitop, bitpos

    @command((Key(bytes, 0),), (bytes,))
    def bitcount(self, key, *args):
        # Redis checks the argument count before decoding integers. That's why
        # we can't declare them as Int.
        if len(args) == 0:
            value = key.value
            return bin(int.from_bytes(value, 'little')).count('1')

        if not 2 <= len(args) <= 3:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        start = Int.decode(args[0])
        end = Int.decode(args[1])
        bit_mode = False
        if len(args) == 3 and self.version < 7:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if len(args) == 3 and self.version >= 7:
            bit_mode = casematch(args[2], b'bit')
            if not bit_mode and not casematch(args[2], b'byte'):
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)

        if bit_mode:
            value = key.value.decode() if key.value else ''
            value = list(map(int, ''.join([bin(ord(i)).lstrip('0b').rjust(8, '0') for i in value])))
            start, end = fix_range_string(start, end, len(value))
            return value[start:end].count(1)
        start, end = fix_range_string(start, end, len(key.value))
        value = key.value[start:end]

        return bin(int.from_bytes(value, 'little')).count('1')

    @command((Key(bytes), BitOffset))
    def getbit(self, key, offset):
        value = key.get(b'')
        byte = offset // 8
        remaining = offset % 8
        actual_bitoffset = 7 - remaining
        try:
            actual_val = value[byte]
        except IndexError:
            return 0
        return 1 if (1 << actual_bitoffset) & actual_val else 0

    @command((Key(bytes), BitOffset, BitValue))
    def setbit(self, key, offset, value):
        val = key.get(b'\x00')
        byte = offset // 8
        remaining = offset % 8
        actual_bitoffset = 7 - remaining
        if len(val) - 1 < byte:
            # We need to expand val so that we can set the appropriate
            # bit.
            needed = byte - (len(val) - 1)
            val += b'\x00' * needed
        old_byte = val[byte]
        if value == 1:
            new_byte = old_byte | (1 << actual_bitoffset)
        else:
            new_byte = old_byte & ~(1 << actual_bitoffset)
        old_value = value if old_byte == new_byte else 1 - value
        reconstructed = bytearray(val)
        reconstructed[byte] = new_byte
        key.update(bytes(reconstructed))
        return old_value

    @staticmethod
    def _bitop(op, *keys):
        value = keys[0].value
        if not isinstance(value, bytes):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        ans = keys[0].value
        i = 1
        while i < len(keys):
            value = keys[i].value if keys[i].value is not None else b''
            if not isinstance(value, bytes):
                raise SimpleError(msgs.WRONGTYPE_MSG)
            ans = bytes(op(a, b) for a, b in zip(ans, value))
            i += 1
        return ans

    @command((bytes, Key(), Key(bytes)), (Key(bytes),))
    def bitop(self, op_name, dst, *keys):
        op = None
        if len(keys) == 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format('bitop'))
        if casematch(op_name, b'and'):
            op = lambda a, b: a & b
        elif casematch(op_name, b'or'):
            op = lambda a, b: a | b
        elif casematch(op_name, b'xor'):
            op = lambda a, b: a ^ b
        elif casematch(op_name, b'not'):
            if len(keys) != 1:
                raise SimpleError(msgs.BITOP_NOT_ONE_KEY_ONLY)
            val = keys[0].value
            print(val)
            print([~val[i] for i in range(len(val))])
            dst.value = bytes([((1 << 8) - 1 - val[i]) for i in range(len(val))])
            return len(dst.value)
        else:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format('bitop'))
        dst.value = self._bitop(op, *keys)
        return len(dst.value)
