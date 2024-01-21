"""Command mixin for emulating `redis-py`'s Count-min sketch functionality."""

import probables

from fakeredis._commands import command, CommandItem, Int, Key, Float


class CountMinSketch(probables.CountMinSketch):
    pass


class CFCommandsMixin:

    @command(
        name="CMS.INCRBY",
        fixed=(Key(CountMinSketch), bytes, bytes),
        repeat=(bytes, bytes,),
    )
    def cf_add(self, key: CommandItem, *args: bytes):
        raise NotImplementedError()

    @command(
        name="CMS.INFO",
        fixed=(Key(CountMinSketch)),
        repeat=(),
    )
    def cf_addnx(self, key: CommandItem):
        raise NotImplementedError()

    @command(
        name="CMS.INITBYDIM",
        fixed=(Key(CountMinSketch), Int, Int),
        repeat=(),
    )
    def cms_initbydim(self, key: CommandItem, width: int, depth: int):
        raise NotImplementedError()

    @command(
        name="CMS.INITBYPROB",
        fixed=(Key(CountMinSketch), Float, Float),
        repeat=(),
    )
    def cms_initby_prob(self, key: CommandItem, error_rate: float, probability: float):
        raise NotImplementedError()

    @command(
        name="CMS.MERGE",
        fixed=(Key(CountMinSketch), Int, bytes),
        repeat=(bytes,),
    )
    def cms_merge(self, key: CommandItem, num_keys: int, *args: bytes):
        raise NotImplementedError()

    @command(
        name="CMS.QUERY",
        fixed=(Key(CountMinSketch), bytes),
        repeat=(bytes),
    )
    def cms_query(self, key: CommandItem, *items: bytes):
        raise NotImplementedError()
