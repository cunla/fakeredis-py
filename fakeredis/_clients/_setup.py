"""Helpers for constructing the underlying redis/valkey client.

Used by the sync and async ``FakeRedisMixin`` classes to translate the arguments accepted by ``FakeRedis(...)`` (and
friends) into the kwargs the real client class expects, wiring in a fakeredis connection pool.
"""

import functools
import inspect
import uuid
import warnings
from typing import Any, Callable, Dict, FrozenSet, Optional, Set, Tuple, Type

from fakeredis._typing import lib_version


def _get_args_to_warn(method: Callable[..., Any]) -> Set[str]:
    """Collect argument names that ``method`` would emit deprecation warnings for.

    redis-py marks deprecated ``__init__`` arguments by wrapping the method in a
    ``@deprecated_args(args_to_warn=[...])`` decorator. There is no public
    API to query the list, so this walks the wrapper's closure cells looking for the ``args_to_warn`` list (recursing
    through nested wrappers). If redis-py changes how the decorator stores the list, this returns an empty set and
    deprecated defaults are simply forwarded again.
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


@functools.lru_cache(maxsize=64)
def _init_parameters(init: Callable[..., Any]) -> Tuple[Tuple[inspect.Parameter, ...], FrozenSet[str]]:
    """The parameters of a client's ``__init__`` (without ``self``) and the ones it warns about.

    Inspecting the signature is slow next to the rest of building a client, and it is the same for every client of a
    class, so it is done once per ``__init__``.
    """
    return tuple(inspect.signature(init).parameters.values())[1:], frozenset(_get_args_to_warn(init))


def convert_args_kwargs(klass: Type[object], *args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Interpret the positional and keyword arguments according to the version of redis in use"""
    parameters, args_to_warn = _init_parameters(klass.__init__)
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
    client_class: Type[Any],
    connection_class: Type[Any],
    connection_pool_class: Type[Any],
    version: Any,
    server_type: Any,
    lua_modules: Any,
    server: Any,
    connected: Optional[bool] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Build the kwargs passed to the underlying redis/valkey client ``__init__``.

    Creates a fakeredis connection pool when one isn't supplied. Shared by the sync and async ``FakeRedisMixin``
    classes; the caller still applies any lib_name / driver_info handling specific to its client library.
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
        connection_kwargs: Dict[str, Any] = {
            "connection_class": connection_class,
            "version": version,
            "server_type": server_type,
            "lua_modules": lua_modules,
            "client_class": client_class,
        }
        connection_kwargs.update({arg: kwds[arg] for arg in _CONNECTION_POOL_KWARGS if arg in kwds})
        kwds["connection_pool"] = connection_pool_class(**connection_kwargs)
    # Report fakeredis, not the client library, in CLIENT SETINFO / CLIENT INFO.
    if "lib_name" in kwds and "lib_version" in kwds and "driver_info" not in kwds:
        kwds["lib_name"] = "fakeredis"
        kwds["lib_version"] = lib_version
    if "driver_info" in kwds:
        from redis import DriverInfo

        kwds["driver_info"] = DriverInfo(name="fakeredis", lib_version=lib_version)
    for key in ("server", "connected", "version", "server_type", "lua_modules"):
        kwds.pop(key, None)
    return kwds


_ACCEPTS_DRIVER_INFO: Dict[Type[Any], bool] = {}


def _accepts_driver_info(connection_class: Type[Any]) -> bool:
    """Whether a connection class takes ``driver_info`` (recent redis-py does; older ones and valkey-py do not).

    The parameter is declared by a base class and reached through ``**kwargs``, so every ``__init__`` is looked at.
    """
    res = _ACCEPTS_DRIVER_INFO.get(connection_class)
    if res is None:
        res = _ACCEPTS_DRIVER_INFO[connection_class] = any(
            "driver_info" in inspect.signature(vars(klass)["__init__"]).parameters
            for klass in connection_class.__mro__
            if "__init__" in vars(klass)
        )
    return res


@functools.lru_cache(maxsize=None)
def _client_lib_version() -> Any:
    from redis.utils import get_lib_version

    return get_lib_version()  # type: ignore[no-untyped-call]


def default_driver_info(connection_class: Type[Any], kwargs: Dict[str, Any]) -> Any:
    """The ``driver_info`` to give a connection that was not told what to report in CLIENT SETINFO, or None when
    the connection should be left to work it out.

    redis-py fills in a missing ``driver_info`` by reading its own version from the installed package metadata, for
    every connection it creates, which takes several times longer than everything else a fake connection does to get
    ready. This builds the same value from a version that is looked up once.
    """
    if any(arg in kwargs for arg in ("driver_info", "lib_name", "lib_version")):
        return None
    if not _accepts_driver_info(connection_class):
        return None
    from redis.driver_info import DriverInfo

    return DriverInfo(lib_version=_client_lib_version())
