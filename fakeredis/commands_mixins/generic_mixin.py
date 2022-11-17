import hashlib
import pickle
from random import random

from fakeredis import _msgs as msgs
from fakeredis._commands import command, Key, Int, DbIndex, BeforeAny, CommandItem, SortFloat, delete_keys
from fakeredis._helpers import compile_pattern, SimpleError, OK, casematch, SimpleString
from fakeredis._zset import ZSet


class GenericCommandsMixin:
    def _lookup_key(self, key, pattern):
        """Python implementation of lookupKeyByPattern from redis"""
        if pattern == b'#':
            return key
        p = pattern.find(b'*')
        if p == -1:
            return None
        prefix = pattern[:p]
        suffix = pattern[p + 1:]
        arrow = suffix.find(b'->', 0, -1)
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

    @staticmethod
    def _key_value_type(key):
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
        if self.version < 7 and any((nx, xx, gt, lt)):
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format('expire'))
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

    @command((Key(),), (Key(),), name='del')
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

    @command((Key(), Int,), (bytes,), name='expire')
    def expire(self, key, seconds, *args):
        res = self._expireat(key, self._db.time + seconds, *args)
        return res

    @command((Key(), Int))
    def expireat(self, key, timestamp):
        return self._expireat(key, float(timestamp))

    @command((bytes,))
    def keys(self, pattern):
        if pattern == b'*':
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
        replace = False
        i = 0
        while i < len(args):
            if casematch(args[i], b'replace'):
                replace = True
                i += 1
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
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
        i = 0
        desc = False
        alpha = False
        limit_start = 0
        limit_count = -1
        store = None
        sortby = None
        dontsort = False
        get = []
        if key.value is not None:
            if not isinstance(key.value, (set, list, ZSet)):
                raise SimpleError(msgs.WRONGTYPE_MSG)

        while i < len(args):
            arg = args[i]
            if casematch(arg, b'asc'):
                desc = False
            elif casematch(arg, b'desc'):
                desc = True
            elif casematch(arg, b'alpha'):
                alpha = True
            elif casematch(arg, b'limit') and i + 2 < len(args):
                try:
                    limit_start = Int.decode(args[i + 1])
                    limit_count = Int.decode(args[i + 2])
                except SimpleError:
                    raise SimpleError(msgs.SYNTAX_ERROR_MSG)
                else:
                    i += 2
            elif casematch(arg, b'store') and i + 1 < len(args):
                store = args[i + 1]
                i += 1
            elif casematch(arg, b'by') and i + 1 < len(args):
                sortby = args[i + 1]
                if b'*' not in sortby:
                    dontsort = True
                i += 1
            elif casematch(arg, b'get') and i + 1 < len(args):
                get.append(args[i + 1])
                i += 1
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            i += 1

        # TODO: force sorting if the object is a set and either in Lua or
        # storing to a key, to match redis behaviour.
        items = list(key.value) if key.value is not None else []

        # These transformations are based on the redis implementation, but
        # changed to produce a half-open range.
        start = max(limit_start, 0)
        end = len(items) if limit_count < 0 else start + limit_count
        if start >= len(items):
            start = end = len(items) - 1
        end = min(end, len(items))

        if not get:
            get.append(b'#')
        if sortby is None:
            sortby = b'#'

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
                    score = SortFloat.decode(byval, ) if byval is not None else 0.0
                    return score, val

            items.sort(key=sort_key, reverse=desc)
        elif isinstance(key.value, (list, ZSet)):
            items.reverse()

        out = []
        for row in items[start:end]:
            for g in get:
                v = self._lookup_key(row, g)
                if store is not None and v is None:
                    v = b''
                out.append(v)
        if store is not None:
            item = CommandItem(store, self._db, item=self._db.get(store))
            item.value = out
            item.writeback()
            return len(out)
        else:
            return out

    @command((Key(),))
    def ttl(self, key):
        return self._ttl(key, 1.0)

    @command((Key(),))
    def type(self, key):
        return self._key_value_type(key)

    @command((Key(),), (Key(),), name='unlink')
    def unlink(self, *keys):
        return delete_keys(*keys)


setattr(GenericCommandsMixin, 'del', GenericCommandsMixin.del_)
delattr(GenericCommandsMixin, 'del_')
