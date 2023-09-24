"""Command mixin for emulating `redis-py`'s BF functionality."""
from fakeredis import _helpers as helpers
from fakeredis._commands import command, Key, CommandItem
from fakeredis import _msgs as msgs
import pybloom_live


class BloomFilter(pybloom_live.ScalableBloomFilter):
    pass


class BFCommandsMixin:
    _db: helpers.Database

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
        fixed=(Key(BloomFilter), bytes),
        repeat=(),
    )
    def bf_add(self, key, value: bytes):
        return BFCommandsMixin._bf_add(key, value)

    @command(
        name="BF.MADD",
        fixed=(Key(BloomFilter), bytes),
        repeat=(bytes,),
    )
    def bf_madd(self, key, *values):
        res = list()
        for value in values:
            res.append(BFCommandsMixin._bf_add(key, value))
        return res

    @command(
        name="BF.CARD",
        fixed=(Key(BloomFilter),),
        repeat=(),
    )
    def bf_card(self, key):
        return len(key.value)

    @command(
        name="BF.EXISTS",
        fixed=(Key(BloomFilter), bytes),
        repeat=(),
    )
    def bf_exist(self, key, value: bytes):
        return BFCommandsMixin._bf_exist(key, value)

    @command(
        name="BF.MEXISTS",
        fixed=(Key(BloomFilter), bytes),
        repeat=(bytes,),
    )
    def bf_mexists(self, key, *values: bytes):
        res = list()
        for value in values:
            res.append(BFCommandsMixin._bf_exist(key, value))
        return res
