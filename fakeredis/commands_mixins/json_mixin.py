"""Command mixin for emulating `redis-py`'s JSON functionality."""

# Future Imports
from __future__ import annotations

# Standard Library Imports
import re
from functools import partial
from itertools import (
    chain,
    repeat,
    starmap,
)
from operator import (
    attrgetter,
    methodcaller,
)
from typing import (
    TYPE_CHECKING,
    Any,
    ForwardRef,
    Optional,
    Union,
)

# Third-Party Imports
from redis.commands.json._util import JsonType
from typing_extensions import (
    Literal,
    Protocol,
    runtime_checkable,
)

# Package-Level Imports
from fakeredis import _msgs as msgs
from fakeredis._commands import (
    CommandItem,
    Key,
    command,
)
from fakeredis._helpers import SimpleError

if TYPE_CHECKING:
    # Package-Level Imports
    from fakeredis._fakesocket import FakeSocket
else:
    FakeSocket = ForwardRef("JSONCommandsMixin")

try:
    # Third-Party Imports
    import orjson
    from jsonpath_ng import jsonpath
    from jsonpath_ng.ext import parse as parse_jsonpath
except ImportError:

    jsonpath = None

    def parse_jsonpath(*_: Any, **__: Any) -> Any:
        """Raise an error."""
        raise SimpleError("Optional JSON support not enabled!")

    class orjson:
        """Raises errors when the optional JSON support is not enabled."""

        loads = dumps = parse_jsonpath
        OPT_NON_STR_KEYS: int = 4


path_pattern: re.Pattern = re.compile(r"^((?<!\$)\.|(\$\.$))")


def format_jsonpath(path: Union[str, bytes]) -> str:
    """Format the supplied JSON path value."""
    if isinstance(path, bytes):
        path = path.decode()

    return path_pattern.sub("$", path)


@runtime_checkable
class RedisCompatibleJSONDecoder(Protocol):
    """Any object implementing a callable `decode` method that returns a
    `JsonType` object."""

    def decode(self, data: Union[str, bytes]) -> JsonType:
        """Deserialize the supplied string to its native Python equivalent."""
        ...


@runtime_checkable
class RedisCompatibleJSONEncoder(Protocol):
    """Any object implementing a callable `encode` method that returns
    `bytes`."""

    def encode(self, obj: Any) -> Union[str, bytes]:
        """Serialize the supplied object to a JSON-encoded string or byte-
        string."""
        ...


class JSONObject:
    """Argument converter for JSON objects."""

    DECODE_ERROR = msgs.WRONGTYPE_MSG
    ENCODE_ERROR = msgs.WRONGTYPE_MSG

    @classmethod
    def valid(cls, value: Any) -> bool:
        """Determine if the supplied value is a "valid" `JSONObject`."""
        raise NotImplementedError

    @classmethod
    def decode(cls, value: bytes) -> Any:
        """Deserialize the supplied bytes into a valid Python object."""
        # Third-Party Imports
        import orjson

        return orjson.loads(value)

    @classmethod
    def encode(cls, value: Any) -> bytes:
        """Serialize the supplied Python object into a valid, JSON-formatted
        byte-encoded string."""
        raise NotImplementedError


