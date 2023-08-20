import itertools
import math
import random
from typing import Callable

from fakeredis import _msgs as msgs
from fakeredis._commands import command, Key, Hash, Int, Float
from fakeredis._helpers import SimpleError, OK, casematch


class HashCommandsMixin:
    _encodeint: Callable[[int, ], bytes]
    _encodefloat: Callable[[float, bool], bytes]

    @command((Key(Hash), bytes), (bytes,))
    def hdel(self, key, *fields):
        h = key.value
        rem = 0
        for field in fields:
            if field in h:
                del h[field]
                key.updated()
                rem += 1
        return rem

    @command((Key(Hash), bytes))
    def hexists(self, key, field):
        return int(field in key.value)

    @command((Key(Hash), bytes))
    def hget(self, key, field):
        return key.value.get(field)

    @command((Key(Hash),))
    def hgetall(self, key):
        return list(itertools.chain(*key.value.items()))

    @command(fixed=(Key(Hash), bytes, bytes))
    def hincrby(self, key, field, amount):
        amount = Int.decode(amount)
        field_value = Int.decode(
            key.value.get(field, b"0"), decode_error=msgs.INVALID_HASH_MSG
        )
        c = field_value + amount
        key.value[field] = self._encodeint(c)
        key.updated()
        return c

    @command((Key(Hash), bytes, bytes))
    def hincrbyfloat(self, key, field, amount):
        c = Float.decode(key.value.get(field, b"0")) + Float.decode(amount)
        if not math.isfinite(c):
            raise SimpleError(msgs.NONFINITE_MSG)
        encoded = self._encodefloat(c, True)
        key.value[field] = encoded
        key.updated()
        return encoded

    @command((Key(Hash),))
    def hkeys(self, key):
        return list(key.value.keys())

    @command((Key(Hash),))
    def hlen(self, key):
        return len(key.value)

    @command((Key(Hash), bytes), (bytes,))
    def hmget(self, key, *fields):
        return [key.value.get(field) for field in fields]

    @command((Key(Hash), bytes, bytes), (bytes, bytes))
    def hmset(self, key, *args):
        self.hset(key, *args)
        return OK

    @command(
        (
                Key(Hash),
                Int,
        ),
        (bytes, bytes),
    )
    def hscan(self, key, cursor, *args):
        cursor, keys = self._scan(key.value, cursor, *args)
        items = []
        for k in keys:
            items.append(k)
            items.append(key.value[k])
        return [cursor, items]

    @command((Key(Hash), bytes, bytes), (bytes, bytes))
    def hset(self, key, *args):
        h = key.value
        keys_count = len(h.keys())
        h.update(
            dict(zip(*[iter(args)] * 2))
        )  # https://stackoverflow.com/a/12739974/1056460
        created = len(h.keys()) - keys_count

        key.updated()
        return created

    @command((Key(Hash), bytes, bytes))
    def hsetnx(self, key, field, value):
        if field in key.value:
            return 0
        return self.hset(key, field, value)

    @command((Key(Hash), bytes))
    def hstrlen(self, key, field):
        return len(key.value.get(field, b""))

    @command((Key(Hash),))
    def hvals(self, key):
        return list(key.value.values())

    @command(name="HRANDFIELD", fixed=(Key(Hash),), repeat=(bytes,))
    def hrandfield(self, key, *args):
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

    def _scan(self, keys, cursor, *args):
        raise NotImplementedError  # Implemented in BaseFakeSocket
