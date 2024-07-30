"""Command mixin for emulating `redis-py`'s top-k functionality."""

import heapq
import random
import time
from typing import Any, List, Optional, Tuple

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import Key, Int, Float, command, CommandItem
from fakeredis._helpers import OK, SimpleError, SimpleString


class Bucket(object):
    def __init__(self, counter: int, fingerprint: int):
        self.counter = counter
        self.fingerprint = fingerprint

    def add(self, fingerprint: int, incr: int, decay: float) -> int:
        if self.fingerprint == fingerprint:
            self.counter += incr
            return self.counter
        elif self._decay(decay):
            self.counter += incr
            self.fingerprint = fingerprint
            return self.counter
        return 0

    def count(self, fingerprint: int) -> int:
        if self.fingerprint == fingerprint:
            return self.counter
        return 0

    def _decay(self, decay: float) -> bool:
        if self.counter > 0:
            probability = decay**self.counter
            if probability >= 1 or random.random() < probability:
                self.counter -= 1
        return self.counter == 0


class HashArray(object):
    def __init__(self, width: int, decay: float):
        self.width = width
        self.decay = decay
        self.array = [Bucket(0, 0) for _ in range(width)]
        self._seed = random.getrandbits(32)

    def count(self, item: bytes) -> int:
        return self.get_bucket(item).count(self._hash(item))

    def add(self, item: bytes, incr: int) -> int:
        bucket = self.get_bucket(item)
        return bucket.add(self._hash(item), incr, self.decay)

    def get_bucket(self, item: bytes) -> Bucket:
        return self.array[self._hash(item) % self.width]

    def _hash(self, item: bytes) -> int:
        return hash(item) ^ self._seed


class HeavyKeeper(object):
    is_topk_initialized = False

    def __init__(self, k: int, width: int = 1024, depth: int = 5, decay: float = 0.9) -> None:
        if not HeavyKeeper.is_topk_initialized:
            random.seed(time.time())
        self.k = k
        self.width = width
        self.depth = depth
        self.decay = decay
        self.hash_arrays = [HashArray(width, decay) for _ in range(depth)]
        self.min_heap: List[Tuple[int, bytes]] = list()

    def _index(self, val: bytes) -> int:
        for ind, item in enumerate(self.min_heap):
            if item[1] == val:
                return ind
        return -1

    def add(self, item: bytes, incr: int) -> Optional[bytes]:
        max_count = 0
        for i in range(self.depth):
            count = self.hash_arrays[i].add(item, incr)
            max_count = max(max_count, count)
        if len(self.min_heap) < self.k:
            heapq.heappush(self.min_heap, (max_count, item))
            return None
        ind = self._index(item)
        if ind >= 0:
            self.min_heap[ind] = (max_count, item)
            heapq.heapify(self.min_heap)
            return None
        if max_count > self.min_heap[0][0]:
            expelled = heapq.heapreplace(self.min_heap, (max_count, item))
            return expelled[1]
        return None

    def count(self, item: bytes) -> int:
        ind = self._index(item)
        if ind > 0:
            return self.min_heap[ind][0]
        return max([ha.count(item) for ha in self.hash_arrays])

    def list(self, k: Optional[int] = None) -> List[Tuple[int, bytes]]:
        sorted_list = sorted(self.min_heap, key=lambda x: x[0], reverse=True)
        if k is None:
            return sorted_list
        return sorted_list[:k]


class TopkCommandsMixin:
    """`CommandsMixin` for enabling TopK compatibility in `fakeredis`."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @command(name="TOPK.ADD", fixed=(Key(HeavyKeeper), bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def topk_add(self, key: CommandItem, *args: bytes) -> List[Optional[bytes]]:
        if key.value is None:
            raise SimpleError("TOPK: key does not exist")
        if not isinstance(key.value, HeavyKeeper):
            raise SimpleError("TOPK: key is not a HeavyKeeper")
        res = [key.value.add(_item, 1) for _item in args]
        key.updated()
        return res

    @command(name="TOPK.COUNT", fixed=(Key(HeavyKeeper), bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def topk_count(self, key: CommandItem, *args: bytes) -> List[int]:
        if key.value is None:
            raise SimpleError("TOPK: key does not exist")
        if not isinstance(key.value, HeavyKeeper):
            raise SimpleError("TOPK: key is not a HeavyKeeper")
        res: List[int] = [key.value.count(_item) for _item in args]
        return res

    @command(name="TOPK.QUERY", fixed=(Key(HeavyKeeper), bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def topk_query(self, key: CommandItem, *args: bytes) -> List[int]:
        if key.value is None:
            raise SimpleError("TOPK: key does not exist")
        if not isinstance(key.value, HeavyKeeper):
            raise SimpleError("TOPK: key is not a HeavyKeeper")
        topk = {item[1] for item in key.value.list()}
        res: List[int] = [1 if _item in topk else 0 for _item in args]
        return res

    @command(name="TOPK.INCRBY", fixed=(Key(), bytes, Int), repeat=(bytes, Int), flags=msgs.FLAG_DO_NOT_CREATE)
    def topk_incrby(self, key: CommandItem, *args: Any) -> List[Optional[bytes]]:
        if key.value is None:
            raise SimpleError("TOPK: key does not exist")
        if not isinstance(key.value, HeavyKeeper):
            raise SimpleError("TOPK: key is not a HeavyKeeper")
        if len(args) % 2 != 0:
            raise SimpleError("TOPK: number of arguments must be even")
        res = list()
        for i in range(0, len(args), 2):
            val, count = args[i], int(args[i + 1])
            res.append(key.value.add(val, count))
        key.updated()
        return res

    @command(name="TOPK.INFO", fixed=(Key(),), repeat=(), flags=msgs.FLAG_DO_NOT_CREATE)
    def topk_info(self, key: CommandItem) -> List[Any]:
        if key.value is None:
            raise SimpleError("TOPK: key does not exist")
        if not isinstance(key.value, HeavyKeeper):
            raise SimpleError("TOPK: key is not a HeavyKeeper")
        return [
            b"k",
            key.value.k,
            b"width",
            key.value.width,
            b"depth",
            key.value.depth,
            b"decay",
            key.value.decay,
        ]

    @command(name="TOPK.LIST", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def topk_list(self, key: CommandItem, *args: Any) -> List[Any]:
        (withcount,), _ = extract_args(args, ("withcount",))
        if key.value is None:
            raise SimpleError("TOPK: key does not exist")
        if not isinstance(key.value, HeavyKeeper):
            raise SimpleError("TOPK: key is not a HeavyKeeper")
        value_list: List[Tuple[int, bytes]] = key.value.list()
        if not withcount:
            return [item[1] for item in value_list]
        else:
            temp = [[item[1], item[0]] for item in value_list]
            return [item for sublist in temp for item in sublist]

    @command(name="TOPK.RESERVE", fixed=(Key(), Int), repeat=(Int, Int, Float), flags=msgs.FLAG_DO_NOT_CREATE)
    def topk_reserve(self, key: CommandItem, topk: int, *args: Any) -> SimpleString:
        if len(args) == 3:
            width, depth, decay = args
        else:
            width, depth, decay = 8, 7, 0.9
        if key.value is not None:
            raise SimpleError("TOPK: key already set")
        key.update(HeavyKeeper(topk, width, depth, decay))
        return OK
