import functools
import hashlib
import itertools
import logging

from fakeredis import _msgs as msgs
from fakeredis._commands import command, Int
from fakeredis._helpers import SimpleError, SimpleString, casenorm, OK

LOGGER = logging.getLogger('fakeredis')
REDIS_LOG_LEVELS = {
    b'LOG_DEBUG': 0,
    b'LOG_VERBOSE': 1,
    b'LOG_NOTICE': 2,
    b'LOG_WARNING': 3
}
REDIS_LOG_LEVELS_TO_LOGGING = {
    0: logging.DEBUG,
    1: logging.INFO,
    2: logging.INFO,
    3: logging.WARNING
}


def _ensure_str(s, encoding, replaceerr):
    if isinstance(s, bytes):
        res = s.decode(encoding=encoding, errors=replaceerr)
    else:
        res = str(s).encode(encoding=encoding, errors=replaceerr)
    return res


def _check_for_lua_globals(lua_runtime, expected_globals):
    unexpected_globals = set(lua_runtime.globals().keys()) - expected_globals
    if len(unexpected_globals) > 0:
        unexpected = [_ensure_str(var, 'utf-8', 'replace') for var in unexpected_globals]
        raise SimpleError(msgs.GLOBAL_VARIABLE_MSG.format(", ".join(unexpected)))


def _lua_redis_log(lua_runtime, expected_globals, lvl, *args):
    _check_for_lua_globals(lua_runtime, expected_globals)
    if len(args) < 1:
        raise SimpleError(msgs.REQUIRES_MORE_ARGS_MSG.format("redis.log()", "two"))
    if lvl not in REDIS_LOG_LEVELS_TO_LOGGING.keys():
        raise SimpleError(msgs.LOG_INVALID_DEBUG_LEVEL_MSG)
    msg = ' '.join([x.decode('utf-8')
                    if isinstance(x, bytes) else str(x)
                    for x in args if not isinstance(x, bool)])
    LOGGER.log(REDIS_LOG_LEVELS_TO_LOGGING[lvl], msg)


