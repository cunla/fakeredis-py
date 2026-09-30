"""The Lua side of Redis Functions: libraries, the sandbox their code runs in, and calling a function.

Functions differ from EVAL scripts in ways a script can observe, and Redis 7 is followed on each:

- They run in a Lua interpreter of their own, so nothing an EVAL script does is visible to them.
- A library's code runs once, when it is loaded. The only global then is a cut-down `redis` table holding
  `register_function`, `log` and the version fields, and reading any other name is an error.
- A function runs with the script API minus `register_function`, and gets its keys and arguments as parameters rather
  than through KEYS and ARGV. Globals are read-only throughout.
- An error a function does not catch is reported with the function's name and the line it was raised on.
"""

from __future__ import annotations

import functools
import hashlib
import itertools
import json
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Callable

from fakeredis import _msgs as msgs
from fakeredis._helpers import SimpleError
from fakeredis._typing import ServerType, VersionType

# The flags a function can declare, in the order FUNCTION LIST reports them.
FUNCTION_FLAGS = (b"no-writes", b"allow-oom", b"allow-stale", b"no-cluster", b"allow-cross-slot-keys")

# The standard Lua globals a function can use. Everything else (print, io, require, ...) is out of reach, as in Redis.
_ALLOWED_GLOBALS = (
    "_VERSION",
    "assert",
    "collectgarbage",
    "coroutine",
    "error",
    "gcinfo",
    "getmetatable",
    "ipairs",
    "load",
    "loadstring",
    "math",
    "next",
    "pairs",
    "pcall",
    "rawequal",
    "rawget",
    "rawset",
    "select",
    "setmetatable",
    "string",
    "table",
    "tonumber",
    "tostring",
    "type",
    "unpack",
    "xpcall",
)

_VALID_NAME = re.compile(rb"[A-Za-z0-9_]+")
_ERROR_POSITION = re.compile(r"^user_function:(\d+): ")

