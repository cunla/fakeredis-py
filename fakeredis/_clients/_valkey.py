from __future__ import annotations

from typing import Any

import valkey

from fakeredis._clients._async import FakeAsyncRedisMixin, FakeBaseAsyncConnection
from fakeredis._clients._sync import FakeBaseConnection, FakeRedisMixin
from fakeredis._typing import Self


def _set_server_type(args_dict: dict[str, Any]) -> None:
    if args_dict.setdefault("server_type", "valkey") != "valkey":
        raise ValueError("server_type must be valkey")


def _validate_server_type(args_dict: dict[str, Any]) -> None:
    _set_server_type(args_dict)
    args_dict.setdefault("client_class", valkey.Valkey)
    args_dict.setdefault("connection_class", FakeValkeyConnection)
    args_dict.setdefault("connection_pool_class", valkey.ConnectionPool)


class FakeValkeyConnection(FakeBaseConnection, valkey.Connection):
    _connection_error_class = valkey.ConnectionError


class FakeAsyncValkeyConnection(FakeBaseAsyncConnection, valkey.asyncio.Connection):
    _connection_error_class = valkey.ConnectionError


class FakeValkey(FakeRedisMixin, valkey.Valkey):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _validate_server_type(kwargs)
        super().__init__(*args, **kwargs)

    @classmethod
    def from_url(cls, *args: Any, **kwargs: Any) -> Self:
        # Set the valkey defaults before the pool is built from the URL: FakeRedisMixin.from_url would otherwise build a
        # redis pool of redis connections for a "redis" server.
        _validate_server_type(kwargs)
        return super().from_url(*args, **kwargs)


class FakeStrictValkey(FakeRedisMixin, valkey.StrictValkey):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _validate_server_type(kwargs)
        super().__init__(*args, **kwargs)

    @classmethod
    def from_url(cls, *args: Any, **kwargs: Any) -> Self:
        # Set the valkey defaults before the pool is built from the URL: FakeRedisMixin.from_url would otherwise build a
        # redis pool of redis connections for a "redis" server.
        _validate_server_type(kwargs)
        return super().from_url(*args, **kwargs)


class FakeAsyncValkey(FakeAsyncRedisMixin, valkey.asyncio.Valkey):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("client_class", valkey.asyncio.Valkey)
        kwargs.setdefault("connection_class", FakeAsyncValkeyConnection)
        kwargs.setdefault("connection_pool_class", valkey.asyncio.ConnectionPool)
        _validate_server_type(kwargs)
        super().__init__(*args, **kwargs)

    @classmethod
    def from_url(cls, *args: Any, **kwargs: Any) -> Self:
        # valkey.asyncio.Valkey.from_url passes these kwargs to the pool only, so the fake connections are configured
        # here rather than in __init__.
        _set_server_type(kwargs)
        kwargs.setdefault("client_class", valkey.asyncio.Valkey)
        kwargs.setdefault("connection_class", FakeAsyncValkeyConnection)
        return super().from_url(*args, **kwargs)
