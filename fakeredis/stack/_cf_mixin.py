"""Command mixin for emulating `redis-py`'s cuckoo filter functionality."""
import io

from cuckoo import filter

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import command, CommandItem, Int, Key
from fakeredis._helpers import SimpleError, OK, casematch


class ScalableCuckooFilter(filter.ScalableCuckooFilter):

    def __init__(self, initial_capacity, error_rate=None, bucket_size=2, max_iterations=20, scale=1):
        super().__init__(initial_capacity, error_rate, bucket_size, max_iterations)
        self.inserted = 0
        self.deleted = 0
        self.scale = scale

    @property
    def capacity(self):
        return sum([filter.capacity for filter in self.filters])

    @property
    def size(self):
        return sum([filter.size for filter in self.filters])

    @property
    def bucket_size(self):
        return self.filters[0].bucket_size

    @property
    def buckets_count(self):
        return sum([int(filter.capacity / filter.bucket_size) for filter in self.filters])

    def insert(self, item):
        ScalableCuckooFilter.SCALE_FACTOR = self.scale
        res = super().insert(item)
        self.inserted += (1 if res else 0)
        return res

    def delete(self, item):
        res = super().delete(item)
        self.deleted += (1 if res else 0)
        return res

    @property
    def max_iterations(self):
        return self.filters[0].max_kicks


class CFCommandsMixin:

    @staticmethod
    def _cf_add(key: CommandItem, item: bytes) -> int:
        if key.value is None:
            key.update(ScalableCuckooFilter(1024))
        res = key.value.insert(item)
        key.updated()
        return 1 if res else 0

    @staticmethod
    def _cf_exist(key: CommandItem, item: bytes) -> int:
        return 1 if (item in key.value) else 0

    @command(
        name="CF.ADD",
        fixed=(Key(ScalableCuckooFilter), bytes),
        repeat=(),
    )
    def cf_add(self, key: CommandItem, value: bytes):
        return CFCommandsMixin._cf_add(key, value)

    @command(
        name="CF.ADDNX",
        fixed=(Key(ScalableCuckooFilter), bytes),
        repeat=(),
    )
    def cf_addnx(self, key: CommandItem, value: bytes):
        if value in key.value:
            return 0
        return CFCommandsMixin._cf_add(key, value)

    @command(
        name="CF.COUNT",
        fixed=(Key(ScalableCuckooFilter), bytes),
        repeat=(),
    )
    def cf_count(self, key: CommandItem, item: bytes):
        return 1 if self._cf_exist(key, item) else 0  # todo

    @command(
        name="CF.DEL",
        fixed=(Key(ScalableCuckooFilter), bytes),
        repeat=(),
    )
    def cf_del(self, key: CommandItem, value: bytes):
        if key.value is None:
            raise SimpleError(msgs.NOT_FOUND_MSG)
        res = key.value.delete(value)
        return 1 if res else 0

    @command(
        name="CF.EXISTS",
        fixed=(Key(ScalableCuckooFilter), bytes),
        repeat=(),
    )
    def cf_exist(self, key: CommandItem, value: bytes):
        return CFCommandsMixin._cf_exist(key, value)

    @command(
        name="CF.INFO",
        fixed=(Key(),),
        repeat=(),
    )
    def cf_info(self, key: CommandItem):
        if key.value is None or type(key.value) is not ScalableCuckooFilter:
            raise SimpleError('...')
        return [
            b'Size', key.value.capacity,
            b'Number of buckets', key.value.buckets_count,
            b'Number of filters', len(key.value.filters),
            b'Number of items inserted', key.value.inserted,
            b'Number of items deleted', key.value.deleted,
            b'Bucket size', key.value.bucket_size,
            b'Max iterations', key.value.max_iterations,
            b'Expansion rate', key.value.scale if key.value.scale > 0 else None,
        ]

    @command(
        name="CF.INSERT",
        fixed=(Key(),),
        repeat=(bytes,),
    )
    def cf_insert(self, key: CommandItem, *args: bytes):
        (capacity, no_create), left_args = extract_args(
            args, ("+capacity", "nocreate"),
            error_on_unexpected=False, left_from_first_unexpected=True)
        # if no_create and (capacity is not None or error_rate is not None):
        #     raise SimpleError("...")
        if len(left_args) < 2 or not casematch(left_args[0], b'items'):
            raise SimpleError("...")
        items = left_args[1:]
        capacity = capacity or 1024

        if key.value is None and no_create:
            raise SimpleError(msgs.NOT_FOUND_MSG)
        if key.value is None:
            key.value = ScalableCuckooFilter(capacity)
        res = list()
        for item in items:
            res.append(self._cf_add(key, item))
        key.updated()
        return res

    @command(
        name="CF.INSERTNX",
        fixed=(Key(),),
        repeat=(bytes,),
    )
    def cf_insertnx(self, key: CommandItem, *args: bytes):
        (capacity, no_create), left_args = extract_args(
            args, ("+capacity", "nocreate"),
            error_on_unexpected=False, left_from_first_unexpected=True)
        # if no_create and (capacity is not None or error_rate is not None):
        #     raise SimpleError("...")
        if len(left_args) < 2 or not casematch(left_args[0], b'items'):
            raise SimpleError("...")
        items = left_args[1:]
        capacity = capacity or 1024
        if key.value is None and no_create:
            raise SimpleError(msgs.NOT_FOUND_MSG)
        if key.value is None:
            key.value = ScalableCuckooFilter(capacity, None)
        res = list()
        for item in items:
            if item in key.value:
                res.append(0)
            else:
                res.append(self._cf_add(key, item))
        key.updated()
        return res

    @command(
        name="CF.MEXISTS",
        fixed=(Key(ScalableCuckooFilter), bytes),
        repeat=(bytes,),
    )
    def cf_mexists(self, key: CommandItem, *values: bytes):
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
    def cf_reserve(self, key: CommandItem, capacity: int, *args: bytes):
        if key.value is not None:
            raise SimpleError(msgs.ITEM_EXISTS_MSG)
        (bucketsize, maxiterations, expansion), _ = extract_args(args, ("+bucketsize", "+maxiterations", "+expansion"))

        maxiterations = maxiterations or 20
        bucketsize = bucketsize or 2
        value = ScalableCuckooFilter(capacity, None, bucket_size=bucketsize, max_iterations=maxiterations)
        key.update(value)
        return OK

    @command(
        name="CF.SCANDUMP",
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
        name="CF.LOADCHUNK",
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
