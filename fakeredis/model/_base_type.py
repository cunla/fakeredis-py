from __future__ import annotations

import functools
from typing import Any


class BaseModel:
    _model_type: bytes

    @classmethod
    def model_type(cls) -> bytes:
        return cls._model_type


@functools.total_ordering
class BeforeAny:
    def __gt__(self, other: Any) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, BeforeAny)

    def __hash__(self) -> int:
        return 1


@functools.total_ordering
class AfterAny:
    def __lt__(self, other: Any) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AfterAny)

    def __hash__(self) -> int:
        return 1
