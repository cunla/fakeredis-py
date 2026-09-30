"""RESP helpers: splitting a request into command and arguments, and checking and shaping replies."""

from __future__ import annotations

import itertools
from typing import Any

from fakeredis._command_args_parsing import Float
from fakeredis._commands import COMMANDS_WITH_SUB
from fakeredis._helpers import NoResponse, SimpleError, SimpleString, decode_command_bytes
from fakeredis._typing import ServerType

_VALID_RESPONSE_TYPES_RESP2 = (bytes, SimpleString, SimpleError, float, int, list)
_VALID_RESPONSE_TYPES_RESP3 = (bytes, SimpleString, SimpleError, float, int, list, dict, str)


def convert_to_resp2(val: Any, server_type: ServerType = "redis", keep_doubles: bool = False) -> Any:
    if isinstance(val, str):
        return val.encode()
    if isinstance(val, float):
        if keep_doubles:
            return val
        if server_type == "dragonfly":
            return Float.encode_shortest(val)
        return Float.encode(val, humanfriendly=False)
    if isinstance(val, dict):
        result = list(itertools.chain(*val.items()))
        return [convert_to_resp2(item, server_type, keep_doubles) for item in result]
    if isinstance(val, (list, tuple)):
        return [convert_to_resp2(item, server_type, keep_doubles) for item in val]
    return val


def extract_command(fields: list[bytes]) -> tuple[Any, list[Any]]:
    """Extracts the command and command arguments from a list of `bytes` fields.

    :param fields: A list of `bytes` fields containing the command and command arguments.
    :return: A tuple of the command and command arguments.

    Example:
        ```
        fields = [b'GET', b'key1']
        result = extract_command(fields)
        print(result) # ('GET', ['key1'])
        ```
    """
    cmd = decode_command_bytes(fields[0])
    if cmd in COMMANDS_WITH_SUB and len(fields) >= 2:
        cmd += " " + decode_command_bytes(fields[1])
        cmd_arguments = fields[2:]
    else:
        cmd_arguments = fields[1:]
    return cmd, cmd_arguments


def valid_response_type(value: Any, protocol_version: int, nested: bool = False) -> bool:
    if isinstance(value, NoResponse) and not nested:
        return True
    allowed_types = _VALID_RESPONSE_TYPES_RESP2 if protocol_version == 2 else _VALID_RESPONSE_TYPES_RESP3
    if value is not None and not isinstance(value, allowed_types):
        return False
    return not (
        isinstance(value, list) and any(not valid_response_type(item, protocol_version, True) for item in value)
    )
