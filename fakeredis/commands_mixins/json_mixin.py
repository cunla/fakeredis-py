"""Command mixin for emulating `redis-py`'s JSON functionality."""

# Future Imports
from __future__ import annotations

# Standard Library Imports
import json
import re
from functools import partial
from itertools import chain, filterfalse
from json import JSONDecodeError
from operator import attrgetter, methodcaller
from typing import Any, Optional, Union

from redis.commands.json.commands import JsonType
from typing_extensions import Literal

from fakeredis import _helpers as helpers, _msgs as msgs
from fakeredis._commands import CommandItem, Key, command
from fakeredis._helpers import SimpleError

try:
    from jsonpath_ng import jsonpath
    from jsonpath_ng.ext import parse


    def parse_jsonpath(path: Union[str, bytes]) -> str:
        """Format the supplied JSON path value."""
        if isinstance(path, bytes):
            path = path.decode()
        re_path = path_pattern.sub("$", path)
        return parse(re_path)

except ImportError:

    jsonpath = None


    def parse_jsonpath(*_: Any, **__: Any) -> Any:
        """Raise an error."""
        raise helpers.SimpleError("Optional JSON support not enabled!")

path_pattern: re.Pattern = re.compile(r"^((?<!\$)\.|(\$\.$))")
is_no_escape = partial(helpers.casematch, b"noescape")
is_not_no_escape = partial(filterfalse, is_no_escape)


class JSONObject:
    """Argument converter for JSON objects."""

    DECODE_ERROR = msgs.JSON_WRONG_REDIS_TYPE
    ENCODE_ERROR = msgs.JSON_WRONG_REDIS_TYPE

    @classmethod
    def decode(cls, value: bytes) -> Any:
        """Deserialize the supplied bytes into a valid Python object."""
        try:
            return json.loads(value or b"null")
        except JSONDecodeError as e:
            raise SimpleError(cls.DECODE_ERROR)

    @classmethod
    def encode(cls, value: Any) -> bytes:
        """Serialize the supplied Python object into a valid, JSON-formatted
        byte-encoded string."""
        return json.dumps(value, default=str).encode()


class JSONCommandsMixin:
    """`CommandsMixin` for enabling RedisJSON compatibility in `fakeredis`."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @command(name=["JSON.DEL", "JSON.FORGET"], fixed=(Key(),), repeat=(bytes,), )
    def json_del(self, key: CommandItem, path: Optional[bytes] = None, ) -> int:
        """Delete the JSON value stored at key `key` under `path`.

        For more information see `JSON.DEL
        <https://redis.io/commands/json.del>`_.
        """
        cached_value = json.loads(key.value or b"null")

        if cached_value is None:
            return 0

        if path != "$":
            raise NotImplementedError("Path-based key-value deletion not yet supported!")

        key.value = None
        key.writeback()

        return 1

    @command(name="JSON.GET", fixed=(Key(),), repeat=(bytes,), )
    def json_get(self, name: CommandItem, *args: bytes, ) -> bytes:
        """Get the object stored as a JSON value at key `name`.

        `args` is zero or more paths, and defaults to root path
        ``no_escape` is a boolean flag to add no_escape option to get
        non-ascii characters

        For more information see `JSON.GET <https://redis.io/commands/json.get>`_.
        """
        # Check the cache for the requested key
        cached_value = json.loads(name.value or b"null")

        # Return early if the requested key is not in the cache
        if not cached_value:
            return b"null"

        # Format the specified paths that are *not* the literal
        # byte-string b"noescape" so that they can be properly
        # parsed by `jsonpath_ng`
        args = [is_not_no_escape(arg) for arg in args]

        # Parse the sanitized paths into `jsonpath.JSONPath` objects
        paths = tuple(map(parse_jsonpath, args))

        find = methodcaller("find", cached_value)

        # Call the `find` method of the parsed paths, with
        # the cached value as the target JSON object to search
        resolved_paths = chain.from_iterable(map(find, paths))

        # Extract the resolved `value` from each of the search "results"
        path_values = tuple(map(attrgetter("value"), resolved_paths))

        # Emulate the behavior of `redis-py`:
        #   - if only one path was supplied,
        #     return a single value
        #   - if more than one path was specified,
        #     return one value for each specified path

        if len(paths) == 1:
            path_values = path_values[0]

        # Ensure the returned data is properly serialized and encoded
        return json.dumps(path_values).encode()

    @command(
        name="JSON.SET",
        fixed=(Key(), bytes, JSONObject),
        repeat=(bytes,),
    )
    def json_set(
            self,
            name: CommandItem,
            path: bytes,
            obj: JsonType,
            flag: Optional[Literal[b"NX", b"XX"]] = None,
    ) -> Optional[helpers.SimpleString]:
        """Set the JSON value at key `name` under the `path` to `obj`.

        if `flag` is b"NX", set `value` only if it does not exist.
        if `flag` is b"XX", set `value` only if it exists.

        For the purpose of using this within a pipeline, this command is also
        aliased to JSON.SET.

        For more information see `JSON.SET <https://redis.io/commands/json.set>`_.
        """
        cached_value, path = (
            json.loads(name.value or b"null"),
            parse_jsonpath(path),
        )

        setter = partial(path.update_or_create, cached_value)

        if flag and flag not in (b"NX", b"XX"):
            raise helpers.SimpleError(f"Unknown or unsupported `JSON.SET` flag: {flag}")
        elif (flag == b"NX" and path.find(cached_value)) or (
                flag == b"XX" and not path.find(cached_value)
        ):
            setter = lambda *_, **__: cached_value

        cached_value, name.value = (
            name.value,
            json.dumps(setter(obj)).encode(),
        )

        name.writeback()

        return helpers.OK if cached_value != name.value else None
