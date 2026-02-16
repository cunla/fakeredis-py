from typing import Any

from probables import CountingCuckooFilter, CuckooFilterFullError, ExpandingBloomFilter

from fakeredis import _msgs as msgs
from ._base_type import BaseModel
from .._helpers import SimpleError


class ScalableBloomFilter(ExpandingBloomFilter, BaseModel):
    NO_GROWTH = 0
    _model_type = b"MBbloom--"

    def __init__(self, capacity: int = 100, error_rate: float = 0.001, scale: int = 2):
        super().__init__(capacity, error_rate)
        self.scale: int = scale

    def add_item(self, key: bytes) -> bool:
        if key in self:
            return True
        if self.scale == self.NO_GROWTH and self.elements_added >= self.estimated_elements:
            raise SimpleError(msgs.FILTER_FULL_MSG)
        super(ScalableBloomFilter, self).add(key)
        return False

    @classmethod
    def bf_frombytes(cls, b: bytes, **kwargs: Any) -> "ScalableBloomFilter":
        size, est_els, added_els, fpr = cls._parse_footer(b)
        blm = ScalableBloomFilter(capacity=est_els, error_rate=fpr)
        blm._parse_blooms(b, size)
        blm._added_elements = added_els
        return blm


class ScalableCuckooFilter(CountingCuckooFilter, BaseModel):
    _model_type = b"MBbloomCF"

    def __init__(self, capacity: int, bucket_size: int = 2, max_iterations: int = 20, expansion: int = 1):
        super().__init__(capacity, bucket_size, max_iterations, expansion)
        self.initial_capacity: int = capacity
        self.inserted: int = 0
        self.deleted: int = 0

    def insert(self, item: bytes) -> bool:
        try:
            super().add(item)
        except CuckooFilterFullError:
            return False
        self.inserted += 1
        return True

    def count(self, item: bytes) -> int:
        return super().check(item)

    def delete(self, item: bytes) -> bool:
        if super().remove(item):
            self.deleted += 1
            return True
        return False
