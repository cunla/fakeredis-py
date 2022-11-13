from __future__ import annotations

import functools
import math
from typing import Optional, Union

import redis

from . import _msgs as msgs
from ._basefakesocket import BaseFakeSocket
from ._commands import (Key, command, Int, CommandItem, Float, BitOffset, BitValue, StringTest, ScoreTest, Timeout)
from ._helpers import (OK, SimpleError, casematch, casenorm)
from ._zset import ZSet
from .commands_mixins.connection_mixin import ConnectionCommandsMixin
from .commands_mixins.generic_mixin import GenericCommandsMixin
from .commands_mixins.hash_mixin import HashCommandsMixin
from .commands_mixins.list_mixin import ListCommandsMixin
from .commands_mixins.pubsub_mixin import PubSubCommandsMixin
from .commands_mixins.scripting_mixin import ScriptingCommandsMixin
from .commands_mixins.server_mixin import ServerCommandsMixin
from .commands_mixins.set_mixin import SetCommandsMixin
from .commands_mixins.string_mixin import StringCommandsMixin
from .commands_mixins.transactions_mixin import TransactionsCommandsMixin


class FakeSocket(
    BaseFakeSocket,
    GenericCommandsMixin,
    ScriptingCommandsMixin,
    HashCommandsMixin,
    ConnectionCommandsMixin,
    ListCommandsMixin,
    ServerCommandsMixin,
    StringCommandsMixin,
    TransactionsCommandsMixin,
    PubSubCommandsMixin,
    SetCommandsMixin,
):
    _connection_error_class = redis.ConnectionError

    def __init__(self, server):
        super(FakeSocket, self).__init__(server)



    # Hyperloglog commands
    # These are not quite the same as the real redis ones, which are
    # approximate and store the results in a string. Instead, it is implemented
    # on top of sets.

    @command((Key(set),), (bytes,))
    def pfadd(self, key, *elements):
        result = self.sadd(key, *elements)
        # Per the documentation:
        # - 1 if at least 1 HyperLogLog internal register was altered. 0 otherwise.
        return 1 if result > 0 else 0

    @command((Key(set),), (Key(set),))
    def pfcount(self, *keys):
        """
        Return the approximated cardinality of
        the set observed by the HyperLogLog at key(s).
        """
        return len(self.sunion(*keys))

    @command((Key(set), Key(set)), (Key(set),))
    def pfmerge(self, dest, *sources):
        "Merge N different HyperLogLogs into a single one."
        self.sunionstore(dest, *sources)
        return OK

    # Sorted set commands

    @command((Key(ZSet),), (Int,))
    def zpopmin(self, key, count=1):
        return self._zpop(key, count, False)

    @command((Key(ZSet),), (Int,))
    def zpopmax(self, key, count=1):
        return self._zpop(key, count, True)

    @command((bytes, bytes), (bytes,), flags='s')
    def bzpopmin(self, *args):
        keys = args[:-1]
        timeout = Timeout.decode(args[-1])
        return self._blocking(timeout, functools.partial(self._bzpop, keys, False))

    @command((bytes, bytes), (bytes,), flags='s')
    def bzpopmax(self, *args):
        keys = args[:-1]
        timeout = Timeout.decode(args[-1])
        return self._blocking(timeout, functools.partial(self._bzpop, keys, True))

    @staticmethod
    def _limit_items(items, offset, count):
        out = []
        for item in items:
            if offset:  # Note: not offset > 0, in order to match redis
                offset -= 1
                continue
            if count == 0:
                break
            count -= 1
            out.append(item)
        return out

    def _apply_withscores(self, items, withscores):
        if withscores:
            out = []
            for item in items:
                out.append(item[1])
                out.append(self._encodefloat(item[0], False))
        else:
            out = [item[1] for item in items]
        return out

    @command((Key(ZSet), bytes, bytes), (bytes,))
    def zadd(self, key, *args):
        zset = key.value
        ZADD_PARAMS = ['nx', 'xx', 'ch', 'incr', 'gt', 'lt', ]
        param_val = {k: False for k in ZADD_PARAMS}
        i = 0

        while i < len(args):
            found = False
            for param in ZADD_PARAMS:
                if casematch(args[i], bytes(param, encoding='utf8')):
                    param_val[param] = True
                    found = True
                    break
            if found:
                i += 1
                continue
            # First argument not matching flags indicates the start of
            # score pairs.
            break

        if param_val['nx'] and param_val['xx']:
            raise SimpleError(msgs.ZADD_NX_XX_ERROR_MSG)
        if [param_val['nx'], param_val['gt'], param_val['lt']].count(True) > 1:
            raise SimpleError(msgs.ZADD_NX_GT_LT_ERROR_MSG)
        elements = args[i:]
        if not elements or len(elements) % 2 != 0:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if param_val['incr'] and len(elements) != 2:
            raise SimpleError(msgs.ZADD_INCR_LEN_ERROR_MSG)
        # Parse all scores first, before updating
        items = [
            (0.0 + Float.decode(elements[j]) if self.version >= 7 else Float.decode(elements[j]), elements[j + 1])
            for j in range(0, len(elements), 2)
        ]
        old_len = len(zset)
        changed_items = 0

        if param_val['incr']:
            item_score, item_name = items[0]
            if (param_val['nx'] and item_name in zset) or (param_val['xx'] and item_name not in zset):
                return None
            return self.zincrby(key, item_score, item_name)

        for item_score, item_name in items:
            if (
                    (param_val['nx'] and item_name not in zset)
                    or (param_val['xx'] and item_name in zset)
                    or (param_val['gt'] and ((item_name in zset and zset.get(item_name) < item_score)
                                             or (not param_val['xx'] and item_name not in zset)))
                    or (param_val['lt'] and ((item_name in zset and zset.get(item_name) > item_score)
                                             or (not param_val['xx'] and item_name not in zset)))
                    or ([param_val['nx'], param_val['gt'], param_val['lt'], param_val['xx']].count(True) == 0)
            ):
                if zset.add(item_name, item_score):
                    changed_items += 1

        if changed_items:
            key.updated()

        if param_val['ch']:
            return changed_items
        return len(zset) - old_len

    @command((Key(ZSet),))
    def zcard(self, key):
        return len(key.value)

    @command((Key(ZSet), ScoreTest, ScoreTest))
    def zcount(self, key, min, max):
        return key.value.zcount(min.lower_bound, max.upper_bound)

    @command((Key(ZSet), Float, bytes))
    def zincrby(self, key, increment, member):
        # Can't just default the old score to 0.0, because in IEEE754, adding
        # 0.0 to something isn't a nop (e.g. 0.0 + -0.0 == 0.0).
        try:
            score = key.value.get(member, None) + increment
        except TypeError:
            score = increment
        if math.isnan(score):
            raise SimpleError(msgs.SCORE_NAN_MSG)
        key.value[member] = score
        key.updated()
        # For some reason, here it does not ignore the version
        # https://github.com/cunla/fakeredis-py/actions/runs/3377186364/jobs/5605815202
        return Float.encode(score, False)
        # return self._encodefloat(score, False)

    @command((Key(ZSet), StringTest, StringTest))
    def zlexcount(self, key, min, max):
        return key.value.zlexcount(min.value, min.exclusive, max.value, max.exclusive)

    def _zrange(self, key, start, stop, reverse, *args):
        zset = key.value
        withscores = False
        byscore = False
        for arg in args:
            if casematch(arg, b'withscores'):
                withscores = True
            elif casematch(arg, b'byscore'):
                byscore = True
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if byscore:
            items = zset.irange_score(start.lower_bound, stop.upper_bound, reverse=reverse)
        else:
            start, stop = Int.decode(start.bytes_val), Int.decode(stop.bytes_val)
            start, stop = self._fix_range(start, stop, len(zset))
            if reverse:
                start, stop = len(zset) - stop, len(zset) - start
            items = zset.islice_score(start, stop, reverse)
        items = self._apply_withscores(items, withscores)
        return items

    @command((Key(ZSet), ScoreTest, ScoreTest), (bytes,))
    def zrange(self, key, start, stop, *args):
        return self._zrange(key, start, stop, False, *args)

    @command((Key(ZSet), ScoreTest, ScoreTest), (bytes,))
    def zrevrange(self, key, start, stop, *args):
        return self._zrange(key, start, stop, True, *args)

    def _zrangebylex(self, key, _min, _max, reverse, *args):
        if args:
            if len(args) != 3 or not casematch(args[0], b'limit'):
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            offset = Int.decode(args[1])
            count = Int.decode(args[2])
        else:
            offset = 0
            count = -1
        zset = key.value
        items = zset.irange_lex(_min.value, _max.value,
                                inclusive=(not _min.exclusive, not _max.exclusive),
                                reverse=reverse)
        items = self._limit_items(items, offset, count)
        return items

    @command((Key(ZSet), StringTest, StringTest), (bytes,))
    def zrangebylex(self, key, _min, _max, *args):
        return self._zrangebylex(key, _min, _max, False, *args)

    @command((Key(ZSet), StringTest, StringTest), (bytes,))
    def zrevrangebylex(self, key, _max, _min, *args):
        return self._zrangebylex(key, _min, _max, True, *args)

    def _zrangebyscore(self, key, _min, _max, reverse, *args):
        withscores = False
        offset = 0
        count = -1
        i = 0
        while i < len(args):
            if casematch(args[i], b'withscores'):
                withscores = True
                i += 1
            elif casematch(args[i], b'limit') and i + 2 < len(args):
                offset = Int.decode(args[i + 1])
                count = Int.decode(args[i + 2])
                i += 3
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        zset = key.value
        items = list(zset.irange_score(_min.lower_bound, _max.upper_bound, reverse=reverse))
        items = self._limit_items(items, offset, count)
        items = self._apply_withscores(items, withscores)
        return items

    @command((Key(ZSet), ScoreTest, ScoreTest), (bytes,))
    def zrangebyscore(self, key, _min, _max, *args):
        return self._zrangebyscore(key, _min, _max, False, *args)

    @command((Key(ZSet), ScoreTest, ScoreTest), (bytes,))
    def zrevrangebyscore(self, key, _max, _min, *args):
        return self._zrangebyscore(key, _min, _max, True, *args)

    @command((Key(ZSet), bytes))
    def zrank(self, key, member):
        try:
            return key.value.rank(member)
        except KeyError:
            return None

    @command((Key(ZSet), bytes))
    def zrevrank(self, key, member):
        try:
            return len(key.value) - 1 - key.value.rank(member)
        except KeyError:
            return None

    @command((Key(ZSet), bytes), (bytes,))
    def zrem(self, key, *members):
        old_size = len(key.value)
        for member in members:
            key.value.discard(member)
        deleted = old_size - len(key.value)
        if deleted:
            key.updated()
        return deleted

    @command((Key(ZSet), StringTest, StringTest))
    def zremrangebylex(self, key, min, max):
        items = key.value.irange_lex(min.value, max.value,
                                     inclusive=(not min.exclusive, not max.exclusive))
        return self.zrem(key, *items)

    @command((Key(ZSet), ScoreTest, ScoreTest))
    def zremrangebyscore(self, key, min, max):
        items = key.value.irange_score(min.lower_bound, max.upper_bound)
        return self.zrem(key, *[item[1] for item in items])

    @command((Key(ZSet), Int, Int))
    def zremrangebyrank(self, key, start, stop):
        zset = key.value
        start, stop = self._fix_range(start, stop, len(zset))
        items = zset.islice_score(start, stop)
        return self.zrem(key, *[item[1] for item in items])

    @command((Key(ZSet), Int), (bytes, bytes))
    def zscan(self, key, cursor, *args):
        new_cursor, ans = self._scan(key.value.items(), cursor, *args)
        flat = []
        for (key, score) in ans:
            flat.append(key)
            flat.append(self._encodefloat(score, False))
        return [new_cursor, flat]

    @command((Key(ZSet), bytes))
    def zscore(self, key, member):
        try:
            return self._encodefloat(key.value[member], False)
        except KeyError:
            return None

    @staticmethod
    def _get_zset(value):
        if isinstance(value, set):
            zset = ZSet()
            for item in value:
                zset[item] = 1.0
            return zset
        elif isinstance(value, ZSet):
            return value
        else:
            raise SimpleError(msgs.WRONGTYPE_MSG)

    def _zunioninter(self, func, dest, numkeys, *args):
        if numkeys < 1:
            raise SimpleError(msgs.ZUNIONSTORE_KEYS_MSG)
        if numkeys > len(args):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        aggregate = b'sum'
        sets = []
        for i in range(numkeys):
            item = CommandItem(args[i], self._db, item=self._db.get(args[i]), default=ZSet())
            sets.append(self._get_zset(item.value))
        weights = [1.0] * numkeys

        i = numkeys
        while i < len(args):
            arg = args[i]
            if casematch(arg, b'weights') and i + numkeys < len(args):
                weights = [Float.decode(x) for x in args[i + 1:i + numkeys + 1]]
                i += numkeys + 1
            elif casematch(arg, b'aggregate') and i + 1 < len(args):
                aggregate = casenorm(args[i + 1])
                if aggregate not in (b'sum', b'min', b'max'):
                    raise SimpleError(msgs.SYNTAX_ERROR_MSG)
                i += 2
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)

        out_members = set(sets[0])
        for s in sets[1:]:
            if func == 'ZUNIONSTORE':
                out_members |= set(s)
            else:
                out_members.intersection_update(s)

        # We first build a regular dict and turn it into a ZSet. The
        # reason is subtle: a ZSet won't update a score from -0 to +0
        # (or vice versa) through assignment, but a regular dict will.
        out = {}
        # The sort affects the order of floating-point operations.
        # Note that redis uses qsort(1), which has no stability guarantees,
        # so we can't be sure to match it in all cases.
        for s, w in sorted(zip(sets, weights), key=lambda x: len(x[0])):
            for member, score in s.items():
                score *= w
                # Redis only does this step for ZUNIONSTORE. See
                # https://github.com/antirez/redis/issues/3954.
                if func == 'ZUNIONSTORE' and math.isnan(score):
                    score = 0.0
                if member not in out_members:
                    continue
                if member in out:
                    old = out[member]
                    if aggregate == b'sum':
                        score += old
                        if math.isnan(score):
                            score = 0.0
                    elif aggregate == b'max':
                        score = max(old, score)
                    elif aggregate == b'min':
                        score = min(old, score)
                    else:
                        assert False  # pragma: nocover
                if math.isnan(score):
                    score = 0.0
                out[member] = score

        out_zset = ZSet()
        for member, score in out.items():
            out_zset[member] = score

        dest.value = out_zset
        return len(out_zset)

    @command((Key(), Int, bytes), (bytes,))
    def zunionstore(self, dest, numkeys, *args):
        return self._zunioninter('ZUNIONSTORE', dest, numkeys, *args)

    @command((Key(), Int, bytes), (bytes,))
    def zinterstore(self, dest, numkeys, *args):
        return self._zunioninter('ZINTERSTORE', dest, numkeys, *args)

    @command(name="zmscore", fixed=(Key(ZSet), bytes), repeat=(bytes,))
    def zmscore(self, key: CommandItem, *members: Union[str, bytes]) -> list[Optional[float]]:
        """Get the scores associated with the specified members in the sorted set
        stored at key.

        For every member that does not exist in the sorted set, a nil value
        is returned.
        """
        encoder = functools.partial(
            self._encodefloat,
            humanfriendly=False,
        )
        scores = map(
            lambda score: score if score is None else encoder(score),
            map(key.value.get, members),
        )
        return list(scores)
