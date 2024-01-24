"""Command mixin for emulating `redis-py`'s Count-min sketch functionality."""

import probables

from fakeredis import _msgs as msgs
from fakeredis._commands import command, CommandItem, Int, Key, Float
from fakeredis._helpers import OK, SimpleString, SimpleError


class CountMinSketch(probables.CountMinSketch):
    def __init__(self, width: int = None, depth: int = None, probability: float = None, error_rate: float = None):
        super().__init__(width=width, depth=depth, error_rate=error_rate, confidence=probability)


class CMSCommandsMixin:

    @command(
        name="CMS.INCRBY",
        fixed=(Key(CountMinSketch), bytes, bytes),
        repeat=(bytes, bytes,),
        flags=msgs.FLAG_NO_INITIATE,
    )
    def cms_incrby(self, key: CommandItem, *args: bytes):
        if key.value is None:
            raise SimpleError("CMS: key does not exist")
        if len(args) % 2 != 0 or len(args) == 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("cms.incrby"))
        pairs = []
        for i in range(0, len(args), 2):
            try:
                pairs.append((args[i], int(args[i + 1])))
            except ValueError:
                raise SimpleError("CMS: Cannot parse number")
        res = []
        for pair in pairs:
            res.append(key.value.add(pair[0], pair[1]))
        key.updated()
        return res

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
        flags=msgs.FLAG_NO_INITIATE,
    )
    def cms_initbydim(self, key: CommandItem, width: int, depth: int) -> SimpleString:
        if key.value is not None:
            raise SimpleError("CMS key already set")
        if width < 1:
            raise SimpleError("CMS: invalid width")
        if depth < 1:
            raise SimpleError("CMS: invalid depth")
        key.update(CountMinSketch(width=width, depth=depth))
        return OK

    @command(
        name="CMS.INITBYPROB",
        fixed=(Key(CountMinSketch), Float, Float),
        repeat=(),
        flags=msgs.FLAG_NO_INITIATE,
    )
    def cms_initby_prob(self, key: CommandItem, error_rate: float, probability: float) -> SimpleString:
        if key.value is not None:
            raise SimpleError("CMS key already set")
        if error_rate <= 0 or error_rate >= 1:
            raise SimpleError("CMS: invalid overestimation value")
        if probability <= 0 or probability >= 1:
            raise SimpleError("CMS: invalid prob value")
        key.update(CountMinSketch(probability=probability, error_rate=error_rate))
        return OK

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
        repeat=(bytes,),
    )
    def cms_query(self, key: CommandItem, *items: bytes):
        if key.value is None:
            raise SimpleError("CMS: key does not exist")
        return [key.value.check(item) for item in items]
