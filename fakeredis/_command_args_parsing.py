from typing import Union

from . import _msgs as msgs
from ._commands import Int
from ._helpers import casematch, SimpleError


def _encode_arg(s: str):
    if s.startswith('+'):
        s = s[1:]
    return s.encode()


def extract_args(actual_args: tuple[bytes, ...], expected: tuple[str, ...]) -> tuple[Union[int, str], ...]:
    """
    Extract from actual arguments which arguments exist and their
    numerical value. Numerical arguments are identified by starting with a +.

    >>> extract_args((b'nx', b'ex', b'324', b'xx',), ('nx', 'xx', '+ex', 'keepttl'))
    True, True, 324, False
    """

    results = [None if key.startswith('+') else False
               for key in expected]
    args_dict: dict[bytes, int] = {_encode_arg(k): i for (i, k) in enumerate(expected)}
    i = 0
    while i < len(actual_args):
        found = False
        for key in args_dict:
            if casematch(actual_args[i], key):
                arg_position: int = args_dict[key]
                results[arg_position] = True
                if expected[arg_position].startswith('+'):
                    results[arg_position] = Int.decode(actual_args[i + 1])
                    i += 1
                i += 1
                found = True
                break
        if not found:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
    return results
