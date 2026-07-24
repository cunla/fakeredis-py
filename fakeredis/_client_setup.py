"""Helpers for constructing the underlying redis/valkey client.

Used by the sync and async ``FakeRedisMixin`` classes to translate the
arguments accepted by ``FakeRedis(...)`` (and friends) into the kwargs the
real client class expects, wiring in a fakeredis connection pool.
"""

from __future__ import annotations

import inspect
import uuid
import warnings
from typing import Any, Callable


def _get_args_to_warn(method: Callable[..., Any]) -> set[str]:
    """Collect argument names that ``method`` would emit deprecation warnings for.

    redis-py marks deprecated ``__init__`` arguments by wrapping the method in
    a ``@deprecated_args(args_to_warn=[...])`` decorator. There is no public
    API to query the list, so this walks the wrapper's closure cells looking
    for the ``args_to_warn`` list (recursing through nested wrappers). If
    redis-py changes how the decorator stores the list, this returns an empty
    set and deprecated defaults are simply forwarded again.
    """
    closure = method.__closure__
    if closure is None:
        return set()
    res = set()
    for cell in closure:
        value = cell.cell_contents
        if isinstance(value, list) and len(value) > 0:
            res.update(value)
        elif callable(value):
            res.update(_get_args_to_warn(value))
    return res


def convert_args_kwargs(klass: type[object], *args: Any, **kwargs: Any) -> dict[str, Any]:
    """Interpret the positional and keyword arguments according to the version of redis in use"""
    parameters = list(inspect.signature(klass.__init__).parameters.values())[1:]
    args_to_warn = _get_args_to_warn(klass.__init__)
    # Convert args => kwargs
    kwargs.update({parameters[i].name: args[i] for i in range(len(args))})
    if "path" not in kwargs and "host" not in kwargs:
        kwargs["host"] = uuid.uuid4().hex
    kwds = {
        p.name: kwargs.get(p.name, p.default)
        for ind, p in enumerate(parameters)
        if p.default != inspect.Parameter.empty and (p.name not in args_to_warn or p.name in kwargs)
    }
    return kwds


# Client kwargs that are forwarded to the connection pool / connection.
_CONNECTION_POOL_KWARGS = frozenset(
    {
        "host",
        "port",
        "db",
        "username",
        "password",
        "socket_timeout",
        "encoding",
        "encoding_errors",
        "decode_responses",
        "retry_on_timeout",
        "max_connections",
        "health_check_interval",
        "client_name",
        "connected",
        "server",
        "protocol",
    }
)


def build_client_kwds(
    *args: Any,
    client_class: type[Any],
    connection_class: type[Any],
    connection_pool_class: type[Any],
    version: Any,
    server_type: Any,
    lua_modules: Any,
    server: Any,
    connected: bool | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Build the kwargs passed to the underlying redis/valkey client ``__init__``.

    Creates a fakeredis connection pool when one isn't supplied. Shared by the sync
    and async ``FakeRedisMixin`` classes; the caller still applies any lib_name /
    driver_info handling specific to its client library.
    """
    kwds = convert_args_kwargs(client_class, *args, **kwargs)
    kwds["server"] = server
    if connected is not None:
        kwds["connected"] = connected
    if not kwds.get("connection_pool", None):
        # Adapted from redis-py: translate the deprecated charset/errors aliases.
        charset = kwds.get("charset", None)
        if charset is not None:
            warnings.warn(DeprecationWarning('"charset" is deprecated. Use "encoding" instead'))
            kwds["encoding"] = charset
        errors = kwds.get("errors", None)
        if errors is not None:
            warnings.warn(DeprecationWarning('"errors" is deprecated. Use "encoding_errors" instead'))
            kwds["encoding_errors"] = errors
        connection_kwargs: dict[str, Any] = {
            "connection_class": connection_class,
            "version": version,
            "server_type": server_type,
            "lua_modules": lua_modules,
            "client_class": client_class,
        }
        connection_kwargs.update({arg: kwds[arg] for arg in _CONNECTION_POOL_KWARGS if arg in kwds})
        kwds["connection_pool"] = connection_pool_class(**connection_kwargs)
    for key in ("server", "connected", "version", "server_type", "lua_modules"):
        kwds.pop(key, None)
    return kwds
