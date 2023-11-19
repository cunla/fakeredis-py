"""Command mixin for emulating `redis-py`'s cuckoo filter functionality."""
import io

from cuckoo import filter

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import command, Key, CommandItem, Int
from fakeredis._helpers import SimpleError, OK, casematch


class ScalableCuckooFilter(filter.ScalableCuckooFilter):

    def __init__(self, initial_capacity, error_rate, bucket_size=4, max_iterations=500):
        super().__init__(initial_capacity, error_rate, bucket_size, max_iterations)


class CFCommandsMixin:

    @staticmethod
    def _cf_add(key: CommandItem, item: bytes) -> int:
        res = key.value.insert(item)
        key.updated()
        return 0 if res else 1

    @staticmethod
    def _cf_exist(key: CommandItem, item: bytes) -> int:
        return 1 if (item in key.value) else 0

    @command(
        name="CF.ADD",
        fixed=(Key(ScalableCuckooFilter), bytes),
        repeat=(),
    )
    def cf_add(self, key, value: bytes):
        return CFCommandsMixin._cf_add(key, value)

    @command(
        name="CF.ADDNX",
        fixed=(Key(ScalableCuckooFilter), bytes),
        repeat=(),
    )
    def cf_add(self, key, value: bytes):
        if value in key.value:
            return 0
        return CFCommandsMixin._cf_add(key, value)


    @command(
        name="CF.CARD",
        fixed=(Key(ScalableCuckooFilter),),
        repeat=(),
    )
    def cf_card(self, key):
        return len(key.value)

    @command(
        name="CF.EXISTS",
        fixed=(Key(ScalableCuckooFilter), bytes),
        repeat=(),
    )
    def cf_exist(self, key, value: bytes):
        return CFCommandsMixin._cf_exist(key, value)

    @command(
        name="CF.MEXISTS",
        fixed=(Key(ScalableCuckooFilter), bytes),
        repeat=(bytes,),
    )
    def cf_mexists(self, key, *values: bytes):
        res = list()
        for value in values:
            res.append(CFCommandsMixin._cf_exist(key, value))
        return res

    @command(
        name="CF.RESERVE",
        fixed=(Key(), Int,),
        repeat=(bytes,),
        flags=msgs.FLAG_LEAVE_EMPTY_VAL,
    )
    def cf_reserve(self, key: CommandItem, capacity, *args: bytes):
        if key.value is not None:
            raise SimpleError(msgs.ITEM_EXISTS_MSG)
        (bucketsize, maxiterations, expansion), _ = extract_args(args, ("+bucketsize", "+maxiterations", "+expansion"))

        if expansion is None:
            expansion = 1
        key.update(ScalableCuckooFilter(capacity, error_rate, scale))
        return OK

    @command(
        name="BF.INSERT",
        fixed=(Key(),),
        repeat=(bytes,),
    )
    def cf_insert(self, key: CommandItem, *args: bytes):
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
        scale = ScalableCuckooFilter.NO_GROWTH if non_scaling else expansion
        if key.value is None:
            key.value = ScalableCuckooFilter(capacity, error_rate, scale)
        res = list()
        for item in items:
            res.append(self._cf_add(key, item))
        key.updated()
        return res

    @command(
        name="BF.INFO",
        fixed=(Key(),),
        repeat=(bytes,),
    )
    def cf_info(self, key: CommandItem, *args: bytes):
        if key.value is None or type(key.value) is not ScalableCuckooFilter:
            raise SimpleError('...')
        if len(args) > 1:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if len(args) == 0:
            return [
                b'Capacity', key.value.capacity,
                b'Size', key.value.capacity,
                b'Number of filters', len(key.value.filters),
                b'Number of items inserted', key.value.count,
                b'Expansion rate', key.value.scale if key.value.scale > 0 else None,
            ]
        if casematch(args[0], b'CAPACITY'):
            return key.value.capacity
        elif casematch(args[0], b'SIZE'):
            return key.value.capacity
        elif casematch(args[0], b'FILTERS'):
            return len(key.value.filters)
        elif casematch(args[0], b'ITEMS'):
            return key.value.count
        elif casematch(args[0], b'EXPANSION'):
            return key.value.scale if key.value.scale > 0 else None
        else:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)

    @command(
        name="BF.SCANDUMP",
        fixed=(Key(), Int,),
        repeat=(),
        flags=msgs.FLAG_LEAVE_EMPTY_VAL,
    )
    def cf_scandump(self, key: CommandItem, iterator: int):
        if key.value is None:
            raise SimpleError(msgs.NOT_FOUND_MSG)
        f = io.BytesIO()

        if iterator == 0:
            key.value.tofile(f)
            f.seek(0)
            s = f.read()
            f.close()
            return [1, s]
        else:
            return [0, None]

    @command(
        name="BF.LOADCHUNK",
        fixed=(Key(), Int, bytes),
        repeat=(),
        flags=msgs.FLAG_LEAVE_EMPTY_VAL,
    )
    def cf_loadchunk(self, key: CommandItem, iterator: int, data: bytes):
        if key.value is not None and type(key.value) is not ScalableCuckooFilter:
            raise SimpleError(msgs.NOT_FOUND_MSG)
        f = io.BytesIO(data)
        key.value = ScalableCuckooFilter.fromfile(f)
        f.close()
        key.updated()
        return OK
