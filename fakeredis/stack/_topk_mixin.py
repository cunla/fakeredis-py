"""Command mixin for emulating `redis-py`'s top-k functionality."""
import heapq
import random
from collections import Counter
from typing import Any, Tuple, List, Optional

from fakeredis._commands import Key, Int, Float, command
from fakeredis._helpers import OK


class TopkCommandsMixin:
    """`CommandsMixin` for enabling TopK compatibility in `fakeredis`."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @command(name="TOPK.ADD", fixed=(Key(), bytes,), repeat=(bytes,), )
    def topk_add(self, key, *args):
        return OK  # todo

    @command(name="TOPK.QUERY", fixed=(Key(), bytes,), repeat=(bytes,), )
    def topk_add(self, key, *args):
        return OK  # todo

    @command(name="TOPK.INFO", fixed=(Key(),), repeat=(), )
    def topk_info(self, key):
        return OK  # todo

    @command(name="TOPK.LIST", fixed=(Key(),), repeat=(bytes,), )
    def topk_list(self, key, *args):
        return OK  # todo

    @command(name="TOPK.INCRBY", fixed=(Key(), bytes, Int,), repeat=(bytes, Int), )
    def topk_incrby(self, key, *args):
        return OK  # todo

    @command(name="TOPK.RESERVE", fixed=(Key(), Int,), repeat=(Int, Int, Float,), )
    def topk_reserve(self, key, topk, width, depth, decay):
        return OK  # todo


class HeavyKeeper:
    def __init__(self, k: int, width: int = 8, depth: int = 7, decay: float = 0.9):
        self._memomask = {}
        self.k = k
        self.width = width
        self.depth = depth
        self.decay = decay
        self.buckets: List[List[Optional[Tuple[int, int]]]] = [[None for _ in range(width)] for _ in
                                                               range(depth)]
        self.top_flows: List = []

    def _index(self, val: bytes) -> int:
        for ind, item in enumerate(self.top_flows):
            if item[1] == val:
                return ind
        return -1

    def query(self, val: bytes) -> bool:
        return self._index(val) >= 0

    def count(self, val: bytes) -> int:
        ind = self._index(val)
        return self.top_flows[ind][0] if ind >= 0 else 0

    def hash_function(self, n: int, val: bytes) -> int:
        mask = self._memomask.get(n)
        if mask is None:
            random.seed(n)
            mask = self._memomask[n] = random.getrandbits(32)
        return hash(val) ^ mask

    def add(self, val: bytes, incr: int) -> Tuple[Optional[bytes], bool]:
        val_fingerprint = self.hash_function(-1, val)
        max_count = 0
        for i in range(self.depth):
            row = self.buckets[i]
            bucket_number: int = int(self.hash_function(i, val)) % self.width
            curr_value = row[bucket_number]
            curr_fingerprint = curr_value[1] if curr_value is not None else None
            curr_count = curr_value[0] if curr_value is not None else 0

            if curr_count == 0 or curr_fingerprint is None:
                row[bucket_number] = (incr, val_fingerprint)
                max_count = max(max_count, incr)
            elif curr_fingerprint == val_fingerprint:
                row[bucket_number] = (curr_count + incr, val_fingerprint)
                max_count = max(max_count, curr_count + incr)
            else:
                for _ in range(incr):  # for every value of incr, we need to check if we need to decay
                    curr_count = row[bucket_number][0]
                    decay = self.decay ** curr_count
                    rand_val = random.random()
                    if rand_val < decay:
                        row[bucket_number] = (curr_count - 1, curr_fingerprint)
                        if curr_count == 1:
                            row[bucket_number] = (1, val_fingerprint)
                            max_count = max(max_count, 1)
        if len(self.top_flows) < self.k:  # Less than k flows, add the current flow
            self.top_flows.append((max_count, val))
            heapq.heapify(self.top_flows)
            return None, True
        min_val = self.top_flows[0]
        if len(self.top_flows) == self.k and max_count <= min_val[0]:  # current flow is not heavy enough
            return None, False
        item_ind = self._index(val)
        if item_ind >= 0:  # flow already in top k, update its count
            self.top_flows[item_ind] = (max_count, val)
            heapq.heapify(self.top_flows)
            return None, True
        expelled = self.top_flows[0][1]  # flow to be expelled
        # replace the min flow with the current flow
        heapq.heappop(self.top_flows)
        heapq.heappush(self.top_flows, (max_count, val))
        return expelled, True

    def list(self, k: int) -> List[Tuple[bytes, int]]:
        sorted_flows = sorted(self.top_flows, reverse=True)
        return sorted_flows[:k]


if __name__ == '__main__':
    real = Counter()
    heavy_keeper = HeavyKeeper(10)
    random.seed(10)
    for i in range(1000000):
        ip_addr = f'{random.randint(0, 100)}'.encode()
        real[ip_addr] += 1
        heavy_keeper.add(ip_addr, 1)
        if i % 100000 == 0:
            print(heavy_keeper.list(5))
    items = heavy_keeper.list(5)
    for item in items:
        for i, x in enumerate(real.items()):
            if item[1] == x[0]:
                ind = i
                break
        print(item, real[item[1]], ind)
    print(real)