class ScriptingCommandsMixin:

    # Script commands
    # script debug and script kill will probably not be supported

    def __init__(self, *args, **kwargs):
        super(ScriptingCommandsMixin, self).__init__(*args, **kwargs)
        # Maps SHA1 to script source
        self.script_cache = {}

    def _convert_redis_arg(self, lua_runtime, value):
        # Type checks are exact to avoid issues like bool being a subclass of int.
        if type(value) is bytes:
            return value
        elif type(value) in {int, float}:
            return '{:.17g}'.format(value).encode()
        else:
            # TODO: add the context
            msg = msgs.LUA_COMMAND_ARG_MSG6 if self.version < 7 else msgs.LUA_COMMAND_ARG_MSG
            raise SimpleError(msg)

    def _convert_redis_result(self, lua_runtime, result):
        if isinstance(result, (bytes, int)):
            return result
        elif isinstance(result, SimpleString):
            return lua_runtime.table_from({b"ok": result.value})
        elif result is None:
            return False
        elif isinstance(result, list):
            converted = [
                self._convert_redis_result(lua_runtime, item)
                for item in result
            ]
            return lua_runtime.table_from(converted)
        elif isinstance(result, SimpleError):
            raise result
        else:
            raise RuntimeError("Unexpected return type from redis: {}".format(type(result)))

    def _convert_lua_result(self, result, nested=True):
        from lupa import lua_type
        if lua_type(result) == 'table':
            for key in (b'ok', b'err'):
                if key in result:
                    msg = self._convert_lua_result(result[key])
                    if not isinstance(msg, bytes):
                        raise SimpleError(msgs.LUA_WRONG_NUMBER_ARGS_MSG)
                    if key == b'ok':
                        return SimpleString(msg)
                    elif nested:
                        return SimpleError(msg.decode('utf-8', 'replace'))
                    else:
                        raise SimpleError(msg.decode('utf-8', 'replace'))
            # Convert Lua tables into lists, starting from index 1, mimicking the behavior of StrictRedis.
            result_list = []
            for index in itertools.count(1):
                if index not in result:
                    break
                item = result[index]
                result_list.append(self._convert_lua_result(item))
            return result_list
        elif isinstance(result, str):
            return result.encode()
        elif isinstance(result, float):
            return int(result)
        elif isinstance(result, bool):
            return 1 if result else None
        return result

    def _lua_redis_call(self, lua_runtime, expected_globals, op, *args):
        # Check if we've set any global variables before making any change.
        _check_for_lua_globals(lua_runtime, expected_globals)
        func, sig = self._name_to_func(self._encode_command(op))
        args = [self._convert_redis_arg(lua_runtime, arg) for arg in args]
        result = self._run_command(func, sig, args, True)
        return self._convert_redis_result(lua_runtime, result)

    def _lua_redis_pcall(self, lua_runtime, expected_globals, op, *args):
        try:
            return self._lua_redis_call(lua_runtime, expected_globals, op, *args)
        except Exception as ex:
            return lua_runtime.table_from({b"err": str(ex)})

    @command((bytes, Int), (bytes,), flags='s')
    def eval(self, script, numkeys, *keys_and_args):
        from lupa import LuaError, LuaRuntime, as_attrgetter

        if numkeys > len(keys_and_args):
            raise SimpleError(msgs.TOO_MANY_KEYS_MSG)
        if numkeys < 0:
            raise SimpleError(msgs.NEGATIVE_KEYS_MSG)
        sha1 = hashlib.sha1(script).hexdigest().encode()
        self.script_cache[sha1] = script
        lua_runtime = LuaRuntime(encoding=None, unpack_returned_tuples=True)

        set_globals = lua_runtime.eval(
            """
            function(keys, argv, redis_call, redis_pcall, redis_log, redis_log_levels)
                redis = {}
                redis.call = redis_call
                redis.pcall = redis_pcall
                redis.log = redis_log
                for level, pylevel in python.iterex(redis_log_levels.items()) do
                    redis[level] = pylevel
                end
                redis.error_reply = function(msg) return {err=msg} end
                redis.status_reply = function(msg) return {ok=msg} end
                KEYS = keys
                ARGV = argv
            end
            """
        )
        expected_globals = set()
        set_globals(
            lua_runtime.table_from(keys_and_args[:numkeys]),
            lua_runtime.table_from(keys_and_args[numkeys:]),
            functools.partial(self._lua_redis_call, lua_runtime, expected_globals),
            functools.partial(self._lua_redis_pcall, lua_runtime, expected_globals),
            functools.partial(_lua_redis_log, lua_runtime, expected_globals),
            as_attrgetter(REDIS_LOG_LEVELS)
        )
        expected_globals.update(lua_runtime.globals().keys())

        try:
            result = lua_runtime.execute(script)
        except SimpleError as ex:
            if self.version == 6:
                raise SimpleError(msgs.SCRIPT_ERROR_MSG.format(sha1.decode(), ex))
            raise SimpleError(ex.value)
        except LuaError as ex:
            raise SimpleError(msgs.SCRIPT_ERROR_MSG.format(sha1.decode(), ex))

        _check_for_lua_globals(lua_runtime, expected_globals)

        return self._convert_lua_result(result, nested=False)

    @command((bytes, Int), (bytes,), flags='s')
    def evalsha(self, sha1, numkeys, *keys_and_args):
        try:
            script = self.script_cache[sha1]
        except KeyError:
            raise SimpleError(msgs.NO_MATCHING_SCRIPT_MSG)
        return self.eval(script, numkeys, *keys_and_args)

    @command(name='script load', fixed=(bytes,), repeat=(bytes,), flags='s', )
    def script_load(self, *args):
        if len(args) != 1:
            raise SimpleError(msgs.BAD_SUBCOMMAND_MSG.format('SCRIPT'))
        script = args[0]
        sha1 = hashlib.sha1(script).hexdigest().encode()
        self.script_cache[sha1] = script
        return sha1

    @command(name='script exists', fixed=(), repeat=(bytes,), flags='s', )
    def script_exists(self, *args):
        if self.version >= 7 and len(args) == 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG7)
        return [int(sha1 in self.script_cache) for sha1 in args]

    @command(name='script flush', fixed=(), repeat=(bytes,), flags='s', )
    def script_flush(self, *args):
        if len(args) > 1 or (len(args) == 1 and casenorm(args[0]) not in {b'sync', b'async'}):
            raise SimpleError(msgs.BAD_SUBCOMMAND_MSG.format('SCRIPT'))
        self.script_cache = {}
        return OK

    @command((bytes,), (bytes,), flags='s')
    def script(self, subcmd, *args):
        raise SimpleError(msgs.BAD_SUBCOMMAND_MSG.format('SCRIPT'))