# Runs once per interpreter. Its arguments are the name the API goes by (`redis`, or `server` on Valkey), the allowed
# standard globals, the Python callbacks and values behind the API, and whether register_function validates function
# names itself (Valkey checks them after the library has loaded instead).
_ENGINE_SOURCE = r"""
local api_name, allowed_globals, py, check_names = ...

local error, ipairs, pairs, select, setmetatable, tostring, type = error, ipairs, pairs, select, setmetatable, tostring, type
local find, lower = string.find, string.lower
local getinfo = debug.getinfo
local load, loadstring, setfenv = load, loadstring, setfenv

local function readonly()
  error("Attempt to modify a readonly table", 2)
end

local function missing(name)
  return "Script attempted to access nonexistent global variable '" .. tostring(name) .. "'"
end

-- A read-only view of `fields`. A strict view also refuses to read a field that is not there.
local function view(fields, strict)
  local index = fields
  if strict then
    index = function(_, name)
      local value = fields[name]
      if value == nil then
        error(missing(name), 2)
      end
      return value
    end
  end
  return setmetatable({}, {__index = index, __newindex = readonly, __metatable = false})
end

-- The functions registered so far by the library being loaded, or nil when no library is loading.
local registered = nil

local function fail(message)
  error(message, 0)
end

local function is_string(value)
  local kind = type(value)
  return kind == "string" or kind == "number"
end

local flag_names = {"no-writes", "allow-oom", "allow-stale", "no-cluster", "allow-cross-slot-keys"}

local function read_flags(flags)
  local result = {}
  local i = 1
  while flags[i] ~= nil do
    local flag = flags[i]
    if not is_string(flag) then
      return nil
    end
    flag = lower(tostring(flag))
    local known = false
    for _, name in ipairs(flag_names) do
      if name == flag then
        known = true
      end
    end
    if not known then
      return nil
    end
    result[flag] = true
    i = i + 1
  end
  return result
end

local function register_function(...)
  local register = api_name .. ".register_function"
  if registered == nil then
    fail(register .. " can only be called on FUNCTION LOAD command")
  end
  local count = select("#", ...)
  if count < 1 or count > 2 then
    fail("wrong number of arguments to " .. register)
  end
  local name, callback, description, flags
  if count == 1 then
    local args = ...
    if type(args) ~= "table" then
      fail("calling " .. register ..
        " with a single argument is only applicable to Lua table (representing named arguments).")
    end
    for key, value in pairs(args) do
      if type(key) ~= "string" then
        fail("named argument key given to " .. register .. " is not a string")
      end
      key = lower(key)
      if key == "function_name" then
        if not is_string(value) then
          fail("function_name argument given to " .. register .. " must be a string")
        end
        name = tostring(value)
      elseif key == "description" then
        if not is_string(value) then
          fail("description argument given to " .. register .. " must be a string")
        end
        description = tostring(value)
      elseif key == "callback" then
        if type(value) ~= "function" then
          fail("callback argument given to " .. register .. " must be a function")
        end
        callback = value
      elseif key == "flags" then
        if type(value) ~= "table" then
          fail("flags argument to " .. register .. " must be a table representing function flags")
        end
        flags = read_flags(value)
        if flags == nil then
          fail("unknown flag given")
        end
      else
        fail("unknown argument given to " .. register)
      end
    end
    if name == nil then
      fail(register .. " must get a function name argument")
    end
    if callback == nil then
      fail(register .. " must get a callback argument")
    end
  else
    local first, second = ...
    if not is_string(first) then
      fail("first argument to " .. register .. " must be a string")
    end
    if type(second) ~= "function" then
      fail("second argument to " .. register .. " must be a function")
    end
    name, callback = tostring(first), second
  end
  if check_names then
    if not find(name, "^[A-Za-z0-9_]+$") then
      fail("Library names can only contain letters, numbers, or underscores(_) and must be at least one character long")
    end
    for _, other in ipairs(registered) do
      if other.name == name then
        fail("Function already exists in the library")
      end
    end
  end
  registered[#registered + 1] = {name = name, callback = callback, description = description, flags = flags or {}}
end

local load_api = {
  register_function = register_function,
  log = py.log,
  REDIS_VERSION = py.version,
  REDIS_VERSION_NUM = py.version_num,
}
local run_api = {
  call = py.call,
  pcall = py.pcall,
  log = py.log,
  setresp = py.setresp,
  sha1hex = py.sha1hex,
  error_reply = function(message) return {err = message} end,
  status_reply = function(message) return {ok = message} end,
  set_repl = function() end,
  REDIS_VERSION = py.version,
  REDIS_VERSION_NUM = py.version_num,
  REPL_NONE = 0,
  REPL_AOF = 1,
  REPL_SLAVE = 2,
  REPL_REPLICA = 2,
  REPL_ALL = 3,
}
for name, level in pairs({LOG_DEBUG = 0, LOG_VERBOSE = 1, LOG_NOTICE = 2, LOG_WARNING = 3}) do
  load_api[name] = level
  run_api[name] = level
end

local load_globals = {redis = view(load_api, true)}
local run_globals = {redis = view(run_api, false), cjson = view(py.cjson, false)}
for _, name in ipairs(allowed_globals) do
  run_globals[name] = _G[name]
end
if api_name == "server" then
  load_globals.server = load_globals.redis
  run_globals.server = run_globals.redis
end

-- Every library shares one environment, which answers with the load-time globals while a library is loading.
local globals = run_globals
local env = setmetatable({}, {
  __index = function(_, name)
    local value = globals[name]
    if value == nil then
      error(missing(name), 2)
    end
    return value
  end,
  __newindex = readonly,
  __metatable = false,
})
run_globals._G = env

local engine = {}

function engine.compile(code)
  local chunk, err
  if setfenv then
    chunk, err = loadstring(code, "@user_function")
    if chunk then
      setfenv(chunk, env)
    end
  else
    chunk, err = load(code, "@user_function", "t", env)
  end
  return chunk, err
end

function engine.begin_load()
  registered = {}
  globals = load_globals
end

function engine.end_load()
  local result = registered
  registered = nil
  globals = run_globals
  return result
end

-- The line of library code that is running, for an error raised from Python on its behalf.
function engine.current_line()
  local level = 2
  while true do
    local info = getinfo(level, "Sl")
    if info == nil then
      return nil
    end
    if info.source == "@user_function" then
      return info.currentline
    end
    level = level + 1
  end
end

return engine
"""


