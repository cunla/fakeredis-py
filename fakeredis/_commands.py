"""The command registry: the `@command` decorator, the `Signature` it records for each command, and `Key` markers.

Argument converters live in `_command_args_parsing.py`, and `CommandItem` in `_core/_database.py`.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Any, Callable

from . import _msgs as msgs
from ._command_args_parsing import RedisType
from ._core import CommandItem, Database
from ._helpers import SimpleError
from ._typing import ServerType, VersionType

SUPPORTED_COMMANDS: dict[str, Signature] = {}  # Dictionary of supported commands name => Signature
COMMANDS_WITH_SUB: set[str] = set()  # Commands with sub-commands


class Key:
    """Marker to indicate that argument in signature is a key"""

    UNSPECIFIED = object()

    def __init__(self, type_: type[Any] | None = None, missing_return: Any = UNSPECIFIED) -> None:
        self.type_ = type_
        self.missing_return = missing_return


class Signature:
    def __init__(
        self,
        name: str,
        func_name: str,
        fixed: tuple[type[RedisType | bytes]],
        repeat: tuple[type[RedisType | bytes]] = (),  # type:ignore
        args: tuple[str] = (),  # type:ignore
        flags: str = "",
        server_types: Collection[ServerType] = ("redis", "valkey", "dragonfly", "kividb"),
    ):
        self.name = name
        self.func_name = func_name
        self.fixed = fixed
        self.repeat = repeat
        self.flags = set(flags)
        self.command_args = args
        self.server_types: set[ServerType] = set(server_types)

    def check_arity(self, args: Sequence[Any], version: VersionType) -> None:
        if len(args) == len(self.fixed):
            return
        delta = len(args) - len(self.fixed)
        if delta < 0 or not self.repeat:
            msg = msgs.WRONG_ARGS_MSG6.format(self.name)
            raise SimpleError(msg)
        if delta % len(self.repeat) != 0:
            msg = msgs.WRONG_ARGS_MSG7 if version >= (7,) else msgs.WRONG_ARGS_MSG6.format(self.name)
            raise SimpleError(msg)

    def apply(
        self, args: Sequence[Any], db: Database, version: VersionType
    ) -> tuple[Any] | tuple[list[Any], list[CommandItem]]:
        """Returns a tuple, which is either:
        - transformed args and a dict of CommandItems; or
        - a single containing a short-circuit return value
        """
        self.check_arity(args, version)

        types = list(self.fixed)
        types.extend([self.repeat[i % len(self.repeat)] for i in range(len(args) - len(types))])

        args_list = list(args)
        # First pass: convert/validate non-keys, and short-circuit on missing keys
        for i, (arg, type_) in enumerate(zip(args_list, types)):
            if isinstance(type_, Key):
                if type_.missing_return is not Key.UNSPECIFIED and arg not in db:
                    return (type_.missing_return,)
            elif type_ is not bytes:
                args_list[i] = type_.decode(
                    args_list[i],
                )

        # Second pass: read keys and check their types
        command_items: list[CommandItem] = []
        for i, (arg, type_) in enumerate(zip(args_list, types)):
            if isinstance(type_, Key):
                item = db.get(arg)
                default = None
                if type_.type_ is not None and item is not None and type(item.value) is not type_.type_:
                    raise SimpleError(msgs.WRONGTYPE_MSG)
                if (
                    msgs.FLAG_DO_NOT_CREATE not in self.flags
                    and type_.type_ is not None
                    and item is None
                    and type_.type_ is not bytes
                ):
                    default = type_.type_()
                args_list[i] = CommandItem(arg, db, item, default=default)
                command_items.append(args_list[i])

        return args_list, command_items


def command(*args, **kwargs) -> Callable:  # type:ignore
    def create_signature(func: Callable[..., Any], cmd_name: str) -> None:
        if " " in cmd_name:
            COMMANDS_WITH_SUB.add(cmd_name.split(" ")[0])
        SUPPORTED_COMMANDS[cmd_name] = Signature(cmd_name, func.__name__, *args, **kwargs)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cmd_names = kwargs.pop("name", func.__name__)
        if isinstance(cmd_names, list):  # Support for alias commands
            for cmd_name in cmd_names:
                create_signature(func, cmd_name.lower())
        elif isinstance(cmd_names, str):
            create_signature(func, cmd_names.lower())
        else:
            raise TypeError("command name should be a string or list of strings")
        return func

    return decorator
