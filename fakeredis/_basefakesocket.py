import itertools
import queue
import time
import weakref

import redis
import six

from . import _msgs as msgs
from ._commands import (
    Int)
from ._helpers import (
    SimpleError, valid_response_type, SimpleString, NoResponse, casematch,
    compile_pattern, QUEUED)
from ._zset import ZSet


class BaseFakeSocket:
    def __init__(self, server):
        self._server = server
        self._db = server.dbs[0]
        self._db_num = 0
        # When in a MULTI, set to a list of function calls
        self._transaction = None
        self._transaction_failed = False
        # Set when executing the commands from EXEC
        self._in_transaction = False
        self._watch_notified = False
        self._watches = set()
        self._pubsub = 0  # Count of subscriptions
        self.responses = queue.Queue()
        # Prevents parser from processing commands. Not used in this module,
        # but set by aioredis module to prevent new commands being processed
        # while handling a blocking command.
        self._paused = False
        self._parser = self._parse_commands()
        self._parser.send(None)
        self.version = server.version

    def put_response(self, msg):
        # redis.Connection.__del__ might call self.close at any time, which
        # will set self.responses to None. We assume this will happen
        # atomically, and the code below then protects us against this.
        responses = self.responses
        if responses:
            responses.put(msg)

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False
        self._parser.send(b'')

    def shutdown(self, flags):
        self._parser.close()

    def fileno(self):
        # Our fake socket must return an integer from `FakeSocket.fileno()` since a real selector
        # will be created. The value does not matter since we replace the selector with our own
        # `FakeSelector` before it is ever used.
        return 0

    def _cleanup(self, server):
        """Remove all the references to `self` from `server`.

        This is called with the server lock held, but it may be some time after
        self.close.
        """
        for subs in server.subscribers.values():
            subs.discard(self)
        for subs in server.psubscribers.values():
            subs.discard(self)
        self._clear_watches()

    def close(self):
        # Mark ourselves for cleanup. This might be called from
        # redis.Connection.__del__, which the garbage collection could call
        # at any time, and hence we can't safely take the server lock.
        # We rely on list.append being atomic.
        self._server.closed_sockets.append(weakref.ref(self))
        self._server = None
        self._db = None
        self.responses = None

    @staticmethod
    def _extract_line(buf):
        pos = buf.find(b'\n') + 1
        assert pos > 0
        line = buf[:pos]
        buf = buf[pos:]
        assert line.endswith(b'\r\n')
        return line, buf

    def _parse_commands(self):
        """Generator that parses commands.

        It is fed pieces of redis protocol data (via `send`) and calls
        `_process_command` whenever it has a complete one.
        """
        buf = b''
        while True:
            while self._paused or b'\n' not in buf:
                buf += yield
            line, buf = self._extract_line(buf)
            assert line[:1] == b'*'  # array
            n_fields = int(line[1:-2])
            fields = []
            for i in range(n_fields):
                while b'\n' not in buf:
                    buf += yield
                line, buf = self._extract_line(buf)
                assert line[:1] == b'$'  # string
                length = int(line[1:-2])
                while len(buf) < length + 2:
                    buf += yield
                fields.append(buf[:length])
                buf = buf[length + 2:]  # +2 to skip the CRLF
            self._process_command(fields)

    def _run_command(self, func, sig, args, from_script):
        command_items = {}
        try:
            ret = sig.apply(args, self._db)
            if len(ret) == 1:
                result = ret[0]
            else:
                args, command_items = ret
                if from_script and msgs.FLAG_NO_SCRIPT in sig.flags:
                    raise SimpleError(msgs.COMMAND_IN_SCRIPT_MSG)
                if self._pubsub and sig.name not in [
                    'ping',
                    'subscribe',
                    'unsubscribe',
                    'psubscribe',
                    'punsubscribe',
                    'quit'
                ]:
                    raise SimpleError(msgs.BAD_COMMAND_IN_PUBSUB_MSG)
                result = func(*args)
                assert valid_response_type(result)
        except SimpleError as exc:
            result = exc
        for command_item in command_items:
            command_item.writeback()
        return result

    def _decode_error(self, error):
        return redis.connection.BaseParser().parse_error(error.value)

    def _decode_result(self, result):
        """Convert SimpleString and SimpleError, recursively"""
        if isinstance(result, list):
            return [self._decode_result(r) for r in result]
        elif isinstance(result, SimpleString):
            return result.value
        elif isinstance(result, SimpleError):
            return self._decode_error(result)
        else:
            return result

    def _blocking(self, timeout, func):
        """Run a function until it succeeds or timeout is reached.

        The timeout must be an integer, and 0 means infinite. The function
        is called with a boolean to indicate whether this is the first call.
        If it returns None it is considered to have "failed" and is retried
        each time the condition variable is notified, until the timeout is
        reached.

        Returns the function return value, or None if the timeout was reached.
        """
        ret = func(True)
        if ret is not None or self._in_transaction:
            return ret
        if timeout:
            deadline = time.time() + timeout
        else:
            deadline = None
        while True:
            timeout = deadline - time.time() if deadline is not None else None
            if timeout is not None and timeout <= 0:
                return None
            # Python <3.2 doesn't return a status from wait. On Python 3.2+
            # we bail out early on False.
            if self._db.condition.wait(timeout=timeout) is False:
                return None  # Timeout expired
            ret = func(False)
            if ret is not None:
                return ret

    def _name_to_func(self, name):
        name = six.ensure_str(name, encoding='utf-8', errors='replace')
        func_name = name.lower()
        func = getattr(self, func_name, None)
        if name.startswith('_') or not func or not hasattr(func, '_fakeredis_sig'):
            # redis remaps \r or \n in an error to ' ' to make it legal protocol
            clean_name = name.replace('\r', ' ').replace('\n', ' ')
            raise SimpleError(msgs.UNKNOWN_COMMAND_MSG.format(clean_name))
        return func, func_name

    def sendall(self, data):
        if not self._server.connected:
            raise self._connection_error_class(msgs.CONNECTION_ERROR_MSG)
        if isinstance(data, str):
            data = data.encode('ascii')
        self._parser.send(data)

    def _process_command(self, fields):
        if not fields:
            return
        func_name = None
        try:
            func, func_name = self._name_to_func(fields[0])
            sig = func._fakeredis_sig
            with self._server.lock:
                # Clean out old connections
                while True:
                    try:
                        weak_sock = self._server.closed_sockets.pop()
                    except IndexError:
                        break
                    else:
                        sock = weak_sock()
                        if sock:
                            sock._cleanup(self._server)
                now = time.time()
                for db in self._server.dbs.values():
                    db.time = now
                sig.check_arity(fields[1:])
                # TODO: make a signature attribute for transactions
                if self._transaction is not None \
                        and func_name not in ('exec', 'discard', 'multi', 'watch'):
                    self._transaction.append((func, sig, fields[1:]))
                    result = QUEUED
                else:
                    result = self._run_command(func, sig, fields[1:], False)
        except SimpleError as exc:
            if self._transaction is not None:
                # TODO: should not apply if the exception is from _run_command
                # e.g. watch inside multi
                self._transaction_failed = True
            if func_name == 'exec' and exc.value.startswith('ERR '):
                exc.value = 'EXECABORT Transaction discarded because of: ' + exc.value[4:]
                self._transaction = None
                self._transaction_failed = False
                self._clear_watches()
            result = exc
        result = self._decode_result(result)
        if not isinstance(result, NoResponse):
            self.put_response(result)

    def notify_watch(self):
        self._watch_notified = True

    # redis has inconsistent handling of negative indices, hence two versions
    # of this code.

    @staticmethod
    def _fix_range_string(start, end, length):
        # Negative number handling is based on the redis source code
        if start < 0 and end < 0 and start > end:
            return -1, -1
        if start < 0:
            start = max(0, start + length)
        if end < 0:
            end = max(0, end + length)
        end = min(end, length - 1)
        return start, end + 1

    @staticmethod
    def _fix_range(start, end, length):
        # Redis handles negative slightly differently for zrange
        if start < 0:
            start = max(0, start + length)
        if end < 0:
            end += length
        if start > end or start >= length:
            return -1, -1
        end = min(end, length - 1)
        return start, end + 1

    def _scan(self, keys, cursor, *args):
        """
        This is the basis of most of the ``scan`` methods.

        This implementation is KNOWN to be un-performant, as it requires
        grabbing the full set of keys over which we are investigating subsets.

        It also doesn't adhere to the guarantee that every key will be iterated
        at least once even if the database is modified during the scan.
        However, provided the database is not modified, every key will be
        returned exactly once.
        """
        cursor = int(cursor)
        pattern = None
        type = None
        count = 10
        if len(args) % 2 != 0:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        for i in range(0, len(args), 2):
            if casematch(args[i], b'match'):
                pattern = args[i + 1]
            elif casematch(args[i], b'count'):
                count = Int.decode(args[i + 1])
                if count <= 0:
                    raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            elif casematch(args[i], b'type'):
                type = args[i + 1]
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)

        if cursor >= len(keys):
            return [0, []]
        data = sorted(keys)
        result_cursor = cursor + count
        result_data = []

        regex = compile_pattern(pattern) if pattern is not None else None

        def match_key(key):
            return regex.match(key) if pattern is not None else True

        def match_type(key):
            if type is not None:
                return casematch(self._type(self._db[key]).value, type)
            return True

        if pattern is not None or type is not None:
            for val in itertools.islice(data, cursor, result_cursor):
                compare_val = val[0] if isinstance(val, tuple) else val
                if match_key(compare_val) and match_type(compare_val):
                    result_data.append(val)
        else:
            result_data = data[cursor:result_cursor]

        if result_cursor >= len(data):
            result_cursor = 0
        return [str(result_cursor).encode(), result_data]

    @staticmethod
    def _calc_setop(op, stop_if_missing, key, *keys):
        if stop_if_missing and not key.value:
            return set()
        ans = key.value.copy()
        for other in keys:
            value = other.value if other.value is not None else set()
            if not isinstance(value, set):
                raise SimpleError(msgs.WRONGTYPE_MSG)
            if stop_if_missing and not value:
                return set()
            ans = op(ans, value)
        return ans

    def _setop(self, op, stop_if_missing, dst, key, *keys):
        """Apply one of SINTER[STORE], SUNION[STORE], SDIFF[STORE].

        If `stop_if_missing`, the output will be made an empty set as soon as
        an empty input set is encountered (use for SINTER[STORE]). May assume
        that `key` is a set (or empty), but `keys` could be anything.
        """
        ans = self._calc_setop(op, stop_if_missing, key, *keys)
        if dst is None:
            return list(ans)
        else:
            dst.value = ans
            return len(dst.value)

    def _type(self, key):
        if key.value is None:
            return SimpleString(b'none')
        elif isinstance(key.value, bytes):
            return SimpleString(b'string')
        elif isinstance(key.value, list):
            return SimpleString(b'list')
        elif isinstance(key.value, set):
            return SimpleString(b'set')
        elif isinstance(key.value, ZSet):
            return SimpleString(b'zset')
        elif isinstance(key.value, dict):
            return SimpleString(b'hash')
        else:
            assert False  # pragma: nocover

    def _clear_watches(self):
        self._watch_notified = False
        while self._watches:
            (key, db) = self._watches.pop()
            db.remove_watch(key, self)

    # Pubsub commands
    # TODO: pubsub command

    def _subscribe(self, channels, subscribers, mtype):
        for channel in channels:
            subs = subscribers[channel]
            if self not in subs:
                subs.add(self)
                self._pubsub += 1
            msg = [mtype, channel, self._pubsub]
            self.put_response(msg)
        return NoResponse()

    def _unsubscribe(self, channels, subscribers, mtype):
        if not channels:
            channels = []
            for (channel, subs) in subscribers.items():
                if self in subs:
                    channels.append(channel)
        for channel in channels:
            subs = subscribers.get(channel, set())
            if self in subs:
                subs.remove(self)
                if not subs:
                    del subscribers[channel]
                self._pubsub -= 1
            msg = [mtype, channel, self._pubsub]
            self.put_response(msg)
        return NoResponse()

    def _delete(self, *keys):
        ans = 0
        done = set()
        for key in keys:
            if key and key.key not in done:
                key.value = None
                done.add(key.key)
                ans += 1
        return ans

    def _expireat(self, key, timestamp, *args):
        nx = False
        xx = False
        gt = False
        lt = False
        for arg in args:
            if casematch(b'nx', arg):
                nx = True
            elif casematch(b'xx', arg):
                xx = True
            elif casematch(b'gt', arg):
                gt = True
            elif casematch(b'lt', arg):
                lt = True
            else:
                raise SimpleError(msgs.EXPIRE_UNSUPPORTED_OPTION.format(arg))
        if self.version < 7 and (nx or xx or gt or lt):
            raise SimpleError(msgs.WRONG_ARGS_MSG.format('expire'))
        counter = (nx, gt, lt).count(True)
        if (counter > 1) or (nx and xx):
            raise SimpleError(msgs.NX_XX_GT_LT_ERROR_MSG)
        if (not key
                or (xx and key.expireat is None)
                or (nx and key.expireat is not None)
                or (gt and key.expireat is not None and timestamp < key.expireat)
                or (lt and key.expireat is not None and timestamp > key.expireat)):
            return 0
        key.expireat = timestamp
        return 1
