from __future__ import annotations

import bisect
import itertools
from collections.abc import Collection
from re import Match
from typing import Any, Callable

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import Float, Int, extract_args
from fakeredis._core import CommandItem, Database, FakeServer
from fakeredis._helpers import SimpleError, SimpleString, casematch, compile_pattern
from fakeredis._typing import ServerType, VersionType
from fakeredis.model import BaseModel, ClientInfo


def bin_reverse(x: int, bits_count: int) -> int:
    result = 0
    for i in range(bits_count):
        if (x >> i) & 1:
            result |= 1 << (bits_count - 1 - i)
    return result


def _scan_sort_key(val: Any) -> Any:
    """The part of a scanned element that places it: the member of a ZSCAN (member, score) pair, whose score may change
    between calls, or the element itself."""
    return val[0] if isinstance(val, tuple) else val


class CommandsMixinBase:
    """Base class for command mixins: declares the attributes the socket provides, and the helpers several mixins
    share."""

    _server: FakeServer
    _client_info: ClientInfo
    _db: Database
    _script_resp: int | None = None
    _in_transaction: bool = False

    @property
    def version(self) -> VersionType:
        raise NotImplementedError

    @property
    def server_type(self) -> ServerType:
        raise NotImplementedError

    @property
    def _resp_version(self) -> int:
        """RESP version the reply being built should be shaped for.

        That is the client's negotiated protocol, except inside a script, where replies to
        `redis.call` follow the script's own RESP mode instead.
        """
        return self._script_resp if self._script_resp is not None else self._client_info.protocol_version

    def _blocking(
        self, timeout: float | None, func: Callable[[bool], Any], shape: Callable[[Any], Any] | None = None
    ) -> Any:
        """Implemented by the socket, sync and async alike; see `FakeSocket._blocking`."""
        raise NotImplementedError

    def _empty_blocking_reply(self, result: Any) -> Any:
        """Shape a timed-out array-returning blocking pop (BLPOP/BRPOP/BZPOPMIN/BZPOPMAX).

        Redis sends a null array, which RESP3 renders as nil. Dragonfly sends an empty array instead, so under RESP3 the
        client sees `[]` rather than `None`. Under RESP2 both encode to `*-1` and the client sees `None` either way.
        """
        if result is None and self.server_type == "dragonfly" and self._resp_version == 3:
            return []
        return result

    def _scan(self, keys: Collection[Any], cursor: int, *args: bytes, scanned_key: bytes | None = None) -> list[Any]:
        """This is the basis of most of the ``scan`` methods.

        `keys` holds plain keys, or (member, score) pairs for ZSCAN; MATCH and TYPE test the first element of a pair.
        `scanned_key` names the key whose members are scanned (HSCAN, SSCAN, ZSCAN), or is None for SCAN itself.

        This implementation is KNOWN to be un-performant, as it requires grabbing the full set of keys over which we are
        investigating subsets.

        The SCAN command, and the other commands in the SCAN family, are able to provide to the user a set of guarantees
        associated with full iterations.

        - A full iteration always retrieves all the elements that were present in the collection from the start to the
          end of a full iteration. This means that if a given element is inside the collection when an iteration is
          started and is still there when an iteration terminates, then at some point the SCAN command returned it to
          the user.

        - A full iteration never returns any element that was NOT present in the collection from the start to the end
          of a full iteration. So if an element was removed before the start of an iteration and is never added back
          to the collection for all the time an iteration lasts, the SCAN command ensures that this element will never
          be returned.

        However, because the SCAN command has very little state associated (just the cursor), it has the following
        drawbacks:

        - A given element may be returned multiple times. It is up to the application to handle the case of duplicated
          elements, for example, only using the returned elements to perform operations that are safe when re-applied
          multiple times.
        - Elements that were not constantly present in the collection during a full iteration may be returned or not:
          it is undefined.

        """
        cursor = int(cursor)
        (pattern, _type, count), _ = extract_args(args, ("*match", "*type", "+count"))
        if count is not None and count <= 0:
            # Dragonfly reads COUNT as unsigned: a negative one never decodes, while a zero is accepted and simply falls
            # back to the default batch size.
            if self._server.server_type != "dragonfly":
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            if count < 0:
                raise SimpleError(msgs.INVALID_INT_MSG)
            count = None
        count = 10 if count is None else count
        data = sorted(keys)
        bits_len = (len(keys) - 1).bit_length()
        # A cursor is a position in the sorted collection, but positions shift when elements are removed mid-scan and
        # an unseen element would be skipped. So each cursor handed out also records the last element it covered, and
        # the scan resumes after that element, wherever it now sits.
        scan_state = (self._db, scanned_key)
        last_seen = self._server.scan_cursors.get((scan_state, cursor)) if cursor else None
        if last_seen is None:
            cursor = bin_reverse(cursor, bits_len)
        else:
            cursor = bisect.bisect_right([_scan_sort_key(val) for val in data], last_seen)
        if cursor >= len(keys):
            return [b"0", []]
        result_cursor = cursor + count
        result_data = []

        regex = compile_pattern(pattern) if pattern is not None else None

        def match_key(key: bytes) -> bool | Match[bytes] | None:
            if isinstance(key, str):
                key = key.encode("utf-8")
            return regex.match(key) if regex is not None else True

        def match_type(key: bytes) -> bool:
            return _type is None or casematch(self._key_value_type(self._db[key]).value, _type)

        if pattern is not None or _type is not None:
            for val in itertools.islice(data, cursor, cursor + count):
                compare_val = val[0] if isinstance(val, tuple) else val
                if match_key(compare_val) and match_type(compare_val):
                    result_data.append(val)
        else:
            result_data = data[cursor : cursor + count]

        if result_cursor >= len(data):
            return [b"0", result_data]
        encoded_cursor = bin_reverse(result_cursor, bits_len)
        self._server.remember_scan_cursor((scan_state, encoded_cursor), _scan_sort_key(data[result_cursor - 1]))
        return [str(encoded_cursor).encode(), result_data]

    def _ttl(self, key: CommandItem, scale: float) -> int:
        if not key:
            return -2
        elif key.expireat is None:
            return -1
        else:
            return int(round((key.expireat - self._db.time) * scale))  # noqa: RUF046  # int() satisfies mypy no-any-return

    def _encodefloat(self, value: float, humanfriendly: bool) -> bytes:
        if self.version >= (7,):
            value = 0 + value
        return Float.encode(value, humanfriendly)

    def _encodeint(self, value: int) -> bytes:
        if self.version >= (7,):
            value = 0 + value
        return Int.encode(value)

    @staticmethod
    def _key_value_type(key: CommandItem) -> SimpleString:
        if key.value is None:
            return SimpleString(b"none")
        elif isinstance(key.value, bytes):
            return SimpleString(b"string")
        elif isinstance(key.value, list):
            return SimpleString(b"list")
        elif isinstance(key.value, BaseModel):
            return SimpleString(key.value.model_type())
        else:
            assert False  # pragma: nocover
