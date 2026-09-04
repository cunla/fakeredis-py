from __future__ import annotations

from typing import Any

import valkey

from ._connection import FakeBaseConnection, FakeRedisMixin
from ._typing import Self
from .aioredis import FakeAsyncRedisMixin, FakeBaseAsyncConnection


def _validate_server_type(args_dict: dict[str, Any]) -> None:
    if "server_type" in args_dict and args_dict["server_type"] != "valkey":
        raise ValueError("server_type must be valkey")
    args_dict.setdefault("server_type", "valkey")
    args_dict.setdefault("client_class", valkey.Valkey)
    args_dict.setdefault("connection_class", FakeValkeyConnection)
    args_dict.setdefault("connection_pool_class", valkey.ConnectionPool)


class FakeValkeyConnection(FakeBaseConnection, valkey.Connection):
    _connection_error_class = valkey.ConnectionError


class FakeAysncValkeyConnection(FakeBaseAsyncConnection, valkey.asyncio.Connection):
    _connection_error_class = valkey.ConnectionError


class FakeValkey(FakeRedisMixin, valkey.Valkey):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _validate_server_type(kwargs)
        super().__init__(*args, **kwargs)

    @classmethod
    def from_url(cls, *args: Any, **kwargs: Any) -> Self:
        return super().from_url(*args, **kwargs)


class FakeStrictValkey(FakeRedisMixin, valkey.StrictValkey):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _validate_server_type(kwargs)
        super().__init__(*args, **kwargs)

    @classmethod
    def from_url(cls, *args: Any, **kwargs: Any) -> Self:
        return super().from_url(*args, **kwargs)


class FakeAsyncValkey(FakeAsyncRedisMixin, valkey.asyncio.Valkey):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("client_class", valkey.asyncio.Valkey)
        kwargs.setdefault("connection_class", FakeAysncValkeyConnection)
        kwargs.setdefault("connection_pool_class", valkey.asyncio.ConnectionPool)
        _validate_server_type(kwargs)
        super().__init__(*args, **kwargs)

    @classmethod
    def from_url(cls, *args: Any, **kwargs: Any) -> Self:
        return super().from_url(*args, **kwargs)
