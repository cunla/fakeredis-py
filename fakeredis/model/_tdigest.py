from sortedcontainers import SortedList

from ._base_type import BaseModel


class TDigest(SortedList, BaseModel):
    _model_type = b"TDIS-TYPE"

    def __init__(self, compression: int = 100):
        super().__init__()
        self.compression = compression
