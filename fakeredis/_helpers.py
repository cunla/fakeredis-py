import functools
import logging
import re
import threading
import time
import weakref
from collections import defaultdict
from collections.abc import MutableMapping

import math

LOGGER = logging.getLogger('fakeredis')
REDIS_LOG_LEVELS = {
    b'LOG_DEBUG': 0,
    b'LOG_VERBOSE': 1,
    b'LOG_NOTICE': 2,
    b'LOG_WARNING': 3
}
REDIS_LOG_LEVELS_TO_LOGGING = {
    0: logging.DEBUG,
    1: logging.INFO,
    2: logging.INFO,
    3: logging.WARNING
}

MAX_STRING_SIZE = 512 * 1024 * 1024

INVALID_EXPIRE_MSG = "ERR invalid expire time in {}"
WRONGTYPE_MSG = "WRONGTYPE Operation against a key holding the wrong kind of value"
SYNTAX_ERROR_MSG = "ERR syntax error"
INVALID_INT_MSG = "ERR value is not an integer or out of range"
INVALID_FLOAT_MSG = "ERR value is not a valid float"
INVALID_OFFSET_MSG = "ERR offset is out of range"
INVALID_BIT_OFFSET_MSG = "ERR bit offset is not an integer or out of range"
INVALID_BIT_VALUE_MSG = "ERR bit is not an integer or out of range"
INVALID_DB_MSG = "ERR DB index is out of range"
INVALID_MIN_MAX_FLOAT_MSG = "ERR min or max is not a float"
INVALID_MIN_MAX_STR_MSG = "ERR min or max not a valid string range item"
STRING_OVERFLOW_MSG = "ERR string exceeds maximum allowed size (512MB)"
OVERFLOW_MSG = "ERR increment or decrement would overflow"
NONFINITE_MSG = "ERR increment would produce NaN or Infinity"
SCORE_NAN_MSG = "ERR resulting score is not a number (NaN)"
INVALID_SORT_FLOAT_MSG = "ERR One or more scores can't be converted into double"
SRC_DST_SAME_MSG = "ERR source and destination objects are the same"
NO_KEY_MSG = "ERR no such key"
INDEX_ERROR_MSG = "ERR index out of range"
ZADD_NX_XX_ERROR_MSG = "ERR ZADD allows either 'nx' or 'xx', not both"
ZADD_INCR_LEN_ERROR_MSG = "ERR INCR option supports a single increment-element pair"
ZUNIONSTORE_KEYS_MSG = "ERR at least 1 input key is needed for ZUNIONSTORE/ZINTERSTORE"
WRONG_ARGS_MSG = "ERR wrong number of arguments for '{}' command"
UNKNOWN_COMMAND_MSG = "ERR unknown command '{}'"
EXECABORT_MSG = "EXECABORT Transaction discarded because of previous errors."
MULTI_NESTED_MSG = "ERR MULTI calls can not be nested"
WITHOUT_MULTI_MSG = "ERR {0} without MULTI"
WATCH_INSIDE_MULTI_MSG = "ERR WATCH inside MULTI is not allowed"
NEGATIVE_KEYS_MSG = "ERR Number of keys can't be negative"
TOO_MANY_KEYS_MSG = "ERR Number of keys can't be greater than number of args"
TIMEOUT_NEGATIVE_MSG = "ERR timeout is negative"
NO_MATCHING_SCRIPT_MSG = "NOSCRIPT No matching script. Please use EVAL."
GLOBAL_VARIABLE_MSG = "ERR Script attempted to set global variables: {}"
COMMAND_IN_SCRIPT_MSG = "ERR This Redis command is not allowed from scripts"
BAD_SUBCOMMAND_MSG = "ERR Unknown {} subcommand or wrong # of args."
BAD_COMMAND_IN_PUBSUB_MSG = \
    "ERR only (P)SUBSCRIBE / (P)UNSUBSCRIBE / PING / QUIT allowed in this context"
CONNECTION_ERROR_MSG = "FakeRedis is emulating a connection error."
REQUIRES_MORE_ARGS_MSG = "ERR {} requires {} arguments or more."
LOG_INVALID_DEBUG_LEVEL_MSG = "ERR Invalid debug level."
LUA_COMMAND_ARG_MSG = "ERR Lua redis() command arguments must be strings or integers"
LUA_WRONG_NUMBER_ARGS_MSG = "ERR wrong number or type of arguments"
SCRIPT_ERROR_MSG = "ERR Error running script (call to f_{}): @user_script:?: {}"
RESTORE_KEY_EXISTS = "BUSYKEY Target key name already exists."
RESTORE_INVALID_CHECKSUM_MSG = "ERR DUMP payload version or checksum are wrong"
RESTORE_INVALID_TTL_MSG = "ERR Invalid TTL value, must be >= 0"

FLAG_NO_SCRIPT = 's'  # Command not allowed in scripts


class SimpleString:
    def __init__(self, value):
        assert isinstance(value, bytes)
        self.value = value

    @classmethod
    def decode(cls, value):
        return value


