"""Command mixin for emulating `redis-py`'s JSON functionality."""

# Future Imports
from __future__ import annotations

import copy
# Standard Library Imports
import json
import re
from json import JSONDecodeError
from typing import Any, Optional, Union

from jsonpath_ng import Root, JSONPath
from jsonpath_ng.ext import parse
from redis.commands.json.commands import JsonType

from fakeredis import _helpers as helpers, _msgs as msgs
from fakeredis._commands import Key, command, delete_keys, CommandItem
from fakeredis._helpers import SimpleError, casematch

path_pattern: re.Pattern = re.compile(r"^((?<!\$)\.|(\$\.$))")


def _parse_jsonpath(path: Union[str, bytes]):
    """Format the supplied JSON path value."""
    if isinstance(path, bytes):
        path = path.decode()
    re_path = path_pattern.sub("$", path)
    return parse(re_path)


def _path_is_root(path: JSONPath) -> bool:
    return path == Root()


def _format_path(path) -> str:
    if isinstance(path, bytes):
        path = path.decode()
    return path_pattern.sub("$", path)


class JSONObject:
    """Argument converter for JSON objects."""

    DECODE_ERROR = msgs.JSON_WRONG_REDIS_TYPE
    ENCODE_ERROR = msgs.JSON_WRONG_REDIS_TYPE

    @classmethod
    def decode(cls, value: bytes) -> Any:
        """Deserialize the supplied bytes into a valid Python object."""
        try:
            return json.loads(value)
        except JSONDecodeError:
            raise SimpleError(cls.DECODE_ERROR)

    @classmethod
    def encode(cls, value: Any) -> bytes:
        """Serialize the supplied Python object into a valid, JSON-formatted
        byte-encoded string."""
        return json.dumps(value, default=str).encode()


