"""Command mixin for emulating `redis-py`'s JSON functionality."""

from __future__ import annotations

import copy
import itertools
import json
import struct
from functools import lru_cache
from json import JSONDecodeError
from typing import Any, Callable, ClassVar

from jsonpath_ng import JSONPath, Root
from jsonpath_ng.exceptions import JsonPathParserError
from jsonpath_ng.ext import parse

from fakeredis import _helpers as helpers
from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import CommandItem, Float, Int, Key, command, delete_keys
from fakeredis._helpers import SimpleString
from fakeredis._typing import JsonType, ServerType
from fakeredis.commands_mixins._mixin_base import CommandsMixinBase
from fakeredis.model import ZSet


def _key_not_found(server_type: ServerType) -> helpers.SimpleError:
    """The error a JSON command answers with when the key does not exist.

    Dragonfly reports the plain `no such key`, where RedisJSON spells the operation out.
    """
    return helpers.SimpleError(msgs.NO_KEY_MSG if server_type == "dragonfly" else msgs.JSON_KEY_NOT_FOUND)


# Marks a JSON.ARRPOP match that is not an array, which the servers report differently from
# an array with nothing left to pop.
_NOT_AN_ARRAY = object()


def _path_is_legacy(path_str: bytes | str | None) -> bool:
    """Whether `path_str` is a legacy path (`.a`) rather than a JSONPath (`$.a`).

    An omitted path counts as legacy: the reply is shaped for the single root match.
    """
    if path_str is None:
        return True
    if isinstance(path_str, str):
        path_str = path_str.encode()
    return not path_str.startswith(b"$")


def _format_path(path: bytes | str) -> str:
    path_str = path.decode() if isinstance(path, bytes) else path
    if path_str == ".":
        return "$"
    elif path_str.startswith("."):
        return "$" + path_str
    elif path_str.startswith("$"):
        return path_str
    else:
        return "$." + path_str


@lru_cache(maxsize=64)
def _parse_jsonpath(path: str | bytes, server_type: ServerType = "redis") -> JSONPath:
    if server_type == "dragonfly" and "[?" in (path.decode() if isinstance(path, bytes) else path):
        # Dragonfly's JSONPath has no filter expressions: `$.a[?(@.b>1)]` is a syntax error,
        # while wildcards and recursive descent parse as they do on RedisJSON.
        raise helpers.SimpleError(msgs.SYNTAX_ERROR_MSG)
    path_str: str = _format_path(path)
    try:
        return parse(path_str)
    except JsonPathParserError:
        raise helpers.SimpleError(msgs.JSON_PATH_DOES_NOT_EXIST.format(path_str))


def _path_is_root(path: JSONPath) -> bool:
    return path == Root()  # type: ignore


def _dict_deep_merge(source: JsonType, destination: dict[str, Any]) -> dict[str, Any]:
    """Deep merge of two dictionaries"""
    if not isinstance(source, dict):
        return destination
    for key, value in source.items():
        if value is None and key in destination:
            del destination[key]
        elif isinstance(value, dict):
            node = destination.setdefault(key, {})
            _dict_deep_merge(value, node)
        else:
            destination[key] = value

    return destination


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
            raise helpers.SimpleError(cls.DECODE_ERROR)

    @classmethod
    def encode(cls, value: Any) -> bytes | None:
        """Serialize the supplied Python object into a valid, JSON-formatted byte-encoded string."""
        return json.dumps(value, default=str).encode() if value is not None else None


def _quantize_fp16(value: float) -> float:
    return struct.unpack("<e", struct.pack("<e", value))[0]  # type: ignore[no-any-return]


def _quantize_fp32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]  # type: ignore[no-any-return]


def _quantize_bf16(value: float) -> float:
    bits: int = struct.unpack("<I", struct.pack("<f", value))[0]
    # Round float32 to bfloat16 (top 16 bits), using round-to-nearest-even.
    rounded = (bits + 0x7FFF + ((bits >> 16) & 1)) >> 16
    if (rounded & 0x7F80) == 0x7F80:  # rounded to infinity => out of bfloat16 range
        raise OverflowError
    return struct.unpack("<f", struct.pack("<I", (rounded << 16) & 0xFFFFFFFF))[0]  # type: ignore[no-any-return]