class JSONCommandsMixin:
    """`CommandsMixin` for enabling RedisJSON compatibility in `fakeredis`."""

    def __init__(
        self: FakeSocket,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        pass

    @command(
        name="JSON.DEL",
        fixed=(Key(),),
        repeat=(bytes,),
    )
    def json_del(
        self: FakeSocket,
        key: CommandItem,
        path: Optional[bytes] = None,
    ) -> int:
        """Delete the JSON value stored at key `key` under `path`.

        For more information see `JSON.DEL
        <https://redis.io/commands/json.del>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    # `forget` is an alias for `delete`
    json_forget = json_del

    @command(
        name="JSON.GET",
        fixed=(Key(),),
        repeat=(bytes,),
    )
    def json_get(
        self: FakeSocket,
        name: CommandItem,
        *args: bytes,
    ) -> bytes:
        """Get the object stored as a JSON value at key `name`.

        `args` is zero or more paths, and defaults to root path
        ``no_escape` is a boolean flag to add no_escape option to get
        non-ascii characters

        For more information see `JSON.GET <https://redis.io/commands/json.get>`_.
        """
        no_escape, args = (
            bool(b"noescape" in args),
            tuple(
                map(
                    parse_jsonpath,
                    (format_jsonpath(arg) for arg in args if arg != b"noescape"),
                )
            ),
        )

        if no_escape:
            raise NotImplementedError

        path_count = len(args)
        cached_value = orjson.loads(name.value)

        callers = starmap(
            methodcaller,
            zip(
                repeat("find", path_count),
                repeat(cached_value, path_count),
            ),
        )
        path_values = tuple(
            map(
                attrgetter("value"),
                chain.from_iterable(
                    (
                        caller(path)
                        for caller, path in zip(
                            callers,
                            args,
                        )
                    )
                ),
            )
        )

        if len(args) == 1:
            path_values = path_values[0]

        return orjson.dumps(path_values, option=orjson.OPT_NON_STR_KEYS)

    @command(
        name="JSON.SET",
        fixed=(Key(), bytes, JSONObject),
        repeat=(bytes,),
    )
    def json_set(
        self: FakeSocket,
        name: CommandItem,
        path: bytes,
        obj: JsonType,
        flag: Optional[Literal[b"NX", b"XX"]] = None,
    ) -> bool:
        """Set the JSON value at key `name` under the `path` to `obj`.

        if `flag` is b"NX", set `value` only if it does not exist.
        if `flag` is b"XX", set `value` only if it exists.

        For the purpose of using this within a pipeline, this command is also
        aliased to JSON.SET.

        For more information see `JSON.SET <https://redis.io/commands/json.set>`_.
        """
        cached_value, path = (
            orjson.loads(name.value or b"null"),
            parse_jsonpath(path.decode()),
        )

        if not flag or flag == b"NX":
            setter = partial(path.update_or_create, cached_value)
        elif flag == b"XX":
            setter = partial(path.update, cached_value)
        else:
            raise SimpleError(f"Unknown or unsupported `JSON.SET` flag: {flag}")

        cached_value, name.value = (
            name.value,
            orjson.dumps(setter(obj)),
        )

        return name.value != cached_value

    @command(
        name="JSON.MGET",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_mget(
        self: FakeSocket,
        keys: list[CommandItem],  # This seems like the wrong type 🤔
        path: bytes,
    ) -> list[JsonType]:
        """Get the objects stored as a JSON values under `path`. `keys` is a
        list of one or more keys.

        For more information see `JSON.MGET
        <https://redis.io/commands/json.mget>`_.
        """
        raise NotImplementedError

    @command(
        name="JSON.RESP",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_resp(
        self: FakeSocket,
        name: CommandItem,
        path: Optional[bytes] = None,
    ) -> Any:
        """Return the JSON value under `path` at key `name`.

        For more information see `JSON.RESP
        <https://redis.io/commands/json.resp>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    @command(
        name="JSON.TYPE",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_type(
        self: FakeSocket,
        name: CommandItem,
        path: Optional[bytes] = None,
    ) -> list[str]:
        """Get the type of the JSON value under `path` from key `name`.

        For more information see `JSON.TYPE
        <https://redis.io/commands/json.type>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    @command(
        name="JSON.CLEAR",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_clear(
        self: FakeSocket,
        name: CommandItem,
        path: Optional[bytes] = None,
    ) -> int:
        """Empty arrays and objects (to have zero slots/keys without deleting
        the array/object).

        Return the count of cleared paths (ignoring non-array and non-objects
        paths).

        For more information see `JSON.CLEAR <https://redis.io/commands/json.clear>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    @command(
        name="JSON.DEBUG",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_debug(
        self: FakeSocket,
        subcommand: CommandItem,
        key: Optional[str] = None,
        path: Optional[bytes] = None,
    ) -> Union[int, list[str]]:
        """Return the memory usage in bytes of a value under `path` from key
        `name`.

        For more information see `JSON.DEBUG
        <https://redis.io/commands/json.debug>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    @command(
        name="JSON.ARRLEN",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_arrlen(
        self: FakeSocket,
        name: CommandItem,
        path: Optional[bytes] = None,
    ) -> list[Union[int, None]]:
        """Return the length of the array JSON value under `path` at key`name`.

        For more information see `JSON.ARRLEN
        <https://redis.io/commands/json.arrlen>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    @command(
        name="JSON.ARRPOP",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_arrpop(
        self: FakeSocket,
        name: CommandItem,
        path: Optional[bytes] = None,
        index: Optional[int] = -1,
    ) -> list[Union[str, None]]:

        """Pop the element at `index` in the array JSON value under `path` at
        key `name`.

        For more information see `JSON.ARRPOP
        <https://redis.io/commands/json.arrpop>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    @command(
        name="JSON.OBJLEN",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_objlen(
        self: FakeSocket,
        name: CommandItem,
        path: Optional[bytes] = None,
    ) -> int:
        """Return the length of the dictionary JSON value under `path` at key
        `name`.

        For more information see `JSON.OBJLEN
        <https://redis.io/commands/json.objlen>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    @command(
        name="JSON.STRLEN",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_strlen(
        self: FakeSocket,
        name: CommandItem,
        path: Optional[bytes] = None,
    ) -> list[Union[int, None]]:
        """Return the length of the string JSON value under `path` at key
        `name`.

        For more information see `JSON.STRLEN
        <https://redis.io/commands/json.strlen>`_.
        """
        raise NotImplementedError

    @command(
        name="JSON.TOGGLE",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_toggle(
        self: FakeSocket,
        name: CommandItem,
        path: Optional[bytes] = None,
    ) -> Union[bool, list[Optional[int]]]:
        """Toggle boolean value under `path` at key `name`. returning the new
        value.

        For more information see `JSON.TOGGLE
        <https://redis.io/commands/json.toggle>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    @command(
        name="JSON.ARRTRIM",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_arrtrim(
        self: FakeSocket,
        name: CommandItem,
        path: bytes,
        start: int,
        stop: int,
    ) -> list[Union[int, None]]:
        """Trim the array JSON value under `path` at key `name` to the
        inclusive range given by `start` and `stop`.

        For more information see `JSON.ARRTRIM
        <https://redis.io/commands/json.arrtrim>`_.
        """
        raise NotImplementedError

    @command(
        name="JSON.OBJKEYS",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_objkeys(
        self: FakeSocket,
        name: CommandItem,
        path: Optional[bytes] = None,
    ) -> list[Union[list[str], None]]:
        """Return the key names in the dictionary JSON value under `path` at
        key `name`.

        For more information see `JSON.OBJKEYS
        <https://redis.io/commands/json.objkeys>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    @command(
        name="JSON.ARRINDEX",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_arrindex(
        self: FakeSocket,
        name: CommandItem,
        path: bytes,
        scalar: int,
        start: Optional[int] = 0,
        stop: Optional[int] = -1,
    ) -> list[Union[int, None]]:
        """Return the index of `scalar` in the JSON array under `path` at key
        `name`.

        The search can be limited using the optional inclusive `start`
        and exclusive `stop` indices.

        For more information see `JSON.ARRINDEX <https://redis.io/commands/json.arrindex>`_.
        """
        raise NotImplementedError

    @command(
        name="JSON.ARRAPPEND",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_arrappend(
        self: FakeSocket,
        name: CommandItem,
        path: Optional[bytes] = None,
        *args: list[JsonType],
    ) -> list[Union[int, None]]:
        """Append the objects `args` to the array under the `path` in key
        `name`.

        For more information see `JSON.ARRAPPEND
        <https://redis.io/commands/json.arrappend>`_..
        """
        # path = path or b"$"
        raise NotImplementedError

    @command(
        name="JSON.ARRINSERT",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_arrinsert(
        self: FakeSocket,
        name: CommandItem,
        path: bytes,
        index: int,
        *args: JsonType,
    ) -> list[Union[int, None]]:
        """Insert the objects `args` to the array at index `index` under the
        `path` in key `name`.

        For more information see `JSON.ARRINSERT
        <https://redis.io/commands/json.arrinsert>`_.
        """
        raise NotImplementedError

    @command(
        name="JSON.NUMINCRBY",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_numincrby(
        self: FakeSocket,
        name: CommandItem,
        path: bytes,
        number: int,
    ) -> str:
        """Increment the numeric (integer or floating point) JSON value under
        `path` at key `name` by the provided `number`.

        For more information see `JSON.NUMINCRBY
        <https://redis.io/commands/json.numincrby>`_.
        """
        raise NotImplementedError

    @command(
        name="JSON.STRAPPEND",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_strappend(
        self: FakeSocket,
        name: CommandItem,
        value: str,
        path: Optional[int] = None,
    ) -> Union[int, list[Optional[int]]]:
        """Append to the string JSON value. If two options are specified after
        the key name, the path is determined to be the first. If a single
        option is passed, then the root_path (i.e JSONPath.root_path()) is
        used.

        For more information see `JSON.STRAPPEND
        <https://redis.io/commands/json.strappend>`_.
        """
        # path = path or b"$"
        raise NotImplementedError

    # <editor-fold desc="# Deprecated Methods ...">

    @command(
        name="JSON.NUMMULTBY",
        fixed=(Key(), bytes),
        repeat=(bytes,),
    )
    def json_nummultby(
        self: FakeSocket,
        name: CommandItem,
        path: bytes,
        number: int,
    ) -> str:
        """Multiply the numeric (integer or floating point) JSON value under
        `path` at key `name` with the provided `number`.

        For more information see `JSON.NUMMULTBY
        <https://redis.io/commands/json.nummultby>`_.
        """
        raise NotImplementedError

    # </editor-fold desc="# Deprecated Methods ...">
