import functools
import math
import re

from . import _msgs as msgs
from ._helpers import MAX_STRING_SIZE, null_terminate, SimpleError


class Key:
    """Marker to indicate that argument in signature is a key"""
    UNSPECIFIED = object()

    def __init__(self, type_=None, missing_return=UNSPECIFIED):
        self.type_ = type_
        self.missing_return = missing_return


class Item:
    """An item stored in the database"""

    __slots__ = ['value', 'expireat']

    def __init__(self, value):
        self.value = value
        self.expireat = None


class CommandItem:
    """An item referenced by a command.

    It wraps an Item but has extra fields to manage updates and notifications.
    """

    def __init__(self, key, db, item=None, default=None):
        if item is None:
            self._value = default
            self._expireat = None
        else:
            self._value = item.value
            self._expireat = item.expireat
        self.key = key
        self.db = db
        self._modified = False
        self._expireat_modified = False

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        self._modified = True
        self.expireat = None

    @property
    def expireat(self):
        return self._expireat

    @expireat.setter
    def expireat(self, value):
        self._expireat = value
        self._expireat_modified = True
        self._modified = True  # Since redis 6.0.7

    def get(self, default):
        return self._value if self else default

    def update(self, new_value):
        self._value = new_value
        self._modified = True

    def updated(self):
        self._modified = True

    def writeback(self):
        if self._modified:
            self.db.notify_watch(self.key)
            if not isinstance(self.value, bytes) and not self.value:
                self.db.pop(self.key, None)
                return
            else:
                item = self.db.setdefault(self.key, Item(None))
                item.value = self.value
                item.expireat = self.expireat
        elif self._expireat_modified and self.key in self.db:
            self.db[self.key].expireat = self.expireat

    def __bool__(self):
        return bool(self._value) or isinstance(self._value, bytes)

    __nonzero__ = __bool__  # For Python 2


class Hash(dict):
    redis_type = b'hash'


class Int:
    """Argument converter for 64-bit signed integers"""

    DECODE_ERROR = msgs.INVALID_INT_MSG
    ENCODE_ERROR = msgs.OVERFLOW_MSG
    MIN_VALUE = -2 ** 63
    MAX_VALUE = 2 ** 63 - 1

    @classmethod
    def valid(cls, value):
        return cls.MIN_VALUE <= value <= cls.MAX_VALUE

    @classmethod
    def decode(cls, value):
        try:
            out = int(value)
            if not cls.valid(out) or str(out).encode() != value:
                raise ValueError
        except ValueError:
            raise SimpleError(cls.DECODE_ERROR)
        return out

    @classmethod
    def encode(cls, value):
        if cls.valid(value):
            return str(value).encode()
        else:
            raise SimpleError(cls.ENCODE_ERROR)


class DbIndex(Int):
    """Argument converter for database indices"""

    DECODE_ERROR = msgs.INVALID_DB_MSG
    MIN_VALUE = 0
    MAX_VALUE = 15


class BitOffset(Int):
    """Argument converter for unsigned bit positions"""

    DECODE_ERROR = msgs.INVALID_BIT_OFFSET_MSG
    MIN_VALUE = 0
    MAX_VALUE = 8 * MAX_STRING_SIZE - 1  # Redis imposes 512MB limit on keys


class BitValue(Int):
    DECODE_ERROR = msgs.INVALID_BIT_VALUE_MSG
    MIN_VALUE = 0
    MAX_VALUE = 1


class Timeout(Int):
    """Argument converter for timeouts"""

    DECODE_ERROR = msgs.TIMEOUT_NEGATIVE_MSG
    MIN_VALUE = 0


class Float:
    """Argument converter for floating-point values.

    Redis uses long double for some cases (INCRBYFLOAT, HINCRBYFLOAT)
    and double for others (zset scores), but Python doesn't support
    long double.
    """

    DECODE_ERROR = msgs.INVALID_FLOAT_MSG

    @classmethod
    def decode(cls, value,
               allow_leading_whitespace=False,
               allow_erange=False,
               allow_empty=False,
               crop_null=False):
        # redis has some quirks in float parsing, with several variants.
        # See https://github.com/antirez/redis/issues/5706
        try:
            if crop_null:
                value = null_terminate(value)
            if allow_empty and value == b'':
                value = b'0.0'
            if not allow_leading_whitespace and value[:1].isspace():
                raise ValueError
            if value[-1:].isspace():
                raise ValueError
            out = float(value)
            if math.isnan(out):
                raise ValueError
            if not allow_erange:
                # Values that over- or underflow- are explicitly rejected by
                # redis. This is a crude hack to determine whether the input
                # may have been such a value.
                if out in (math.inf, -math.inf, 0.0) and re.match(b'^[^a-zA-Z]*[1-9]', value):
                    raise ValueError
            return out
        except ValueError:
            raise SimpleError(cls.DECODE_ERROR)

    @classmethod
    def encode(cls, value, humanfriendly):
        if math.isinf(value):
            return str(value).encode()
        elif humanfriendly:
            # Algorithm from ld2string in redis
            out = '{:.17f}'.format(value)
            out = re.sub(r'\.?0+$', '', out)
            return out.encode()
        else:
            return '{:.17g}'.format(value).encode()


