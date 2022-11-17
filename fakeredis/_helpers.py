import logging
import re
import threading
import time
import weakref
from collections import defaultdict
from collections.abc import MutableMapping

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


def valid_response_type(value, nested=False):
    if isinstance(value, NoResponse) and not nested:
        return True
    if (value is not None
            and not isinstance(value, (bytes, SimpleString, SimpleError, int, list))):
        return False
    if isinstance(value, list):
        if any(not valid_response_type(item, True) for item in value):
            return False
    return True


def fix_range_string(start, end, length):
    # Negative number handling is based on the redis source code
    if 0 > start > end and end < 0:
        return -1, -1
    if start < 0:
        start = max(0, start + length)
    if end < 0:
        end = max(0, end + length)
    end = min(end, length - 1)
    return start, end + 1


class _DummyParser:
    def __init__(self, socket_read_size):
        self.socket_read_size = socket_read_size

    def on_disconnect(self):
        pass

    def on_connect(self, connection):
        pass


class FakeSelector(object):
    def __init__(self, sock):
        self.sock = sock

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

    @staticmethod
    def check_is_ready_for_command(timeout):
        return True
