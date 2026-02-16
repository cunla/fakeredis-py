from typing import Optional

import probables

from ._base_type import BaseModel


class CountMinSketch(probables.CountMinSketch, BaseModel):
    _model_type = b"CMSk-TYPE"

    def __init__(
        self,
        width: Optional[int] = None,
        depth: Optional[int] = None,
        probability: Optional[float] = None,
        error_rate: Optional[float] = None,
    ):
        super().__init__(width=width, depth=depth, error_rate=error_rate, confidence=probability)
