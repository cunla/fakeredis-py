from __future__ import annotations

import json
import os
from typing import Any, AnyStr

from fakeredis._helpers import asbytes
from fakeredis._typing import VersionType

_COMMAND_INFO: dict[bytes, list[Any]] | None = None
_COMMAND_SINCE: dict[bytes, VersionType] = {}


def _encode_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return obj.encode()
    if isinstance(obj, list):
        return [_encode_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {_encode_obj(k): _encode_obj(obj[k]) for k in obj}
    return obj


def _load_command_info() -> None:
    global _COMMAND_INFO
    if _COMMAND_INFO is None:
        with open(os.path.join(os.path.dirname(__file__), "..", "commands.json"), encoding="utf8") as f:
            info = _encode_obj(json.load(f))
        for cmd, cmd_info in info.items():
            since = cmd_info.pop()  # not part of the `COMMAND` reply
            if since:
                _COMMAND_SINCE[cmd] = tuple(since)
        _COMMAND_INFO = info


def is_command_in_version(cmd: bytes, version: VersionType) -> bool:
    """Compares only the parts `version` has, so `(8,)` has every 8.x command."""
    _load_command_info()
    since = _COMMAND_SINCE.get(cmd)
    return since is None or version >= since[: len(version)]


def get_all_commands_info() -> dict[bytes, list[Any]]:
    _load_command_info()
    return _COMMAND_INFO  # type: ignore[return-value]


def get_command_info(cmd: bytes) -> list[Any] | None:
    _load_command_info()
    if _COMMAND_INFO is None or cmd not in _COMMAND_INFO:
        return None
    return _COMMAND_INFO.get(cmd, None)


def is_write_command(cmd: bytes) -> bool:
    """Whether the command is flagged as writing to its keys."""
    info = get_command_info(cmd)
    return info is not None and b"write" in info[2]


def get_categories() -> list[bytes]:
    _load_command_info()
    if _COMMAND_INFO is None:
        return []
    categories = set()
    for info in _COMMAND_INFO.values():
        categories.update(info[6])
    categories = {asbytes(x[1:]) for x in categories}
    return list(categories)


def get_commands_by_category(_category: AnyStr) -> list[bytes]:
    _load_command_info()
    if _COMMAND_INFO is None:
        return []
    category = asbytes(_category)
    if category[0] != ord(b"@"):
        category = b"@" + category
    commands = []
    for cmd, info in _COMMAND_INFO.items():
        if category in info[6]:
            commands.append(cmd)
    return commands
