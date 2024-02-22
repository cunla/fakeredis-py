import hashlib
import pickle
import random
from typing import Tuple, Any, Callable, List

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import (
    command,
    Key,
    Int,
    DbIndex,
    BeforeAny,
    CommandItem,
    SortFloat,
    delete_keys, Item,
)
from fakeredis._helpers import compile_pattern, SimpleError, OK, casematch, Database, SimpleString
from fakeredis._zset import ZSet


class GenericCommandsMixin:
    _ttl: Callable[[CommandItem, float], int]
    _scan: Callable[[CommandItem, int, bytes, bytes], Tuple[int, List[bytes]]]
    _key_value_type: Callable[[Item], SimpleString]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(GenericCommandsMixin, self).__init__(*args, **kwargs)
        self.version: Tuple[int]
        self._server: Any
        self._db: Database
        self._db_num: int

    def _lookup_key(self, key, pattern):
        """Python implementation of lookupKeyByPattern from redis"""
        if pattern == b"#":
            return key
        p = pattern.find(b"*")
        if p == -1:
            return None
        prefix = pattern[:p]
        suffix = pattern[p + 1:]
        arrow = suffix.find(b"->", 0, -1)
        if arrow != -1:
            field = suffix[arrow + 2:]
            suffix = suffix[:arrow]
        else:
            field = None
        new_key = prefix + key + suffix
        item = CommandItem(new_key, self._db, item=self._db.get(new_key))
        if item.value is None:
            return None
        if field is not None:
            if not isinstance(item.value, dict):
                return None
            return item.value.get(field)
        else:
            if not isinstance(item.value, bytes):
                return None
            return item.value

    def _expireat(self, key, timestamp, *args):
        (
            nx,
            xx,
            gt,
            lt,
        ), _ = extract_args(
            args,
            (
                "nx",
                "xx",
                "gt",
                "lt",
            ),
            exception=msgs.EXPIRE_UNSUPPORTED_OPTION,
        )
        if self.version < (7,) and any((nx, xx, gt, lt)):
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("expire"))
        counter = (nx, gt, lt).count(True)
        if (counter > 1) or (nx and xx):
            raise SimpleError(msgs.NX_XX_GT_LT_ERROR_MSG)
        if (
                not key
                or (xx and key.expireat is None)
                or (nx and key.expireat is not None)
                or (gt and key.expireat is not None and timestamp < key.expireat)
                or (lt and key.expireat is not None and timestamp > key.expireat)
        ):
            return 0
        key.expireat = timestamp
        return 1

    @command((Key(),), (Key(),), name="del")
    def del_(self, *keys):
        return delete_keys(*keys)

    @command((Key(missing_return=None),))
    def dump(self, key):
        value = pickle.dumps(key.value)
        checksum = hashlib.sha1(value).digest()
        return checksum + value

    @command((Key(),), (Key(),))
    def exists(self, *keys):
        ret = 0
        for key in keys:
            if key:
                ret += 1
        return ret

    @command(
        (
                Key(),
                Int,
        ),
        (bytes,),
        name="expire",
    )
    def expire(self, key, seconds, *args):
        res = self._expireat(key, self._db.time + seconds, *args)
        return res

    @command((Key(), Int))
    def expireat(self, key, timestamp):
        return self._expireat(key, float(timestamp))

    @command((bytes,))
    def keys(self, pattern):
        if pattern == b"*":
            return list(self._db)
        else:
            regex = compile_pattern(pattern)
            return [key for key in self._db if regex.match(key)]

    @command((Key(), DbIndex))
    def move(self, key, db):
        if db == self._db_num:
            raise SimpleError(msgs.SRC_DST_SAME_MSG)
        if not key or key.key in self._server.dbs[db]:
            return 0
        # TODO: what is the interaction with expiry?
        self._server.dbs[db][key.key] = self._server.dbs[self._db_num][key.key]
        key.value = None  # Causes deletion
        return 1

    @command((Key(),))
    def persist(self, key):
        if key.expireat is None:
            return 0
        key.expireat = None
        return 1

    @command((Key(), Int))
    def pexpire(self, key, ms):
        return self._expireat(key, self._db.time + ms / 1000.0)

    @command((Key(), Int))
    def pexpireat(self, key, ms_timestamp):
        return self._expireat(key, ms_timestamp / 1000.0)

    @command((Key(),))
    def pttl(self, key):
        return self._ttl(key, 1000.0)

    @command(())
    def randomkey(self):
        keys = list(self._db.keys())
        if not keys:
            return None
        return random.choice(keys)

    @command((Key(), Key()))
    def rename(self, key, newkey):
        if not key:
            raise SimpleError(msgs.NO_KEY_MSG)
        # TODO: check interaction with WATCH
        if newkey.key != key.key:
            newkey.value = key.value
            newkey.expireat = key.expireat
            key.value = None
        return OK

    @command((Key(), Key()))
    def renamenx(self, key, newkey):
        if not key:
            raise SimpleError(msgs.NO_KEY_MSG)
        if newkey:
            return 0
        self.rename(key, newkey)
        return 1

    @command((Key(), Int, bytes), (bytes,))
    def restore(self, key, ttl, value, *args):
        (replace,), _ = extract_args(args, ("replace",))
        if key and not replace:
            raise SimpleError(msgs.RESTORE_KEY_EXISTS)
        checksum, value = value[:20], value[20:]
        if hashlib.sha1(value).digest() != checksum:
            raise SimpleError(msgs.RESTORE_INVALID_CHECKSUM_MSG)
        if ttl < 0:
            raise SimpleError(msgs.RESTORE_INVALID_TTL_MSG)
        if ttl == 0:
            expireat = None
        else:
            expireat = self._db.time + ttl / 1000.0
        key.value = pickle.loads(value)
        key.expireat = expireat
        return OK

    @command((Int,), (bytes, bytes))
    def scan(self, cursor, *args):
        return self._scan(list(self._db), cursor, *args)

    @command((Key(),), (bytes,))
    def sort(self, key, *args):
        if key.value is not None and not isinstance(key.value, (set, list, ZSet)):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        (asc, desc, alpha, store, sortby, (limit_start, limit_count),), left_args = extract_args(
            args,
            ("asc", "desc", "alpha", "*store", "*by", "++limit"),
            error_on_unexpected=False,
            left_from_first_unexpected=False,
        )
        limit_start = limit_start or 0
        limit_count = -1 if limit_count is None else limit_count
        dontsort = sortby is not None and b"*" not in sortby

        i = 0
        get = []
        while i < len(left_args):
            if casematch(left_args[i], b"get") and i + 1 < len(left_args):
                get.append(left_args[i + 1])
                i += 2
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)

        # TODO: force sorting if the object is a set and either in Lua or
        #  storing to a key, to match redis behaviour.
        items = list(key.value) if key.value is not None else []

        # These transformations are based on the redis implementation, but
        # changed to produce a half-open range.
        start = max(limit_start, 0)
        end = len(items) if limit_count < 0 else start + limit_count
        if start >= len(items):
            start = end = len(items) - 1
        end = min(end, len(items))

        if not get:
            get.append(b"#")
        if sortby is None:
            sortby = b"#"

        if not dontsort:
            if alpha:

                def sort_key(val):
                    byval = self._lookup_key(val, sortby)
                    # TODO: use locale.strxfrm when not storing? But then need to decode too.
                    if byval is None:
                        byval = BeforeAny()
                    return byval

            else:

                def sort_key(val):
                    byval = self._lookup_key(val, sortby)
                    score = (
                        SortFloat.decode(
                            byval,
                        )
                        if byval is not None
                        else 0.0
                    )
                    return score, val

            items.sort(key=sort_key, reverse=desc)
        elif isinstance(key.value, (list, ZSet)):
            items.reverse()

        out = []
        for row in items[start:end]:
            for g in get:
                v = self._lookup_key(row, g)
                if store is not None and v is None:
                    v = b""
                out.append(v)
        if store is not None:
            item = CommandItem(store, self._db, item=self._db.get(store))
            item.value = out
            item.writeback()
            return len(out)
        else:
            return out

    @command((Key(),))
    def ttl(self, key: CommandItem):
        return self._ttl(key, 1.0)

    @command((Key(),))
    def type(self, key: CommandItem):
        return self._key_value_type(key)

    @command((Key(),), (Key(),), name="unlink")
    def unlink(self, *keys: CommandItem):
        return delete_keys(*keys)
