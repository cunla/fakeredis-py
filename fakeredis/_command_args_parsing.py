from typing import Tuple, List, Dict

from . import _msgs as msgs
from ._commands import Int
from ._helpers import SimpleError, null_terminate


def _count_params(s: str):
    res = 0
    while s[res] == '+' or s[res] == '*':
        res += 1
    return res


def _encode_arg(s: str):
    return s[_count_params(s):].encode()


def _default_value(s: str):
    ind = _count_params(s)
    if ind == 0:
        return False
    elif ind == 1:
        return None
    else:
        return [None] * ind


def _parse_params(argument_name: str, ind: int, parse_following: int, actual_args: Tuple[bytes, ...]):
    if parse_following == 0:
        return True
    if ind + parse_following >= len(actual_args):
        raise SimpleError(msgs.SYNTAX_ERROR_MSG)
    temp_res = []
    for i in range(parse_following):
        curr_arg = actual_args[ind + i + 1]
        if argument_name[i] == '+':
            curr_arg = Int.decode(curr_arg)
        temp_res.append(curr_arg)

    if len(temp_res) == 1:
        return temp_res[0]
    else:
        return temp_res


def extract_args(
        actual_args: Tuple[bytes, ...],
        expected: Tuple[str, ...],
        error_on_unexpected: bool = True,
        left_from_first_unexpected: bool = True,
) -> Tuple[List, List]:
    """Parse argument values

    Extract from actual arguments which arguments exist and their
    numerical value.
    An argument can have parameters:
    - A numerical (Int) parameter is identified with +.
    - A non-numerical parameter is identified with a *.
    For example: '++limit' will translate as an argument with 2 int parameters.


    >>> extract_args((b'nx', b'ex', b'324', b'xx',), ('nx', 'xx', '+ex', 'keepttl'))
    [True, True, 324, False], None
    """

    results: List = [_default_value(key) for key in expected]
    left_args = []
    args_info: Dict[bytes, int] = {
        _encode_arg(k): (i, _count_params(k))
        for (i, k) in enumerate(expected)
    }
    i = 0
    while i < len(actual_args):
        found = False
        for key in args_info:
            if null_terminate(actual_args[i]).lower() == key:
                arg_position, parse_following = args_info[key]
                results[arg_position] = _parse_params(expected[arg_position], i, parse_following, actual_args)
                i += parse_following
                found = True
                break

        if not found:
            if error_on_unexpected:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            if left_from_first_unexpected:
                return results, actual_args[i:]
            left_args.append(actual_args[i])
        i += 1
    return results, left_args