def _quantize_fp64(value: float) -> float:
    return value


# FPHA type token -> (name used in error messages, quantizer)
_FPHA_TYPES: dict[bytes, tuple[str, Callable[[float], float]]] = {
    b"fp16": ("F16", _quantize_fp16),
    b"bf16": ("BF16", _quantize_bf16),
    b"fp32": ("F32", _quantize_fp32),
    b"fp64": ("F64", _quantize_fp64),
}


def _shortest_float_in_type(quantized: float, quantizer: Callable[[float], float]) -> float:
    """Return the double parsed from the shortest decimal string that round-trips through the FP type.

    This matches how real redis prints FPHA values: the stored FP16/BF16/FP32 value is rendered with the fewest digits
    that still parse back to the same value in that type (e.g. FP16(0.1) prints as 0.1).
    """
    for precision in range(1, 18):
        candidate = float(f"{quantized:.{precision}g}")
        try:
            if quantizer(candidate) == quantized:
                return candidate
        except OverflowError:
            continue
    return quantized


def _number_token_positions(raw: bytes) -> list[tuple[int, int]]:
    """Scan a JSON document for number tokens, returning (line, column-after-token) for each.

    Positions are 1-based, matching the `value out of range ... at line L column C` errors of real redis.
    """
    positions = []
    line, col = 1, 1
    i, n = 0, len(raw)
    in_string = False
    while i < n:
        c = raw[i]
        if in_string:
            if c == ord("\\"):
                i += 1
                col += 1
            elif c == ord('"'):
                in_string = False
            i += 1
            col += 1
        elif c == ord('"'):
            in_string = True
            i += 1
            col += 1
        elif c == ord("\n"):
            line += 1
            col = 1
            i += 1
        elif c == ord("-") or ord("0") <= c <= ord("9"):
            while i < n and raw[i] in b"0123456789+-.eE":
                i += 1
                col += 1
            positions.append((line, col))
        else:
            i += 1
            col += 1
    return positions


def _apply_fpha(value: JsonType, fpha_type: bytes, raw: bytes) -> JsonType:
    """Convert homogeneous numeric arrays in `value` to the requested floating-point type.

    Every number in an array whose elements are all numbers is quantized to the FP type; an out-of-range number raises
    the same error as real redis, pointing at its position in `raw`.
    """
    type_name, quantizer = _FPHA_TYPES[fpha_type]
    # Index of the current number in document order, used to locate the offending token on error.
    number_index = itertools.count()

    def convert(item: float) -> float:
        index = next(number_index)
        try:
            quantized = quantizer(float(item))
        except OverflowError:
            line_col = _number_token_positions(raw)[index]
            raise helpers.SimpleError(msgs.JSON_VALUE_OUT_OF_RANGE_MSG.format(type_name, *line_col))
        return _shortest_float_in_type(quantized, quantizer)

    def walk(node: JsonType) -> JsonType:
        if type(node) in (int, float):
            next(number_index)
            return node
        if isinstance(node, list):
            if len(node) > 0 and all(type(item) in (int, float) for item in node):
                return [convert(item) for item in node]
            return [walk(item) for item in node]
        if isinstance(node, dict):
            return {k: walk(v) for k, v in node.items()}
        return node

    return walk(value)


def _json_write_iterate(
    method: Callable[[JsonType], tuple[JsonType | None, Any, bool]],
    key: CommandItem,
    path_str: str | bytes,
    allow_result_none: bool = False,
    server_type: ServerType = "redis",
) -> JsonType:
    """Implement json.* write commands.
    Iterate over values with path_str in key and running method to get new value for path item.
    """
    if key.value is None:
        raise _key_not_found(server_type)
    path = _parse_jsonpath(path_str, server_type)
    found_matches = path.find(key.value)
    if len(found_matches) == 0:
        raise helpers.SimpleError(msgs.JSON_PATH_NOT_FOUND_OR_NOT_STRING.format(path_str))

    curr_value = copy.deepcopy(key.value)
    res: list[JsonType] = []
    for item in found_matches:
        new_value, res_val, update = method(item.value)
        if update:
            curr_value = item.full_path.update(curr_value, new_value)
        res.append(res_val)

    key.update(curr_value)

    if len(path_str) > 1 and path_str[0] == ord(b"."):
        if allow_result_none:
            return res[-1]
        else:
            return next(x for x in reversed(res) if x is not None)
    if len(res) == 1 and (path_str[0] != ord(b"$") or path_str == b"."):
        return res[0]
    return res


