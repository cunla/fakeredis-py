from __future__ import annotations

import math
import re
import sys
from collections.abc import Sequence
from typing import Any

from . import _msgs as msgs
from ._helpers import SimpleError, null_terminate
from .model import AfterAny, BeforeAny


class RedisType:
    @classmethod
    def decode(cls, *args, **kwargs):  # type:ignore
        raise NotImplementedError


class Int(RedisType):
    """Argument converter for 64-bit signed integers"""

    DECODE_ERROR = msgs.INVALID_INT_MSG
    ENCODE_ERROR = msgs.OVERFLOW_MSG
    MIN_VALUE = -(2**63)
    MAX_VALUE = 2**63 - 1

    @classmethod
    def valid(cls, value: int) -> bool:
        return cls.MIN_VALUE <= value <= cls.MAX_VALUE

    @classmethod
    def decode(cls, value: bytes, decode_error: str | None = None) -> int:
        try:
            out = int(value)
            if not cls.valid(out) or str(out).encode() != value:
                raise ValueError
            return out
        except ValueError:
            raise SimpleError(decode_error or cls.DECODE_ERROR)

    @classmethod
    def encode(cls, value: int) -> bytes:
        if cls.valid(value):
            return str(value).encode()
        else:
            raise SimpleError(cls.ENCODE_ERROR)


class DbIndex(Int):
    """Argument converter for database indices"""

    DECODE_ERROR = msgs.INVALID_DB_MSG
    MIN_VALUE = 0
    MAX_VALUE = 15


class Float(RedisType):
    """Argument converter for floating-point values.

    Redis uses long double for some cases (INCRBYFLOAT, HINCRBYFLOAT) and double for others (zset scores), but Python
    doesn't support
    `long double`.
    """

    DECODE_ERROR = msgs.INVALID_FLOAT_MSG

    @classmethod
    def decode(
        cls,
        value: bytes,
        allow_leading_whitespace: bool = False,
        allow_erange: bool = False,
        allow_empty: bool = False,
        crop_null: bool = False,
        decode_error: str | None = None,
    ) -> float:
        # Redis has some quirks in float parsing, with several variants. See
        # https://github.com/antirez/redis/issues/5706
        try:
            if crop_null:
                value = null_terminate(value)
            if allow_empty and value == b"":
                value = b"0.0"
            if not allow_leading_whitespace and value[:1].isspace():
                raise ValueError
            if value[-1:].isspace():
                raise ValueError
            out = float(value)
            if math.isnan(out):
                raise ValueError
            # Values that over- or under-flow are explicitly rejected by redis. This is a crude hack to determine
            # whether the input may have been such a value.
            if not allow_erange and out in (math.inf, -math.inf, 0.0) and re.match(b"^[^a-zA-Z]*[1-9]", value):
                raise ValueError
            return out
        except ValueError:
            raise SimpleError(decode_error or cls.DECODE_ERROR)

    @classmethod
    def encode_shortest(cls, value: float) -> bytes:
        """Render a double the way Dragonfly does, as the shortest string that round-trips.

        Redis pads doubles out to 17 significant digits, so a score of 3.2 comes back as
        ``3.2000000000000002``; Dragonfly prints ``3.2``, and drops the fractional part
        altogether for whole numbers.
        """
        if math.isinf(value):
            return str(value).encode()
        out = repr(value)
        if out.endswith(".0"):
            out = out[:-2]
        return out.encode()

    @classmethod
    def encode(cls, value: float, humanfriendly: bool) -> bytes:
        if math.isinf(value):
            return str(value).encode()
        elif humanfriendly:
            # Algorithm from `ld2string` in redis
            out = f"{value:.17f}"
            out = re.sub(r"\.?0+$", "", out)
            return out.encode()
        else:
            return f"{value:.17g}".encode()


class Timeout(Float):
    """Argument converter for timeouts"""

    DECODE_ERROR = msgs.TIMEOUT_NEGATIVE_MSG
    MIN_VALUE = 0.0

    @classmethod
    def decode(cls, value: bytes, *args: Any, **kwargs: Any) -> float:
        res = super().decode(value, *args, **kwargs)
        if res < cls.MIN_VALUE:
            raise SimpleError(cls.DECODE_ERROR)
        return res


class StringTest(RedisType):
    """Argument converter for sorted set LEX endpoints."""

    def __init__(self, value: bytes | BeforeAny | AfterAny, exclusive: bool):
        self.value = value
        self.exclusive = exclusive

    @property
    def inclusive(self) -> bool:
        return not self.exclusive

    @classmethod
    def decode(cls, value: bytes) -> StringTest:
        if value == b"-":
            return cls(BeforeAny(), True)
        elif value == b"+":
            return cls(AfterAny(), True)
        elif value[:1] == b"(":
            return cls(value[1:], True)
        elif value[:1] == b"[":
            return cls(value[1:], False)
        else:
            raise SimpleError(msgs.INVALID_MIN_MAX_STR_MSG)


def _count_params(s: str) -> int:
    res = 0
    while res < len(s) and s[res] in ".+*~":
        res += 1
    return res


def _encode_arg(s: str) -> bytes:
    return s[_count_params(s) :].encode()


def _default_value(s: str) -> Any:
    if s[0] == "~":
        return None
    ind = _count_params(s)
    if ind == 0:
        return False
    elif ind == 1:
        return None
    else:
        return [None] * ind