class SimpleError(Exception):
    """Exception that will be turned into a frontend-specific exception."""

    def __init__(self, value):
        assert isinstance(value, str)
        self.value = value


class NoResponse:
    """Returned by pub/sub commands to indicate that no response should be returned"""
    pass


OK = SimpleString(b'OK')
QUEUED = SimpleString(b'QUEUED')
PONG = SimpleString(b'PONG')
BGSAVE_STARTED = SimpleString(b'Background saving started')


def null_terminate(s):
    # Redis uses C functions on some strings, which means they stop at the
    # first NULL.
    if b'\0' in s:
        return s[:s.find(b'\0')]
    return s


def casenorm(s):
    return null_terminate(s).lower()


def casematch(a, b):
    return casenorm(a) == casenorm(b)


def compile_pattern(pattern):
    """Compile a glob pattern (e.g. for keys) to a bytes regex.

    fnmatch.fnmatchcase doesn't work for this, because it uses different
    escaping rules to redis, uses ! instead of ^ to negate a character set,
    and handles invalid cases (such as a [ without a ]) differently. This
    implementation was written by studying the redis implementation.
    """
    # It's easier to work with text than bytes, because indexing bytes
    # doesn't behave the same in Python 3. Latin-1 will round-trip safely.
    pattern = pattern.decode('latin-1', )
    parts = ['^']
    i = 0
    pattern_len = len(pattern)
    while i < pattern_len:
        c = pattern[i]
        i += 1
        if c == '?':
            parts.append('.')
        elif c == '*':
            parts.append('.*')
        elif c == '\\':
            if i == pattern_len:
                i -= 1
            parts.append(re.escape(pattern[i]))
            i += 1
        elif c == '[':
            parts.append('[')
            if i < pattern_len and pattern[i] == '^':
                i += 1
                parts.append('^')
            parts_len = len(parts)  # To detect if anything was added
            while i < pattern_len:
                if pattern[i] == '\\' and i + 1 < pattern_len:
                    i += 1
                    parts.append(re.escape(pattern[i]))
                elif pattern[i] == ']':
                    i += 1
                    break
                elif i + 2 < pattern_len and pattern[i + 1] == '-':
                    start = pattern[i]
                    end = pattern[i + 2]
                    if start > end:
                        start, end = end, start
                    parts.append(re.escape(start) + '-' + re.escape(end))
                    i += 2
                else:
                    parts.append(re.escape(pattern[i]))
                i += 1
            if len(parts) == parts_len:
                if parts[-1] == '[':
                    # Empty group - will never match
                    parts[-1] = '(?:$.)'
                else:
                    # Negated empty group - matches any character
                    assert parts[-1] == '^'
                    parts.pop()
                    parts[-1] = '.'
            else:
                parts.append(']')
        else:
            parts.append(re.escape(c))
    parts.append('\\Z')
    regex = ''.join(parts).encode('latin-1')
    return re.compile(regex, re.S)


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


class Database(MutableMapping):
    def __init__(self, lock, *args, **kwargs):
        self._dict = dict(*args, **kwargs)
        self.time = 0.0
        self._watches = defaultdict(weakref.WeakSet)  # key to set of connections
        self.condition = threading.Condition(lock)
        self._change_callbacks = set()

    def swap(self, other):
        self._dict, other._dict = other._dict, self._dict
        self.time, other.time = other.time, self.time

    def notify_watch(self, key):
        for sock in self._watches.get(key, set()):
            sock.notify_watch()
        self.condition.notify_all()
        for callback in self._change_callbacks:
            callback()

    def add_watch(self, key, sock):
        self._watches[key].add(sock)

    def remove_watch(self, key, sock):
        watches = self._watches[key]
        watches.discard(sock)
        if not watches:
            del self._watches[key]

    def add_change_callback(self, callback):
        self._change_callbacks.add(callback)

    def remove_change_callback(self, callback):
        self._change_callbacks.remove(callback)

    def clear(self):
        for key in self:
            self.notify_watch(key)
        self._dict.clear()

    def expired(self, item):
        return item.expireat is not None and item.expireat < self.time

    def _remove_expired(self):
        for key in list(self._dict):
            item = self._dict[key]
            if self.expired(item):
                del self._dict[key]

    def __getitem__(self, key):
        item = self._dict[key]
        if self.expired(item):
            del self._dict[key]
            raise KeyError(key)
        return item

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __delitem__(self, key):
        del self._dict[key]

    def __iter__(self):
        self._remove_expired()
        return iter(self._dict)

    def __len__(self):
        self._remove_expired()
        return len(self._dict)

    def __hash__(self):
        return hash(super(object, self))

    def __eq__(self, other):
        return super(object, self) == other


class Hash(dict):
    redis_type = b'hash'


class Int:
    """Argument converter for 64-bit signed integers"""

    DECODE_ERROR = INVALID_INT_MSG
    ENCODE_ERROR = OVERFLOW_MSG
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