class JSONCommandsMixin:
    """`CommandsMixin` for enabling RedisJSON compatibility in `fakeredis`."""

    TYPES_EMPTY_VAL_DICT = {
        dict: {},
        int: 0,
        float: 0.0,
        list: [],
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @command(name=["JSON.DEL", "JSON.FORGET"], fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_del(self, key, path_str) -> int:
        """Delete the JSON value stored at key `key` under `path`.

        For more information see `JSON.DEL
        <https://redis.io/commands/json.del>`_.
        """
        if key.value is None:
            return 0

        path = _parse_jsonpath(path_str)
        if _path_is_root(path):
            delete_keys(key)
            return 1
        curr_value = copy.deepcopy(key.value)

        found_matches = path.find(curr_value)
        res = 0
        while len(found_matches) > 0:
            item = found_matches[0]
            curr_value = item.full_path.filter(lambda _: True, curr_value)
            res += 1
            found_matches = path.find(curr_value)

        key.update(curr_value)
        return res

    @staticmethod
    def _get_single(key, path_str: str, always_return_list: bool = False, empty_list_as_none: bool = False):
        path = _parse_jsonpath(path_str)
        path_value = path.find(key.value)
        val = [i.value for i in path_value]
        if empty_list_as_none and len(val) == 0:
            val = None
        elif len(val) == 1 and not always_return_list:
            val = val[0]
        return val

    @command(name="JSON.GET", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_get(self, key, *args) -> bytes:
        """Get the object stored as a JSON value at key `name`.

        `args` is zero or more paths, and defaults to root path
        ``no_escape` is a boolean flag to add no_escape option to get
        non-ascii characters

        For more information see `JSON.GET <https://redis.io/commands/json.get>`_.
        """
        paths = [arg for arg in args if not casematch(b'noescape', arg)]
        no_wrapping_array = (len(paths) == 1 and paths[0] == b'.')

        formatted_paths = [
            _format_path(arg) for arg in args
            if not casematch(b'noescape', arg)
        ]
        path_values = [self._get_single(key, path, len(formatted_paths) > 1) for path in formatted_paths]

        # Emulate the behavior of `redis-py`:
        #   - if only one path was supplied => return a single value
        #   - if more than one path was specified => return one value for each specified path
        if (no_wrapping_array or
                (len(path_values) == 1 and isinstance(path_values[0], list))):
            return JSONObject.encode(path_values[0])
        if len(path_values) == 1:
            return JSONObject.encode(path_values)
        return JSONObject.encode(dict(zip(formatted_paths, path_values)))

    @command(name="JSON.SET", fixed=(Key(), bytes, JSONObject), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_set(self, key, path_str: bytes, value: JsonType, *args) -> Optional[helpers.SimpleString]:
        """Set the JSON value at key `name` under the `path` to `obj`.

        if `flag` is b"NX", set `value` only if it does not exist.
        if `flag` is b"XX", set `value` only if it exists.

        For the purpose of using this within a pipeline, this command is also
        aliased to JSON.SET.

        For more information see `JSON.SET <https://redis.io/commands/json.set>`_.
        """
        path = _parse_jsonpath(path_str)
        if key.value is not None and (type(key.value) is not dict) and not _path_is_root(path):
            raise SimpleError(msgs.JSON_WRONG_REDIS_TYPE)
        old_value = path.find(key.value)
        nx, xx = False, False
        i = 0
        while i < len(args):
            if casematch(args[i], b'nx'):
                nx = True
                i += 1
            elif casematch(args[i], b'xx'):
                xx = True
                i += 1
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if xx and nx:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if (nx and old_value) or (xx and not old_value):
            return None
        new_value = path.update_or_create(key.value, value)
        key.update(new_value)

        return helpers.OK

    @command(name="JSON.MGET", fixed=(bytes,), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_mget(self, *args):
        if len(args) < 2:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format('json.mget'))
        path_str = args[-1]
        keys = [CommandItem(key, self._db, item=self._db.get(key), default=[])
                for key in args[:-1]]

        result = [self._get_single(key, path_str, empty_list_as_none=True) for key in keys]
        return result

    @command(name="JSON.CLEAR", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_clear(self, key, *args, ):
        if key.value is None:
            raise SimpleError(msgs.JSON_KEY_NOT_FOUND)
        path_str = args[0] if len(args) > 0 else '$'
        path = _parse_jsonpath(path_str)
        found_matches = path.find(key.value)
        curr_value = copy.deepcopy(key.value)
        res = 0
        for item in found_matches:
            new_val = self.TYPES_EMPTY_VAL_DICT.get(type(item.value), None)
            if new_val is not None:
                curr_value = item.full_path.update(curr_value, new_val)
                res += 1

        key.update(curr_value)
        return res

    @command(name="JSON.STRLEN", fixed=(Key(),), repeat=(bytes,))
    def json_strlen(self, key, *args):
        """Returns the length of the JSON String at path in key

        """
        if key.value is None:
            return None
        path_str = args[0] if len(args) > 0 else '$'
        path = _parse_jsonpath(path_str)
        found_matches = path.find(key.value)
        res = list()
        for item in found_matches:
            res.append(len(item.value) if type(item.value) == str else None)

        if len(res) == 1 and (len(args) == 0 or (len(args) == 1 and args[0] == b'.')):
            return res[0]

        return res

    @command(name="JSON.TOGGLE", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_toggle(self, key, *args):
        """Toggle a Boolean value stored at path

        Returns an array of integer replies for each path, the new value (0 if
        false or 1 if true), or nil for JSON values matching the path that are
        not Boolean.

        """
        if key.value is None:
            raise SimpleError(msgs.JSON_KEY_NOT_FOUND)
        path_str = args[0] if len(args) > 0 else '$'
        path = _parse_jsonpath(path_str)
        found_matches = path.find(key.value)

        curr_value = copy.deepcopy(key.value)
        res = list()
        for item in found_matches:
            if type(item.value) == bool:
                curr_value = item.full_path.update(curr_value, not item.value)
                res.append(not item.value)
            else:
                res.append(None)
        if all([x is None for x in res]):
            raise SimpleError(msgs.JSON_KEY_NOT_FOUND)
        key.update(curr_value)

        if len(res) == 1 and (len(args) == 0 or (len(args) == 1 and args[0] == b'.')):
            return res[0]

        return res
