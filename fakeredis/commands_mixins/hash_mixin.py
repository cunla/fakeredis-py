import datetime
import itertools
import math
import random
import time
from typing import Callable, List, Tuple, Any, Optional, Union

from fakeredis import _msgs as msgs
from fakeredis._commands import command, Key, Hash, Int, Float, CommandItem
from fakeredis._helpers import HEXPIRE_CONDITION_UNMET, HEXPIRE_NO_SUCH_KEY
from fakeredis._helpers import SimpleError, OK, casematch, SimpleString


class HashCommandsMixin:
    _encodeint: Callable[
        [
            int,
        ],
        bytes,
    ]
    _encodefloat: Callable[[float, bool], bytes]
    _scan: Callable[[CommandItem, int, bytes, bytes], Tuple[int, List[bytes]]]

    def _hset(self, key: CommandItem, *args: bytes) -> int:
        h = key.value
        keys_count = len(h.keys())
        h.update(dict(zip(*[iter(args)] * 2)))  # type: ignore  # https://stackoverflow.com/a/12739974/1056460
        created = len(h.keys()) - keys_count

        key.updated()
        return created

    @command((Key(Hash), bytes), (bytes,))
    def hdel(self, key: CommandItem, *fields: bytes) -> int:
        h = key.value
        rem = 0
        for field in fields:
            if field in h:
                del h[field]
                key.updated()
                rem += 1
        return rem

    @command((Key(Hash), bytes))
    def hexists(self, key: CommandItem, field: bytes) -> int:
        return int(field in key.value)

    @command((Key(Hash), bytes))
    def hget(self, key: CommandItem, field: bytes) -> Any:
        return key.value.get(field)

    @command((Key(Hash),))
    def hgetall(self, key: CommandItem) -> List[bytes]:
        return list(itertools.chain(*key.value.items()))

    @command(fixed=(Key(Hash), bytes, bytes))
    def hincrby(self, key: CommandItem, field: bytes, amount_bytes: bytes) -> int:
        amount = Int.decode(amount_bytes)
        field_value = Int.decode(key.value.get(field, b"0"), decode_error=msgs.INVALID_HASH_MSG)
        c = field_value + amount
        key.value[field] = self._encodeint(c)
        key.updated()
        return c

    @command((Key(Hash), bytes, bytes))
    def hincrbyfloat(self, key: CommandItem, field: bytes, amount: bytes) -> bytes:
        c = Float.decode(key.value.get(field, b"0")) + Float.decode(amount)
        if not math.isfinite(c):
            raise SimpleError(msgs.NONFINITE_MSG)
        encoded = self._encodefloat(c, True)
        key.value[field] = encoded
        key.updated()
        return encoded

    @command((Key(Hash),))
    def hkeys(self, key: CommandItem) -> List[bytes]:
        return list(key.value.keys())

    @command((Key(Hash),))
    def hlen(self, key: CommandItem) -> int:
        return len(key.value)

    @command((Key(Hash), bytes), (bytes,))
    def hmget(self, key: CommandItem, *fields: bytes) -> List[bytes]:
        return [key.value.get(field) for field in fields]

    @command((Key(Hash), bytes, bytes), (bytes, bytes))
    def hmset(self, key: CommandItem, *args: bytes) -> SimpleString:
        self.hset(key, *args)
        return OK

    @command((Key(Hash), Int), (bytes, bytes))
    def hscan(self, key: CommandItem, cursor: int, *args: bytes) -> List[Any]:
        cursor, keys = self._scan(key.value, cursor, *args)
        items = []
        for k in keys:
            items.append(k)
            items.append(key.value[k])
        return [cursor, items]

    @command((Key(Hash), bytes, bytes), (bytes, bytes))
    def hset(self, key: CommandItem, *args: bytes) -> int:
        return self._hset(key, *args)

    @command((Key(Hash), bytes, bytes))
    def hsetnx(self, key: CommandItem, field: bytes, value: bytes) -> int:
        if field in key.value:
            return 0
        return self._hset(key, field, value)

    @command((Key(Hash), bytes))
    def hstrlen(self, key: CommandItem, field: bytes) -> int:
        return len(key.value.get(field, b""))

    @command((Key(Hash),))
    def hvals(self, key: CommandItem) -> List[bytes]:
        return list(key.value.values())

    @command(name="HRANDFIELD", fixed=(Key(Hash),), repeat=(bytes,))
    def hrandfield(self, key: CommandItem, *args: bytes) -> Optional[List[bytes]]:
        if len(args) > 2:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if key.value is None or len(key.value) == 0:
            return None
        count = min(Int.decode(args[0]) if len(args) >= 1 else 1, len(key.value))
        withvalues = casematch(args[1], b"withvalues") if len(args) >= 2 else False
        if count == 0:
            return list()

        if count < 0:  # Allow repetitions
            res = random.choices(sorted(key.value.items()), k=-count)
        else:  # Unique values from hash
            res = random.sample(sorted(key.value.items()), count)

        if withvalues:
            res = [item for t in res for item in t]
        else:
            res = [t[0] for t in res]
        return res

    def _set_key_expiration(
        self,
        key: CommandItem,
        field: bytes,
        expiration: Union[datetime.datetime, datetime.timedelta, int, float],
        include_ms: bool,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> int:
        hash_val: Hash = key.value
        if field not in hash_val:
            return HEXPIRE_NO_SUCH_KEY
        current_expiration = hash_val._get_expiration(field)
        if isinstance(expiration, datetime.datetime):
            final_expiration = expiration.timestamp()
        elif isinstance(expiration, datetime.timedelta):
            final_expiration = time.time() + expiration.total_seconds()
        else:
            final_expiration = time.time() + expiration
        if include_ms:
            final_expiration = float(final_expiration)
        else:
            final_expiration = int(final_expiration)
        if (
            (nx and current_expiration is not None)
            or (xx and current_expiration is None)
            or (gt and final_expiration <= current_expiration)
            or (lt and final_expiration >= current_expiration)
        ):
            return HEXPIRE_CONDITION_UNMET
        return hash_val._set_expiration(field, final_expiration)

    @command(name="HEXPIRE", fixed=(Key, Union[int, datetime.timedelta]), repeat=(bytes,))
    def hexpire(
        self,
        key: CommandItem,
        seconds: Union[int, datetime.timedelta],
        *fields: bytes,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> List[int]:
        return [self._set_key_expiration(key, field, seconds, False, nx, xx, gt, lt) for field in fields]

    @command(name="HPEXPIRE", fixed=(Key, Union[float, datetime.timedelta]), repeat=(bytes,))
    def hpexpire(
        self,
        key: CommandItem,
        milliseconds: float,
        *fields: bytes,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> List[int]:
        return [self._set_key_expiration(key, field, milliseconds, True, nx, xx, gt, lt) for field in fields]

    @command(name="HEXPIREAT", fixed=(Key, Union[int, datetime.datetime]), repeat=(bytes,))
    def hexpireat(
        self,
        key: CommandItem,
        unix_time_seconds: Union[int, datetime.datetime],
        *fields: bytes,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> List[int]:
        return [self._set_key_expiration(key, field, unix_time_seconds, False, nx, xx, gt, lt) for field in fields]

    @command(name="HPEXPIREAT", fixed=(Key, Union[float, datetime.datetime]), repeat=(bytes,))
    def hpexpireat(
        self,
        key: CommandItem,
        unix_time_milliseconds: float,
        *fields: bytes,
        nx: bool = False,
        xx: bool = False,
        gt: bool = False,
        lt: bool = False,
    ) -> List[int]:
        return [self._set_key_expiration(key, field, unix_time_milliseconds, True, nx, xx, gt, lt) for field in fields]

    @command(name="HPERSIST", fixed=(Key,), repeat=(bytes,))
    def hpersist(self, key: CommandItem, *fields: bytes) -> List[int]:
        hash_val: Hash = key.value
        return [
            -2 if field not in hash_val._expirations else (1 if hash_val._clear_expiration(field) else -1)
            for field in fields
        ]

    @command(name="HEXPIRETIME", fixed=(Key,), repeat=(bytes,))
    def hexpiretime(self, key: CommandItem, *fields: bytes) -> List[int]:
        hash_val: Hash = key.value
        return [
            -2 if field not in hash_val._expirations else int(hash_val._get_expiration(field) or -1) for field in fields
        ]

    @command(name="HPEXPIRETIME", fixed=(Key,), repeat=(bytes,))
    def hpexpiretime(self, key: CommandItem, *fields: bytes) -> List[float]:
        hash_val: Hash = key.value
        return [
            -2 if field not in hash_val._expirations else float(hash_val._get_expiration(field) or -1)
            for field in fields
        ]

    @command(name="HTTL", fixed=(Key,), repeat=(bytes,))
    def httl(self, key: CommandItem, *fields: bytes) -> List[int]:
        hash_val: Hash = key.value
        return [
            (
                -2
                if field not in hash_val._expirations
                else int(hash_val._get_expiration(field) - time.time() if hash_val._get_expiration(field) else -1)
            )
            for field in fields
        ]

    @command(name="HPTTL", fixed=(Key,), repeat=(bytes,))
    def hpttl(self, key: CommandItem, *fields: bytes) -> List[float]:
        hash_val: Hash = key.value
        return [
            (
                -2
                if field not in hash_val._expirations
                else float(hash_val._get_expiration(field) - time.time() if hash_val._get_expiration(field) else -1)
            )
            for field in fields
        ]