def _json_read_iterate(
    method: Callable[[JsonType], Any | None],
    key: CommandItem,
    *args: Any,
    error_on_zero_matches: bool = False,
    server_type: ServerType = "redis",
) -> list[Any | None] | Any | None:
    path_str = args[0] if len(args) > 0 else "$"
    if key.value is None:
        if path_str[0] == ord(b"$"):
            raise _key_not_found(server_type)
        else:
            return None

    path = _parse_jsonpath(path_str, server_type)
    found_matches = path.find(key.value)
    if error_on_zero_matches and len(found_matches) == 0 and path_str[0] != ord(b"$"):
        raise helpers.SimpleError(msgs.JSON_PATH_NOT_FOUND_OR_NOT_STRING.format(path_str))
    res = [method(item.value) for item in found_matches]

    if len(path_str) > 1 and path_str[0] == ord(b"."):
        return res[0] if len(res) > 0 else None
    if len(res) == 1 and (len(args) == 0 or path_str[0] == ord(b".")):
        return res[0]

    return res


class JSONCommandsMixin(CommandsMixinBase):
    """`CommandsMixin` for enabling RedisJSON compatibility in `fakeredis`."""

    TYPES_EMPTY_VAL_DICT: ClassVar[dict[type[object], Any]] = {
        dict: {},
        int: 0,
        float: 0.0,
        list: [],
    }
    TYPE_NAMES: ClassVar[dict[type[object], bytes]] = {
        dict: b"object",
        int: b"integer",
        float: b"number",
        bytes: b"string",
        list: b"array",
        set: b"set",
        str: b"string",
        bool: b"boolean",
        type(None): b"null",
        ZSet: b"zset",
    }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._db: helpers.Database

    def _legacy_path_reply(self, res: Any, legacy: bool) -> list[Any | None] | Any | None:
        """Shape the reply to a legacy path the way the server under test shapes it.

        Under RESP3 dragonfly answers a legacy path with the one-element array it answers a
        JSONPath with -- `JSON.STRLEN j .a` is `[5]`, not the `5` RedisJSON sends. Under RESP2,
        for a JSONPath, and for a null -- which is what a path that matched nothing answers
        with -- the two agree.
        """
        if res is None or not legacy or self.server_type != "dragonfly" or self._client_info.protocol_version != 3:
            return res
        return [res]

    def _read_iterate(
        self,
        method: Callable[[JsonType], Any | None],
        key: CommandItem,
        *args: Any,
        error_on_zero_matches: bool = False,
    ) -> list[Any | None] | Any | None:
        res = _json_read_iterate(
            method, key, *args, error_on_zero_matches=error_on_zero_matches, server_type=self.server_type
        )
        return self._legacy_path_reply(res, _path_is_legacy(args[0] if len(args) > 0 else None))

    def _write_iterate(
        self,
        method: Callable[[JsonType], tuple[JsonType | None, Any, bool]],
        key: CommandItem,
        path_str: str | bytes,
        allow_result_none: bool = False,
        legacy: bool | None = None,
    ) -> list[Any | None] | Any | None:
        """`legacy` overrides the path form for a command that defaults an omitted path to `$`."""
        res = _json_write_iterate(
            method, key, path_str, allow_result_none=allow_result_none, server_type=self.server_type
        )
        return self._legacy_path_reply(res, _path_is_legacy(path_str) if legacy is None else legacy)

    def _get_single(
        self,
        key: CommandItem,
        path_str: str | bytes,
        always_return_list: bool = False,
        empty_list_as_none: bool = False,
    ) -> Any:
        path: JSONPath = _parse_jsonpath(path_str, self.server_type)
        path_value = path.find(key.value)
        val = [i.value for i in path_value]
        if empty_list_as_none and len(val) == 0:
            return None
        elif len(val) == 1 and not always_return_list:
            return val[0]
        return val

    @command(
        name=["JSON.DEL", "JSON.FORGET"],
        fixed=(Key(),),
        repeat=(bytes,),
        flags=msgs.FLAG_LEAVE_EMPTY_VAL,
    )
    def json_del(self, key: CommandItem, path_str: bytes) -> int:
        if key.value is None:
            return 0

        path = _parse_jsonpath(path_str, self.server_type)
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

    def _json_set(self, key: CommandItem, path_str: bytes, value: JsonType, *args: Any) -> SimpleString | None:
        path = _parse_jsonpath(path_str, self.server_type)
        if key.value is not None and (type(key.value) is not dict) and not _path_is_root(path):
            raise helpers.SimpleError(msgs.JSON_WRONG_REDIS_TYPE)
        old_value_list = path.find(key.value)
        (nx, xx), _ = extract_args(args, ("nx", "xx"))
        if xx and nx:
            raise helpers.SimpleError(msgs.SYNTAX_ERROR_MSG)
        old_value = old_value_list[0].value if len(old_value_list) > 0 else None
        if (nx and old_value is not None) or (xx and old_value is None):
            return None
        new_value = path.update_or_create(key.value, value)
        key.update(new_value)
        return helpers.OK

    @command(
        name="JSON.SET",
        fixed=(Key(), bytes, bytes),
        repeat=(bytes,),
        flags=msgs.FLAG_LEAVE_EMPTY_VAL + msgs.FLAG_DO_NOT_CREATE,
    )
    def json_set(self, key: CommandItem, path_str: bytes, value_bytes: bytes, *args: bytes) -> SimpleString | None:
        """Set the JSON value at key `name` under the `path` to `obj`.

        For more information see `JSON.SET <https://redis.io/commands/json.set>`_.
        """
        fpha: bytes | None = None
        left_args: list[bytes] = []
        i = 0
        while i < len(args):
            if helpers.casematch(args[i], b"fpha"):
                if i + 1 >= len(args):
                    raise helpers.SimpleError(msgs.WRONG_ARGS_MSG6.format("json.set"))
                fpha = args[i + 1].lower()
                i += 2
            else:
                left_args.append(args[i])
                i += 1
        if fpha is not None:
            # The FPHA argument was added in redis 8.8
            if self.version < (8, 8) or self.server_type != "redis":
                raise helpers.SimpleError(msgs.SYNTAX_ERROR_MSG)
            if fpha not in _FPHA_TYPES:
                raise helpers.SimpleError(msgs.JSON_INVALID_FPHA_TYPE_MSG)
        value = JSONObject.decode(value_bytes)
        if fpha is not None:
            value = _apply_fpha(value, fpha, value_bytes)
        return self._json_set(key, path_str, value, *left_args)

    @command(name="JSON.GET", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_get(self, key: CommandItem, *args: bytes) -> bytes | None:
        if key.value is None:
            return None
        paths = [arg for arg in args if not helpers.casematch(b"noescape", arg)]
        no_wrapping_array = len(paths) == 1 and paths[0][0] == ord(b".")

        formatted_paths: list[str] = [_format_path(arg) for arg in args if not helpers.casematch(b"noescape", arg)]
        path_values = [self._get_single(key, path, len(formatted_paths) > 1) for path in formatted_paths]

        # Emulate the behavior of `redis-py`:
        #   - if only one path was supplied => return a single value
        #   - if more than one path was specified => return one value for each specified path
        if no_wrapping_array or (len(path_values) == 1 and isinstance(path_values[0], list)):
            return JSONObject.encode(path_values[0])
        if len(path_values) == 1:
            return JSONObject.encode(path_values)
        return JSONObject.encode(dict(zip(formatted_paths, path_values)))

    @command(name="JSON.MGET", fixed=(bytes,), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_mget(self, *args: bytes) -> list[bytes | None]:
        if len(args) < 2:
            raise helpers.SimpleError(msgs.WRONG_ARGS_MSG6.format("json.mget"))
        path_str = args[-1]
        keys = [CommandItem(key, self._db, item=self._db.get(key), default=[]) for key in args[:-1]]

        result = [JSONObject.encode(self._get_single(key, path_str, empty_list_as_none=True)) for key in keys]
        return result

    @command(name="JSON.TOGGLE", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_toggle(self, key: CommandItem, *args: bytes) -> list[Any] | bytes | bool | None:
        if key.value is None:
            raise _key_not_found(self.server_type)
        path_str = args[0] if len(args) > 0 else b"$"
        path = _parse_jsonpath(path_str, self.server_type)
        found_matches = path.find(key.value)

        curr_value = copy.deepcopy(key.value)
        res: list[bool | None] = []
        for item in found_matches:
            if type(item.value) is bool:
                curr_value = item.full_path.update(curr_value, not item.value)
                res.append(not item.value)
            else:
                res.append(None)
        if all(x is None for x in res):
            raise _key_not_found(self.server_type)
        key.update(curr_value)

        if self.server_type == "dragonfly":
            # Dragonfly answers a legacy path with the JSON text of the new value and a
            # JSONPath with 0/1, where RedisJSON answers with booleans either way.
            if _path_is_legacy(path_str):
                return self._legacy_path_reply(JSONObject.encode(res[0]), True)
            toggled: list[Any] = [int(x) if type(x) is bool else x for x in res]
            return toggled

        if len(res) == 1 and (len(args) == 0 or (len(args) == 1 and args[0] == b".")):
            return res[0]

        return res

    @command(name="JSON.CLEAR", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_clear(self, key: CommandItem, *args: bytes) -> int:
        if key.value is None:
            raise _key_not_found(self.server_type)
        path_str: bytes = args[0] if len(args) > 0 else b"$"
        path = _parse_jsonpath(path_str, self.server_type)
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

    @command(name="JSON.STRAPPEND", fixed=(Key(), bytes), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_strappend(
        self, key: CommandItem, path_str: bytes, *args: bytes
    ) -> list[JsonType | None] | JsonType | None:
        if len(args) == 0:
            raise helpers.SimpleError(msgs.WRONG_ARGS_MSG6.format("json.strappend"))
        addition = JSONObject.decode(args[0])

        def strappend(val: JsonType) -> tuple[JsonType | None, int | None, bool]:
            if type(val) is str:
                new_value = val + addition
                return new_value, len(new_value), True
            else:
                return None, None, False

        return self._write_iterate(strappend, key, path_str)

    @command(name="JSON.ARRAPPEND", fixed=(Key(), bytes), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_arrappend(
        self, key: CommandItem, path_str: bytes, *args: bytes
    ) -> list[JsonType | None] | JsonType | None:
        if len(args) == 0:
            raise helpers.SimpleError(msgs.WRONG_ARGS_MSG6.format("json.arrappend"))

        addition = [JSONObject.decode(item) for item in args]

        def arrappend(val: JsonType) -> tuple[JsonType | None, int | None, bool]:
            if type(val) is list:
                new_value = val + addition
                return new_value, len(new_value), True
            else:
                return None, None, False

        return self._write_iterate(arrappend, key, path_str)

    @command(name="JSON.ARRINSERT", fixed=(Key(), bytes, Int), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_arrinsert(
        self, key: CommandItem, path_str: bytes, index: int, *args: bytes
    ) -> list[JsonType | None] | JsonType | None:
        if len(args) == 0:
            raise helpers.SimpleError(msgs.WRONG_ARGS_MSG6.format("json.arrinsert"))

        addition = [JSONObject.decode(item) for item in args]

        def arrinsert(val: JsonType) -> tuple[JsonType | None, int | None, bool]:
            if type(val) is list:
                new_value = val[:index] + addition + val[index:]
                return new_value, len(new_value), True
            else:
                return None, None, False

        return self._write_iterate(arrinsert, key, path_str)

    @command(name="JSON.ARRPOP", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_arrpop(self, key: CommandItem, *args: bytes) -> JsonType:
        path_str: bytes | str = args[0] if len(args) > 0 else "$"
        index = Int.decode(args[1]) if len(args) > 1 else -1

        def arrpop(val: JsonType) -> tuple[JsonType, bytes | None, bool]:
            if type(val) is list and len(val) > 0:
                ind = index if index < len(val) else -1
                res = val.pop(ind)
                return val, JSONObject.encode(res), True
            # An empty array has nothing to pop; a match that is no array at all is reported
            # differently again, so the two are told apart below rather than here.
            return None, (None if type(val) is list else _NOT_AN_ARRAY), False  # type:ignore[return-value]

        res: Any = _json_write_iterate(arrpop, key, path_str, allow_result_none=True, server_type=self.server_type)
        if isinstance(res, list):
            return [None if item is _NOT_AN_ARRAY else item for item in res]
        if res is _NOT_AN_ARRAY:
            # Flattening a legacy path down to one value, dragonfly reports a match that is no
            # array as the JSON text `null`, where RedisJSON sends a null reply.
            res = b"null" if self.server_type == "dragonfly" else None
        # An omitted path is a legacy path here, whatever the `$` default says.
        return self._legacy_path_reply(res, _path_is_legacy(args[0] if len(args) > 0 else None))

    @command(name="JSON.ARRTRIM", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_arrtrim(self, key: CommandItem, *args: bytes) -> JsonType:
        path_str: bytes = args[0] if len(args) > 0 else b"$"
        start = Int.decode(args[1]) if len(args) > 1 else 0
        stop = Int.decode(args[2]) if len(args) > 2 else None

        def arrtrim(val: JsonType) -> tuple[JsonType | None, int | None, bool]:
            if type(val) is list:
                start_ind = min(start, len(val))
                stop_ind = len(val) if stop is None or stop == -1 else stop + 1
                if stop_ind < 0:
                    stop_ind = len(val) + stop_ind + 1
                new_val = val[start_ind:stop_ind]
                return new_val, len(new_val), True
            else:
                return None, None, False

        return self._write_iterate(arrtrim, key, path_str, legacy=_path_is_legacy(args[0] if len(args) > 0 else None))

    @command(
        name="JSON.NUMINCRBY",
        fixed=(Key(), bytes, Float),
        repeat=(bytes,),
        flags=msgs.FLAG_LEAVE_EMPTY_VAL + msgs.FLAG_SKIP_CONVERT_TO_RESP2,
    )
    def json_numincrby(
        self, key: CommandItem, path_str: bytes, inc_by: float, *_: bytes
    ) -> list[JsonType | None] | JsonType | None:
        def numincrby(val: JsonType | None) -> tuple[JsonType | None, float | None, bool]:
            if val is not None and type(val) in {int, float}:
                new_value = val + inc_by  # type: ignore
                return new_value, new_value, True
            else:
                return None, None, False

        return self._number_reply(_json_write_iterate(numincrby, key, path_str, server_type=self.server_type))

    @command(
        name="JSON.NUMMULTBY",
        fixed=(Key(), bytes, Float),
        repeat=(bytes,),
        flags=msgs.FLAG_LEAVE_EMPTY_VAL + msgs.FLAG_SKIP_CONVERT_TO_RESP2,
    )
    def json_nummultby(self, key: CommandItem, path_str: bytes, mult_by: float, *_: bytes) -> JsonType:
        def nummultby(val: JsonType | None) -> tuple[JsonType | None, float | None, bool]:
            if type(val) in {int, float}:
                new_value = val * mult_by  # type: ignore
                return new_value, new_value, True
            else:
                return None, None, False

        return self._number_reply(_json_write_iterate(nummultby, key, path_str, server_type=self.server_type))

    # Read operations
    @command(name="JSON.ARRINDEX", fixed=(Key(), bytes, bytes), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_arrindex(self, key: CommandItem, path_str: bytes, encoded_value: bytes, *args: bytes) -> JsonType:
        start = max(0, Int.decode(args[0]) if len(args) > 0 else 0)
        end = Int.decode(args[1]) if len(args) > 1 else -1
        end = end if end > 0 else -1
        expected_value = JSONObject.decode(encoded_value)

        def check_index(value: JsonType) -> int | None:
            if type(value) is not list:
                return None
            try:
                ind = next(
                    filter(
                        lambda x: x[1] == expected_value and type(x[1]) is type(expected_value),
                        enumerate(value[start:end]),
                    )
                )
                return ind[0] + start
            except StopIteration:
                return -1

        return self._read_iterate(check_index, key, path_str, error_on_zero_matches=True)

    @command(name="JSON.STRLEN", fixed=(Key(),), repeat=(bytes,))
    def json_strlen(self, key: CommandItem, *args: bytes) -> list[int | None] | int | None:
        return self._read_iterate(lambda val: len(val) if type(val) is str else None, key, *args)

    @command(name="JSON.ARRLEN", fixed=(Key(),), repeat=(bytes,))
    def json_arrlen(self, key: CommandItem, *args: bytes) -> list[int | None] | int | None:
        return self._read_iterate(lambda val: len(val) if type(val) is list else None, key, *args)

    @command(name="JSON.OBJLEN", fixed=(Key(),), repeat=(bytes,))
    def json_objlen(self, key: CommandItem, *args: bytes) -> list[int | None] | int | None:
        return self._read_iterate(lambda val: len(val) if type(val) is dict else None, key, *args)

    def _resp3_wrapping_list(self, res: Any, wrap_list: bool = False) -> Any:
        if self._client_info.protocol_version == 2:
            return res
        if isinstance(res, list) and not wrap_list:
            return res
        return [res]

    def _number_reply(self, res: JsonType) -> list[Any | None] | Any | None:
        """Shape a JSON.NUMINCRBY / JSON.NUMMULTBY reply.

        RedisJSON wraps the new value in an array under RESP3. Dragonfly does not, and
        under RESP2 sends the JSON text of the value rather than the value itself.
        """
        if self.server_type != "dragonfly":
            return self._resp3_wrapping_list(res)
        if self._client_info.protocol_version == 2:
            return JSONObject.encode(res)
        return res

    @command(name="JSON.TYPE", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_type(self, key: CommandItem, *args: bytes) -> list[bytes | None] | bytes | None:
        res = _json_read_iterate(
            lambda val: self.TYPE_NAMES.get(type(val), None), key, *args, server_type=self.server_type
        )
        if self.server_type == "dragonfly":
            if self._client_info.protocol_version == 3 and isinstance(res, list):
                # Dragonfly wraps every match of a JSONPath in an array of its own, where
                # RedisJSON wraps the whole reply in one.
                wrapped: list[Any] = [[item] for item in res]
                return wrapped
            return self._legacy_path_reply(res, _path_is_legacy(args[0] if len(args) > 0 else None))
        return self._resp3_wrapping_list(res, wrap_list=True)  # type:ignore

    @command(name="JSON.OBJKEYS", fixed=(Key(),), repeat=(bytes,))
    def json_objkeys(self, key: CommandItem, *args: bytes) -> list[bytes | None] | bytes | None:
        return self._read_iterate(lambda val: [i.encode() for i in val] if type(val) is dict else None, key, *args)

    @command(name="JSON.MSET", fixed=(), repeat=(Key(), bytes, JSONObject), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_mset(self, *args: Any) -> SimpleString:
        if len(args) < 3 or len(args) % 3 != 0:
            raise helpers.SimpleError(msgs.WRONG_ARGS_MSG6.format("json.mset"))
        for i in range(0, len(args), 3):
            key, path_str, value = args[i], args[i + 1], args[i + 2]
            self._json_set(key, path_str, value)
        return helpers.OK

    @command(name="JSON.MERGE", fixed=(Key(), bytes, JSONObject), repeat=(), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def json_merge(self, key: CommandItem, path_str: bytes, value: JsonType) -> SimpleString:
        path: JSONPath = _parse_jsonpath(path_str, self.server_type)
        if key.value is not None and (type(key.value) is not dict) and not _path_is_root(path):
            raise helpers.SimpleError(msgs.JSON_WRONG_REDIS_TYPE)
        matching = path.find(key.value)
        for item in matching:
            prev_value = item.value if item is not None else {}
            _dict_deep_merge(value, prev_value)
        if len(matching) > 0:
            key.updated()
        return helpers.OK