class FunctionError(SimpleError):
    """An error raised from Python on behalf of running library code, with the line that code was on."""

    def __init__(self, value: str, line: int | None) -> None:
        super().__init__(value)
        self.line = line


@dataclass
class LuaFunction:
    name: bytes
    callback: Any
    description: bytes | None
    flags: list[bytes]


@dataclass
class FunctionLibrary:
    name: bytes
    code: bytes
    functions: dict[bytes, LuaFunction]


def parse_library_metadata(code: bytes) -> tuple[bytes, bytes]:
    """Read a library's first line, `#!<engine> name=<name>`, returning the library name and the code after that line.

    The code keeps the newline that ended the first line, so Lua counts lines from the top of the library, as Redis does.
    """
    if not code.startswith(b"#!"):
        raise SimpleError(msgs.FUNCTION_MISSING_METADATA_MSG)
    end = code.find(b"\n")
    if end == -1:
        raise SimpleError(msgs.FUNCTION_INVALID_METADATA_MSG)
    shebang, *options = code[:end].split()
    name = None
    for option in options:
        if option[:5].lower() != b"name=":
            raise SimpleError(msgs.FUNCTION_INVALID_METADATA_VALUE_MSG.format(option.decode("utf-8", "replace")))
        if name is not None:
            raise SimpleError(msgs.FUNCTION_NAME_GIVEN_TWICE_MSG)
        name = option[5:]
    if name is None:
        raise SimpleError(msgs.FUNCTION_NO_LIBRARY_NAME_MSG)
    if not _VALID_NAME.fullmatch(name):
        raise SimpleError(msgs.FUNCTION_INVALID_LIBRARY_NAME_MSG)
    engine = shebang[2:]
    if engine.lower() != b"lua":
        raise SimpleError(msgs.FUNCTION_ENGINE_NOT_FOUND_MSG.format(engine.decode("utf-8", "replace")))
    return name, code[end:]


def _lua_error_text(error: Exception) -> str:
    """The message of a Lua error, without the stack traceback lupa appends to it."""
    message = error.args[0] if error.args else ""
    if isinstance(message, bytes):
        message = message.decode("utf-8", "replace")
    return str(message).split("\nstack traceback:", 1)[0]


def _check_function_names_free(libraries: Iterable[FunctionLibrary], others: Iterable[FunctionLibrary]) -> None:
    taken = {name for other in others for name in other.functions}
    for library in libraries:
        for name in library.functions:
            if name in taken:
                raise SimpleError(msgs.FUNCTION_EXISTS_MSG.format(name.decode()))


def _sha1hex(*args: Any) -> bytes:
    if len(args) != 1:
        raise SimpleError(msgs.LUA_SHA1HEX_ARGS_MSG)
    value = args[0]
    if not isinstance(value, bytes):
        value = f"{value:.17g}".encode() if isinstance(value, (int, float)) else str(value).encode()
    return hashlib.sha1(value).hexdigest().encode()


