from __future__ import annotations

import probables

from ._base_type import BaseModel


class CountMinSketch(probables.CountMinSketch, BaseModel):
    _model_type = b"CMSk-TYPE"

    def __init__(
        self,
        width: int | None = None,
        depth: int | None = None,
        probability: float | None = None,
        error_rate: float | None = None,
    ):
        super().__init__(width=width, depth=depth, error_rate=error_rate, confidence=probability)
