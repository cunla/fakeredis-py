from . import _msgs as msgs
from ._commands import Int
from ._helpers import casematch, SimpleError


def _encode_arg(s: str):
    ind = 0
    while s[ind] == '+' or s[ind] == '*':
        ind += 1
    return s[ind:].encode()


def _default_value(s: str):
    ind = 0
    while s[ind] == '+' or s[ind] == '*':
        ind += 1
    if ind == 0:
        return False
    elif ind == 1:
        return None
    else:
        return [None] * ind


def _number_of_args(s: str):
    res = 0
    while s[res] == '+' or s[res] == '*':
        res += 1
    return res


def _parse_params(argument_name: str, ind: int, parse_following: int, actual_args: tuple[bytes, ...]):
    if parse_following == 0:
        return True
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
        actual_args: tuple[bytes, ...],
        expected: tuple[str, ...],
        error_on_non_param: bool = True,
) -> tuple[list[int | bool | None, ...], list[bytes, ...]]:
    """Parse argument values

    Extract from actual arguments which arguments exist and their
    numerical value. Numerical arguments are identified by starting with a +.

    >>> extract_args((b'nx', b'ex', b'324', b'xx',), ('nx', 'xx', '+ex', 'keepttl'))
    [True, True, 324, False], None
    """

    results = [_default_value(key) for key in expected]
    left_args = []
    args_info: dict[bytes, int] = {
        _encode_arg(k): (i, _number_of_args(k))
        for (i, k) in enumerate(expected)
    }
    i = 0
    while i < len(actual_args):
        found = False
        for key in args_info:
            if casematch(actual_args[i], key):
                arg_position, parse_following = args_info[key]
                results[arg_position] = _parse_params(expected[arg_position], i, parse_following, actual_args)
                i += 1 + parse_following
                found = True
                break
        if not found:
            if error_on_non_param:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            else:
                left_args.append(actual_args[i])
                i += 1
    return results, left_args
