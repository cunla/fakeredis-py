from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from fakeredis._typing import ServerType, VersionType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fakeredis._commands import CommandItem, Signature
    from fakeredis._helpers import Database, SimpleString
    from fakeredis._server import FakeServer
    from fakeredis.model import ClientInfo


class CommandsMixinBase:
    """Base class for command mixins: the contract between a mixin and the socket it is mixed into.

    `FakeSocket` combines `BaseFakeSocket` with every mixin, so a mixin can use state and helpers that live on the socket
    or on a sibling mixin. Everything a mixin relies on that way is declared here, once.
    """

    _server: FakeServer
    _client_info: ClientInfo
    _db: Database
    _script_resp: int | None = None

    if TYPE_CHECKING:
        # Stubs for type checkers only. They do not exist at runtime, so they can never shadow the implementations that
        # come later in FakeSocket's MRO.

        # Implemented by BaseFakeSocket.
        def put_response(self, msg: Any) -> None: ...

        def add_subkey_event(self, event: bytes, key: bytes, subkeys: Sequence[bytes]) -> None: ...

        def _name_to_func(self, cmd_name: str) -> tuple[Callable[[Any], Any] | None, Signature]: ...

        def _run_command(
            self, func: Callable[[Any], Any] | None, sig: Signature, args: list[Any], from_script: bool
        ) -> Any: ...

        def _scan(self, keys: Sequence[bytes], cursor: int, *args: bytes) -> list[bytes | list[bytes]]: ...

        def _ttl(self, key: CommandItem, scale: float) -> int: ...

        def _encodefloat(self, value: float, humanfriendly: bool) -> bytes: ...

        def _encodeint(self, value: int) -> bytes: ...

        @staticmethod
        def _key_value_type(key: CommandItem) -> SimpleString: ...

        # Implemented by GenericCommandsMixin.
        def _expireat(self, key: CommandItem, timestamp: float, *args: bytes) -> int: ...

        # Implemented by TransactionsCommandsMixin.
        def _clear_watches(self) -> None: ...

    @property
    def version(self) -> VersionType:
        raise NotImplementedError

    @property
    def server_type(self) -> ServerType:
        raise NotImplementedError

    @property
    def _resp_version(self) -> int:
        """RESP version the reply being built should be shaped for.

        That is the client's negotiated protocol, except inside a script, where replies to
        `redis.call` follow the script's own RESP mode instead.
        """
        return self._script_resp if self._script_resp is not None else self._client_info.protocol_version

    def _blocking(
        self, timeout: float | None, func: Callable[[bool], Any], shape: Callable[[Any], Any] | None = None
    ) -> Any:
        """Implemented by the socket, sync and async alike; see `FakeSocket._blocking`."""
        raise NotImplementedError

    def _empty_blocking_reply(self, result: Any) -> Any:
        """Shape a timed-out array-returning blocking pop (BLPOP/BRPOP/BZPOPMIN/BZPOPMAX).

        Redis sends a null array, which RESP3 renders as nil. Dragonfly sends an empty array instead, so under RESP3 the
        client sees `[]` rather than `None`. Under RESP2 both encode to `*-1` and the client sees `None` either way.
        """
        if result is None and self.server_type == "dragonfly" and self._resp_version == 3:
            return []
        return result
