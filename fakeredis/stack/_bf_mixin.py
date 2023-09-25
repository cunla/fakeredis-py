"""Command mixin for emulating `redis-py`'s BF functionality."""
import pybloom_live

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import command, Key, CommandItem, Float, Int
from fakeredis._helpers import SimpleError, OK, casematch


class ScalableBloomFilter(pybloom_live.ScalableBloomFilter):
    NO_GROWTH = 0

    def add(self, key):
        if key in self:
            return True
        if self.scale == self.NO_GROWTH and self.filters and self.filters[-1].count >= self.filters[-1].capacity:
            raise SimpleError(msgs.FILTER_FULL_MSG)
        return super(ScalableBloomFilter, self).add(key)


class BFCommandsMixin:

    @staticmethod
    def _bf_add(key: CommandItem, item: bytes) -> int:
        res = key.value.add(item)
        key.updated()
        return 0 if res else 1

    @staticmethod
    def _bf_exist(key: CommandItem, item: bytes) -> int:
        return 1 if (item in key.value) else 0

    @command(
        name="BF.ADD",
        fixed=(Key(ScalableBloomFilter), bytes),
        repeat=(),
    )
    def bf_add(self, key, value: bytes):
        return BFCommandsMixin._bf_add(key, value)

    @command(
        name="BF.MADD",
        fixed=(Key(ScalableBloomFilter), bytes),
        repeat=(bytes,),
    )
    def bf_madd(self, key, *values):
        res = list()
        for value in values:
            res.append(BFCommandsMixin._bf_add(key, value))
        return res

    @command(
        name="BF.CARD",
        fixed=(Key(ScalableBloomFilter),),
        repeat=(),
    )
    def bf_card(self, key):
        return len(key.value)

    @command(
        name="BF.EXISTS",
        fixed=(Key(ScalableBloomFilter), bytes),
        repeat=(),
    )
    def bf_exist(self, key, value: bytes):
        return BFCommandsMixin._bf_exist(key, value)

    @command(
        name="BF.MEXISTS",
        fixed=(Key(ScalableBloomFilter), bytes),
        repeat=(bytes,),
    )
    def bf_mexists(self, key, *values: bytes):
        res = list()
        for value in values:
            res.append(BFCommandsMixin._bf_exist(key, value))
        return res

    @command(
        name="BF.RESERVE",
        fixed=(Key(), Float, Int,),
        repeat=(bytes,),
        flags=msgs.FLAG_LEAVE_EMPTY_VAL,
    )
    def bf_reserve(self, key: CommandItem, error_rate, capacity, *args: bytes):
        if key.value is not None:
            raise SimpleError(msgs.ITEM_EXISTS_MSG)
        (expansion, non_scaling), _ = extract_args(args, ("+expansion", "nonscaling"))
        if expansion is not None and non_scaling:
            raise SimpleError(msgs.NONSCALING_FILTERS_CANNOT_EXPAND_MSG)
        if expansion is None:
            expansion = 2
        scale = ScalableBloomFilter.NO_GROWTH if non_scaling else expansion
        key.update(ScalableBloomFilter(capacity, error_rate, scale))
        return OK

    @command(
        name="BF.INSERT",
        fixed=(Key(),),
        repeat=(bytes,),
    )
    def bf_insert(self, key: CommandItem, *args: bytes):
        (capacity, error_rate, expansion, non_scaling, no_create), left_args = extract_args(
            args, ("+capacity", ".error", "+expansion", "nonscaling", "nocreate"),
            error_on_unexpected=False, left_from_first_unexpected=True)
        # if no_create and (capacity is not None or error_rate is not None):
        #     raise SimpleError("...")
        if len(left_args) < 2 or not casematch(left_args[0], b'items'):
            raise SimpleError("...")
        items = left_args[1:]

        error_rate = error_rate or 0.001
        capacity = capacity or 100
        if key.value is None and no_create:
            raise SimpleError(msgs.NOT_FOUND_MSG)
        if expansion is not None and non_scaling:
            raise SimpleError(msgs.NONSCALING_FILTERS_CANNOT_EXPAND_MSG)
        if expansion is None:
            expansion = 2
        scale = ScalableBloomFilter.NO_GROWTH if non_scaling else expansion
        if key.value is None:
            key.value = ScalableBloomFilter(capacity, error_rate, scale)
        res = list()
        for item in items:
            res.append(self._bf_add(key, item))
        key.updated()
        return res