def extract_args(
    actual_args: tuple[bytes, ...],
    expected: tuple[str, ...],
    error_on_unexpected: bool = True,
    left_from_first_unexpected: bool = True,
    exception: str | None = None,
) -> tuple[list[Any], Sequence[Any]]:
    """Parse argument values.

    Extract from actual arguments which arguments exist and their value if relevant.

    :param actual_args: The actual arguments to parse
    :param expected: Arguments to look for, see below explanation.
    :param error_on_unexpected: Should an error be raised when actual_args contain an unexpected argument?
    :param left_from_first_unexpected: Once reaching an unexpected argument in actual_args, Should parsing stop?
    :param exception: What exception msg to raise
    :returns:
        - List of values for expected arguments.
        - List of remaining args.

    An expected argument can have parameters:
    - A numerical (Int) parameter is identified with '+'
    - A float (Float) parameter is identified with '.'
    - A non-numerical parameter is identified with a '*'
    - An argument with potentially ~ or = between the argument name and the value is identified with a '~'
    - A numberical argument with potentially ~ or = between the argument name and the value marked with a '~+'

    E.g. '++limit' will translate as an argument with 2 int parameters.

    >>> extract_args((b'nx', b'ex', b'324', b'xx',), ('nx', 'xx', '+ex', 'keepttl'))
    [True, True, 324, False], None

    >>> extract_args(
        (b'maxlen', b'10',b'nx', b'ex', b'324', b'xx',),
        ('~+maxlen', 'nx', 'xx', '+ex', 'keepttl'))
    10, [True, True, 324, False], None
    """
    args_info: dict[bytes, tuple[int, int]] = {_encode_arg(k): (i, _count_params(k)) for (i, k) in enumerate(expected)}

    def _parse_params(key: bytes, ind: int, _actual_args: tuple[bytes, ...]) -> tuple[Any, int]:
        """Parse an argument from actual args.
        :param key: Argument name to parse
        :param ind: index of argument in actual_args
        :param _actual_args: actual args
        """
        pos, expected_following = args_info[key]
        argument_name = expected[pos]

        # Deal with parameters with optional ~/= before numerical value.
        arg: Any
        if argument_name[0] == "~":
            if ind + 1 >= len(_actual_args):
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            if _actual_args[ind + 1] != b"~" and _actual_args[ind + 1] != b"=":
                arg, _parsed = _actual_args[ind + 1], 1
            elif ind + 2 >= len(_actual_args):
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            else:
                arg, _parsed = _actual_args[ind + 2], 2
            if argument_name[1] == "+":
                arg = Int.decode(arg)
            return arg, _parsed
        # Boolean parameters
        if expected_following == 0:
            return True, 0

        if ind + expected_following >= len(_actual_args):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        temp_res = []
        for i in range(expected_following):
            curr_arg: Any = _actual_args[ind + i + 1]
            if argument_name[i] == "+":
                curr_arg = Int.decode(curr_arg)
            elif argument_name[i] == ".":
                curr_arg = Float.decode(curr_arg)
            temp_res.append(curr_arg)

        if len(temp_res) == 1:
            return temp_res[0], expected_following
        else:
            return temp_res, expected_following

    results: list[Any] = [_default_value(key) for key in expected]
    left_args = []
    i = 0
    while i < len(actual_args):
        found = False
        for key, arg_info in args_info.items():
            if null_terminate(actual_args[i]) == key:
                arg_position, _ = arg_info
                results[arg_position], parsed = _parse_params(key, i, actual_args)
                i += parsed
                found = True
                break

        if not found:
            if error_on_unexpected:
                raise (
                    SimpleError(msgs.SYNTAX_ERROR_MSG)
                    if exception is None
                    # The offending argument is echoed as text, not as a bytes repr.
                    else SimpleError(exception.format(actual_args[i].decode(errors="replace")))
                )
            if left_from_first_unexpected:
                return results, actual_args[i:]
            left_args.append(actual_args[i])
        i += 1
    return results, left_args


def parse_mpop_args(
    command: str, numkeys: int, args: tuple[bytes, ...], directions: tuple[str, str], server_type: str = "redis"
) -> tuple[Sequence[bytes], int, bool]:
    """Validate the LMPOP/BLMPOP/ZMPOP/BZMPOP tail: keys, a direction token, optional COUNT.

    `args` is ``key [key ...] <directions[0] | directions[1]> [COUNT count]``.
    Returns (keys, count, whether ``directions[0]`` was the chosen direction).
    """
    if len(args) < 2:  # arity (at least one key + a direction) is checked before numkeys, like real redis
        raise SimpleError(msgs.WRONG_ARGS_MSG6.format(command))
    if numkeys <= 0:
        if server_type != "dragonfly":
            raise SimpleError(msgs.NUMKEYS_GREATER_THAN_ZERO_MSG)
        # Dragonfly reads numkeys as unsigned, so a negative one never decodes.
        raise SimpleError(msgs.INVALID_INT_MSG if numkeys < 0 else msgs.DRAGONFLY_AT_LEAST_ONE_KEY_MSG)
    (count, first, second), keys = extract_args(
        args, ("+count", *directions), error_on_unexpected=False, left_from_first_unexpected=False
    )
    if len(keys) != numkeys or first == second:  # exactly one direction, and it follows exactly `numkeys` keys
        raise SimpleError(msgs.SYNTAX_ERROR_MSG)
    if count is not None and count <= 0:
        if server_type != "dragonfly":
            raise SimpleError(msgs.COUNT_GREATER_THAN_ZERO_MSG)
        # Dragonfly accepts COUNT 0 and simply pops nothing. A negative count is read as unsigned by ZMPOP -- popping
        # everything -- but rejected outright by LMPOP.
        if count < 0:
            if command.lower().endswith("lmpop"):
                raise SimpleError(msgs.INVALID_INT_MSG)
            count = sys.maxsize
    return keys, 1 if count is None else count, first
