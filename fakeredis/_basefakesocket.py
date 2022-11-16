import itertools
import queue
import time
import weakref

import redis

from . import _msgs as msgs
from ._commands import (Int, Float)
from ._helpers import (
    SimpleError, valid_response_type, SimpleString, NoResponse, casematch,
    compile_pattern, QUEUED)


class BaseFakeSocket:
    def __init__(self, server, *args, **kwargs):
        super(BaseFakeSocket, self).__init__(*args, **kwargs)
        self._server = server
        self._db = server.dbs[0]
        self._db_num = 0
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

    @staticmethod
    def fileno():
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
            ret = sig.apply(args, self._db, self.version)
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
        name = (name.decode(encoding='utf-8', errors='replace')
                if isinstance(name, bytes)
                else str(name).encode(encoding='utf-8', errors='replace'))
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
                sig.check_arity(fields[1:], self.version)
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
        _type = None
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
                _type = args[i + 1]
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
            if _type is not None:
                return casematch(self._type(self._db[key]).value, _type)
            return True

        if pattern is not None or _type is not None:
            for val in itertools.islice(data, cursor, result_cursor):
                compare_val = val[0] if isinstance(val, tuple) else val
                if match_key(compare_val) and match_type(compare_val):
                    result_data.append(val)
        else:
            result_data = data[cursor:result_cursor]

        if result_cursor >= len(data):
            result_cursor = 0
        return [str(result_cursor).encode(), result_data]

    def _ttl(self, key, scale):
        if not key:
            return -2
        elif key.expireat is None:
            return -1
        else:
            return int(round((key.expireat - self._db.time) * scale))

    def _encodefloat(self, value, humanfriendly):
        if self.version >= 7:
            value = 0 + value
        return Float.encode(value, humanfriendly)

    def _encodeint(self, value):
        if self.version >= 7:
            value = 0 + value
        return Int.encode(value)