class SortFloat(Float):
    DECODE_ERROR = msgs.INVALID_SORT_FLOAT_MSG

    @classmethod
    def decode(cls, value, **kwargs):
        return super().decode(
            value, allow_leading_whitespace=True, allow_empty=True, crop_null=True)


@functools.total_ordering
class BeforeAny:
    def __gt__(self, other):
        return False

    def __eq__(self, other):
        return isinstance(other, BeforeAny)


@functools.total_ordering
class AfterAny:
    def __lt__(self, other):
        return False

    def __eq__(self, other):
        return isinstance(other, AfterAny)


class ScoreTest:
    """Argument converter for sorted set score endpoints."""

    def __init__(self, value, exclusive=False, bytes_val=None):
        self.value = value
        self.exclusive = exclusive
        self.bytes_val = bytes_val

    @classmethod
    def decode(cls, value):
        try:
            original_value = value
            exclusive = False
            if value[:1] == b'(':
                exclusive = True
                value = value[1:]
            value = Float.decode(
                value, allow_leading_whitespace=True, allow_erange=True,
                allow_empty=True, crop_null=True)
            return cls(value, exclusive, original_value)
        except SimpleError:
            raise SimpleError(msgs.INVALID_MIN_MAX_FLOAT_MSG)

    def __str__(self):
        if self.exclusive:
            return '({!r}'.format(self.value)
        else:
            return repr(self.value)

    @property
    def lower_bound(self):
        return self.value, AfterAny() if self.exclusive else BeforeAny()

    @property
    def upper_bound(self):
        return self.value, BeforeAny() if self.exclusive else AfterAny()


class StringTest:
    """Argument converter for sorted set LEX endpoints."""

    def __init__(self, value, exclusive):
        self.value = value
        self.exclusive = exclusive

    @classmethod
    def decode(cls, value):
        if value == b'-':
            return cls(BeforeAny(), True)
        elif value == b'+':
            return cls(AfterAny(), True)
        elif value[:1] == b'(':
            return cls(value[1:], True)
        elif value[:1] == b'[':
            return cls(value[1:], False)
        else:
            raise SimpleError(msgs.INVALID_MIN_MAX_STR_MSG)


class Signature:
    def __init__(self, name, fixed, repeat=(), flags=""):
        self.name = name
        self.fixed = fixed
        self.repeat = repeat
        self.flags = flags

    def check_arity(self, args, version):
        if len(args) != len(self.fixed):
            delta = len(args) - len(self.fixed)
            if delta < 0 or not self.repeat:
                msg = msgs.WRONG_ARGS_MSG7 if version >= 7 else msgs.WRONG_ARGS_MSG6.format(self.name)
                raise SimpleError(msg)

    def apply(self, args, db, version):
        """Returns a tuple, which is either:
        - transformed args and a dict of CommandItems; or
        - a single containing a short-circuit return value
        """
        self.check_arity(args, version)
        if self.repeat:
            delta = len(args) - len(self.fixed)
            if delta % len(self.repeat) != 0:
                msg = msgs.WRONG_ARGS_MSG7 if version >= 7 else msgs.WRONG_ARGS_MSG6.format(self.name)
                raise SimpleError(msg)

        types = list(self.fixed)
        for i in range(len(args) - len(types)):
            types.append(self.repeat[i % len(self.repeat)])

        args = list(args)
        # First pass: convert/validate non-keys, and short-circuit on missing keys
        for i, (arg, type_) in enumerate(zip(args, types)):
            if isinstance(type_, Key):
                if type_.missing_return is not Key.UNSPECIFIED and arg not in db:
                    return type_.missing_return,
            elif type_ != bytes:
                args[i] = type_.decode(args[i], )

        # Second pass: read keys and check their types
        command_items = []
        for i, (arg, type_) in enumerate(zip(args, types)):
            if isinstance(type_, Key):
                item = db.get(arg)
                default = None
                if type_.type_ is not None:
                    if item is not None and type(item.value) != type_.type_:
                        raise SimpleError(msgs.WRONGTYPE_MSG)
                    if item is None:
                        if type_.type_ is not bytes:
                            default = type_.type_()
                args[i] = CommandItem(arg, db, item, default=default)
                command_items.append(args[i])

        return args, command_items


def command(*args, **kwargs):
    def decorator(func):
        name = kwargs.pop('name', func.__name__)
        func._fakeredis_sig = Signature(name, *args, **kwargs)
        return func

    return decorator


def delete_keys(*keys):
    ans = 0
    done = set()
    for key in keys:
        if key and key.key not in done:
            key.value = None
            done.add(key.key)
            ans += 1
    return ans


def fix_range(start, end, length):
    # Redis handles negative slightly differently for zrange
    if start < 0:
        start = max(0, start + length)
    if end < 0:
        end += length
    if start > end or start >= length:
        return -1, -1
    end = min(end, length - 1)
    return start, end + 1