class FunctionsEngine:
    """The function libraries of one server, and the Lua interpreter they run in."""

    def __init__(
        self,
        lua_module: Any,
        server_type: ServerType,
        version: VersionType,
        log: Callable[..., None],
        cjson_encode: Callable[..., bytes],
        cjson_decode: Callable[..., Any],
        cjson_null: Any,
    ) -> None:
        self._lua_module = lua_module
        self._server_type = server_type
        self._version = version
        self.libraries: dict[bytes, FunctionLibrary] = {}
        runtime = lua_module.LuaRuntime(encoding=None, unpack_returned_tuples=True)
        self.runtime = runtime
        # Filled in once the interpreter is set up: the callbacks shared with EVAL check no global was added since.
        self.expected_globals: set[Any] = set()
        # The client whose FCALL is running, and whether that function may write.
        self._caller: Any = None
        self._read_only = False

        major, minor, patch = (tuple(version) + (0, 0, 0))[:3]
        cjson = runtime.table_from(
            {
                b"encode": self._located(functools.partial(cjson_encode, runtime, self.expected_globals)),
                b"decode": self._located(functools.partial(cjson_decode, runtime, self.expected_globals)),
                b"null": cjson_null,
            }
        )
        api = runtime.table_from(
            {
                b"call": self._located(self._redis_call),
                b"pcall": self._redis_pcall,
                b"setresp": self._located(self._setresp),
                b"log": self._located(functools.partial(log, runtime, self.expected_globals, server_type)),
                b"sha1hex": self._located(_sha1hex),
                b"version": f"{major}.{minor}.{patch}".encode(),
                b"version_num": (major << 16) | (minor << 8) | patch,
                b"cjson": cjson,
            }
        )
        allowed = runtime.table_from([name.encode() for name in _ALLOWED_GLOBALS])
        api_name = b"server" if server_type == "valkey" else b"redis"
        self._lua = runtime.execute(_ENGINE_SOURCE, api_name, allowed, api, server_type != "valkey")
        self.expected_globals.update(runtime.globals().keys())

    def _located(self, func: Callable[..., Any]) -> Callable[..., Any]:
        """Wrap a callback so that an error it raises carries the line of library code that called it."""

        def wrapper(*args: Any) -> Any:
            try:
                return func(*args)
            except FunctionError:
                raise
            except SimpleError as error:
                raise FunctionError(error.value, self._lua.current_line()) from None

        return wrapper

    def _redis_call(self, *args: Any) -> Any:
        return self._caller._function_redis_call(self.runtime, self._read_only, *args)

    def _redis_pcall(self, *args: Any) -> Any:
        try:
            return self._redis_call(*args)
        except SimpleError as error:
            return self.runtime.table_from({b"err": error.value})

    def _setresp(self, *args: Any) -> None:
        self._caller._lua_setresp(self.runtime, self.expected_globals, *args)

    def find(self, name: bytes) -> LuaFunction | None:
        for library in self.libraries.values():
            function = library.functions.get(name)
            if function is not None:
                return function
        return None

    def load(self, code: bytes, replace: bool) -> bytes:
        name, body = parse_library_metadata(code)
        if name in self.libraries and not replace:
            raise SimpleError(msgs.FUNCTION_LIBRARY_EXISTS_MSG.format(name.decode()))
        library = self._create_library(name, code, body)
        _check_function_names_free([library], [other for other in self.libraries.values() if other.name != name])
        self.libraries[name] = library
        return name

    def delete(self, name: bytes) -> None:
        if self.libraries.pop(name, None) is None:
            raise SimpleError(msgs.FUNCTION_LIBRARY_NOT_FOUND_MSG)

    def dump(self) -> bytes:
        """Serialize every library.

        The payload has nothing in common with Redis' RDB-based one: it only has to be readable by FUNCTION RESTORE on a
        fakeredis server. It is JSON rather than a pickle because RESTORE takes it from the client.
        """
        body = json.dumps([library.code.decode("latin-1") for library in self.libraries.values()]).encode()
        return hashlib.sha1(body).digest() + body

    def restore(self, payload: bytes, policy: bytes) -> None:
        checksum, body = payload[:20], payload[20:]
        try:
            if hashlib.sha1(body).digest() != checksum:
                raise ValueError
            texts = json.loads(body)
            if not isinstance(texts, list) or not all(isinstance(text, str) for text in texts):
                raise ValueError
            codes = [text.encode("latin-1") for text in texts]
        except ValueError:
            raise SimpleError(msgs.FUNCTION_RESTORE_PAYLOAD_MSG) from None

        restored: dict[bytes, FunctionLibrary] = {}
        for code in codes:
            name, library_body = parse_library_metadata(code)
            if name in restored:
                raise SimpleError(msgs.FUNCTION_LIBRARY_EXISTS_MSG.format(name.decode()))
            library = self._create_library(name, code, library_body)
            _check_function_names_free([library], restored.values())
            restored[name] = library
        if policy == b"flush":
            self.libraries = restored
            return
        for name in restored:
            if name in self.libraries and policy != b"replace":
                raise SimpleError(msgs.FUNCTION_RESTORE_LIBRARY_EXISTS_MSG.format(name.decode()))
        kept = {name: library for name, library in self.libraries.items() if name not in restored}
        _check_function_names_free(restored.values(), kept.values())
        kept.update(restored)
        self.libraries = kept

    def _create_library(self, name: bytes, code: bytes, body: bytes) -> FunctionLibrary:
        """Compile a library and run its code, collecting the functions it registers."""
        chunk, error = self._lua.compile(body)
        if chunk is None:
            raise SimpleError(msgs.FUNCTION_COMPILE_ERROR_MSG.format(error.decode("utf-8", "replace")))
        self._lua.begin_load()
        try:
            chunk()
        except self._lua_module.LuaError as lua_error:
            raise SimpleError(msgs.FUNCTION_REGISTER_ERROR_MSG.format("ERR " + _lua_error_text(lua_error))) from None
        except SimpleError as simple_error:
            raise SimpleError(msgs.FUNCTION_REGISTER_ERROR_MSG.format(simple_error.value)) from None
        finally:
            registered = self._lua.end_load()

        functions: dict[bytes, LuaFunction] = {}
        for index in itertools.count(1):
            entry = registered[index]
            if entry is None:
                break
            function_name = entry[b"name"]
            if self._server_type == "valkey":
                # Valkey checks function names once the library has loaded, outside the registration error.
                if not _VALID_NAME.fullmatch(function_name):
                    raise SimpleError(msgs.VALKEY_FUNCTION_INVALID_NAME_MSG)
                if function_name in functions:
                    raise SimpleError(msgs.FUNCTION_DUPLICATE_IN_LIBRARY_MSG)
            flags = entry[b"flags"]
            functions[function_name] = LuaFunction(
                name=function_name,
                callback=entry[b"callback"],
                description=entry[b"description"],
                flags=[flag for flag in FUNCTION_FLAGS if flags[flag]],
            )
        if not functions:
            raise SimpleError(msgs.FUNCTION_NO_FUNCTIONS_MSG)
        return FunctionLibrary(name=name, code=code, functions=functions)

    def call(
        self, caller: Any, function: LuaFunction, keys: Sequence[bytes], args: Sequence[bytes], read_only: bool
    ) -> Any:
        """Run a function for `caller`, returning its raw Lua result."""
        self._caller, self._read_only = caller, read_only
        try:
            return function.callback(self.runtime.table_from(keys), self.runtime.table_from(args))
        except FunctionError as error:
            raise SimpleError(self._with_location(error.value, function.name, error.line)) from None
        except self._lua_module.LuaError as lua_error:
            message = _lua_error_text(lua_error)
            position = _ERROR_POSITION.match(message)
            line = int(position.group(1)) if position else None
            raise SimpleError(self._with_location("ERR " + message, function.name, line)) from None
        finally:
            self._caller = None

    def _with_location(self, message: str, function_name: bytes, line: int | None) -> str:
        """Say where an uncaught error was raised, as Redis does. Valkey 9 stopped naming the function."""
        if line is None:
            return message
        if self._server_type == "valkey" and self._version >= (9,):
            return f"{message} script: on @user_function:{line}."
        return f"{message} script: {function_name.decode('utf-8', 'replace')}, on @user_function:{line}."
