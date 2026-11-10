import time
from typing import AnyStr


def current_time() -> int:
    """Return current_time in ms"""
    return int(time.time() * 1000)


def asbytes(value: AnyStr) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    return value


class SimpleError(Exception):
    """Exception that will be turned into a frontend-specific exception."""

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("SimpleError value must be str")
        self.value = value