class BitOffset(Int):
    """Argument converter for unsigned bit positions"""

    DECODE_ERROR = INVALID_BIT_OFFSET_MSG
    MIN_VALUE = 0
    MAX_VALUE = 8 * MAX_STRING_SIZE - 1  # Redis imposes 512MB limit on keys


class BitValue(Int):
    DECODE_ERROR = INVALID_BIT_VALUE_MSG
    MIN_VALUE = 0
    MAX_VALUE = 1


class DbIndex(Int):
    """Argument converter for database indices"""

    DECODE_ERROR = INVALID_DB_MSG
    MIN_VALUE = 0
    MAX_VALUE = 15


class Timeout(Int):
    """Argument converter for timeouts"""

    DECODE_ERROR = TIMEOUT_NEGATIVE_MSG
    MIN_VALUE = 0


class Float:
    """Argument converter for floating-point values.

    Redis uses long double for some cases (INCRBYFLOAT, HINCRBYFLOAT)
    and double for others (zset scores), but Python doesn't support
    long double.
    """

    DECODE_ERROR = INVALID_FLOAT_MSG

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
    DECODE_ERROR = INVALID_SORT_FLOAT_MSG

    @classmethod
    def decode(cls, value, **kwargs):
        return super().decode(
            value, allow_leading_whitespace=True, allow_empty=True, crop_null=True)


class ScoreTest:
    """Argument converter for sorted set score endpoints."""

    def __init__(self, value, exclusive=False):
        self.value = value
        self.exclusive = exclusive

    @classmethod
    def decode(cls, value):
        try:
            exclusive = False
            if value[:1] == b'(':
                exclusive = True
                value = value[1:]
            value = Float.decode(
                value, allow_leading_whitespace=True, allow_erange=True,
                allow_empty=True, crop_null=True)
            return cls(value, exclusive)
        except SimpleError:
            raise SimpleError(INVALID_MIN_MAX_FLOAT_MSG)

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
            raise SimpleError(INVALID_MIN_MAX_STR_MSG)


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


class Key:
    """Marker to indicate that argument in signature is a key"""
    UNSPECIFIED = object()

    def __init__(self, type_=None, missing_return=UNSPECIFIED):
        self.type_ = type_
        self.missing_return = missing_return


class Signature:
    def __init__(self, name, fixed, repeat=(), flags=""):
        self.name = name
        self.fixed = fixed
        self.repeat = repeat
        self.flags = flags

    def check_arity(self, args):
        if len(args) != len(self.fixed):
            delta = len(args) - len(self.fixed)
            if delta < 0 or not self.repeat:
                raise SimpleError(WRONG_ARGS_MSG.format(self.name))

    def apply(self, args, db):
        """Returns a tuple, which is either:
        - transformed args and a dict of CommandItems; or
        - a single containing a short-circuit return value
        """
        self.check_arity(args)
        if self.repeat:
            delta = len(args) - len(self.fixed)
            if delta % len(self.repeat) != 0:
                raise SimpleError(WRONG_ARGS_MSG.format(self.name))

        types = list(self.fixed)
        for i in range(len(args) - len(types)):
            types.append(self.repeat[i % len(self.repeat)])

        args = list(args)
        # First pass: convert/validate non-keys, and short-circuit on missing keys
        for i, (arg, type_) in enumerate(zip(args, types)):
            if isinstance(type_, Key):
                if type_.missing_return is not Key.UNSPECIFIED and arg not in db:
                    return (type_.missing_return,)
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
                        raise SimpleError(WRONGTYPE_MSG)
                    if item is None:
                        if type_.type_ is not bytes:
                            default = type_.type_()
                args[i] = CommandItem(arg, db, item, default=default)
                command_items.append(args[i])

        return args, command_items


def valid_response_type(value, nested=False):
    if isinstance(value, NoResponse) and not nested:
        return True
    if value is not None and not isinstance(value, (bytes, SimpleString, SimpleError,
                                                    int, list)):
        return False
    if isinstance(value, list):
        if any(not valid_response_type(item, True) for item in value):
            return False
    return True


def command(*args, **kwargs):
    def decorator(func):
        name = kwargs.pop('name', func.__name__)
        func._fakeredis_sig = Signature(name, *args, **kwargs)
        return func

    return decorator




class _DummyParser:
    def __init__(self, socket_read_size):
        self.socket_read_size = socket_read_size

    def on_disconnect(self):
        pass

    def on_connect(self, connection):
        pass


# Redis <3.2 will not have a selector
try:
    from redis.selector import BaseSelector
except ImportError:
    class BaseSelector:
        def __init__(self, sock):
            self.sock = sock


class FakeSelector(BaseSelector):
    def check_can_read(self, timeout):
        if self.sock.responses.qsize():
            return True
        if timeout is not None and timeout <= 0:
            return False

        # A sleep/poll loop is easier to mock out than messing with condition
        # variables.
        start = time.time()
        while True:
            if self.sock.responses.qsize():
                return True
            time.sleep(0.01)
            now = time.time()
            if timeout is not None and now > start + timeout:
                return False

    def check_is_ready_for_command(self, timeout):
        return True
