from probables import CountingCuckooFilter, CuckooFilterFullError

from ._base_type import BaseModel


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
