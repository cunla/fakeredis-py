from __future__ import annotations

import functools
import re
import time
from typing import AnyStr


class SimpleString:
    def __init__(self, value: bytes) -> None:
        if not isinstance(value, bytes):
            raise TypeError("SimpleString value must be bytes")
        self.value = value

    @classmethod
    def decode(cls, value: bytes) -> bytes:
        return value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"


class SimpleError(Exception):
    """Exception that will be turned into a frontend-specific exception."""

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("SimpleError value must be str")
        self.value = value


class NoResponse:
    """Returned by pub/sub commands to indicate that no response should be returned"""


OK = SimpleString(b"OK")
QUEUED = SimpleString(b"QUEUED")
BGSAVE_STARTED = SimpleString(b"Background saving started")

# Dragonfly stores at most 256MB in one string, where redis allows 512MB.
DRAGONFLY_MAX_STRING_SIZE = 2**28
MAX_STRING_SIZE = 512 * 1024 * 1024


def current_time() -> int:
    """Return current_time in ms"""
    return int(time.time() * 1000)


def null_terminate(s: bytes) -> bytes:
    # Redis uses C functions on some strings, which means they stop at the first NULL.
    ind = s.find(b"\0")
    if ind > -1:
        return s[:ind].lower()
    return s.lower()


def casematch_any(a: bytes, *args: bytes) -> bool:
    return any(casematch(a, b) for b in args)


def casematch(a: bytes, b: bytes) -> bool:
    return null_terminate(a) == null_terminate(b)


def decode_command_bytes(s: bytes) -> str:
    return s.decode(encoding="utf-8", errors="replace").lower()


def asbytes(value: AnyStr) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


@functools.lru_cache(maxsize=1024)
def compile_pattern(pattern_bytes: bytes) -> re.Pattern:  # type: ignore
    """Compile a glob pattern (e.g., for keys) to a `bytes` regex.

    Cached: clients reuse a handful of patterns, and every PUBLISH and keyspace notification recompiles each pattern
    subscribed with PSUBSCRIBE.

    `fnmatch.fnmatchcase` doesn't work for this because it uses different
    escaping rules to redis, uses ! instead of ^ to negate a character set, and handles invalid cases (such as a [
    without a ]) differently. This implementation was written by studying the redis implementation.
    """
    # It's easier to work with text than bytes, because indexing bytes doesn't behave the same in Python 3. Latin-1 will
    # round-trip safely.
    pattern: str = pattern_bytes.decode(
        "latin-1",
    )
    parts = ["^"]
    i = 0
    pattern_len = len(pattern)
    while i < pattern_len:
        c = pattern[i]
        i += 1
        if c == "?":
            parts.append(".")
        elif c == "*":
            parts.append(".*")
        elif c == "\\":
            if i == pattern_len:
                i -= 1
            parts.append(re.escape(pattern[i]))
            i += 1
        elif c == "[":
            parts.append("[")
            if i < pattern_len and pattern[i] == "^":
                i += 1
                parts.append("^")
            parts_len = len(parts)  # To detect if anything was added
            while i < pattern_len:
                if pattern[i] == "\\" and i + 1 < pattern_len:
                    i += 1
                    parts.append(re.escape(pattern[i]))
                elif pattern[i] == "]":
                    i += 1
                    break
                elif i + 2 < pattern_len and pattern[i + 1] == "-":
                    start = pattern[i]
                    end = pattern[i + 2]
                    if start > end:
                        start, end = end, start
                    parts.append(re.escape(start) + "-" + re.escape(end))
                    i += 2
                else:
                    parts.append(re.escape(pattern[i]))
                i += 1
            if len(parts) == parts_len:
                if parts[-1] == "[":
                    # Empty group - will never match
                    parts[-1] = "(?:$.)"
                else:
                    # Negated empty group - matches any character
                    if parts[-1] != "^":
                        raise AssertionError("Invalid pattern")
                    parts.pop()
                    parts[-1] = "."
            else:
                parts.append("]")
        else:
            parts.append(re.escape(c))
    parts.append("\\Z")
    regex: bytes = "".join(parts).encode("latin-1")
    return re.compile(regex, flags=re.DOTALL)


def fix_range(start: int, end: int, length: int) -> tuple[int, int]:
    # Redis handles negative slightly differently for zrange
    if start < 0:
        start = max(0, start + length)
    if end < 0:
        end += length
    if start > end or start >= length:
        return -1, -1
    end = min(end, length - 1)
    return start, end + 1


def fix_range_string(start: int, end: int, length: int) -> tuple[int, int]:
    # Negative number handling is based on the redis source code
    if 0 > start > end and end < 0:
        return -1, -1
    if start < 0:
        start = max(0, start + length)
    if end < 0:
        end = max(0, end + length)
    end = min(end, length - 1)
    return start, end + 1
