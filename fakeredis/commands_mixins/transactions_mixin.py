from __future__ import annotations

from typing import Any, Callable

from fakeredis import _msgs as msgs
from fakeredis._commands import CommandItem, Key, command
from fakeredis._helpers import OK, SimpleError, SimpleString
from fakeredis.commands_mixins._mixin_base import CommandsMixinBase


class TransactionsCommandsMixin(CommandsMixinBase):
    _run_command: Callable  # type: ignore

    def __init__(self, *args, **kwargs) -> None:  # type: ignore
        super().__init__(*args, **kwargs)
        self._watches: set[Any] = set()
        # When in a MULTI, set to a list of function calls
        self._transaction: list[Any] | None = None
        self._transaction_failed = False
        # Dragonfly only: queueing stopped after a command failed to queue, but the queue
        # itself is kept until the next MULTI resumes it (or DISCARD/EXEC throws it away).
        self._transaction_paused = False
        # Set when executing the commands from EXEC
        self._in_transaction = False
        self._watch_notified = False

    def _clear_watches(self) -> None:
        self._watch_notified = False
        while self._watches:
            (key, db) = self._watches.pop()
            db.remove_watch(key, self)

    def _forget_watches_without_multi(self) -> None:
        """Drop the watches a DISCARD/EXEC outside a MULTI clears on dragonfly.

        Redis leaves them armed and answers the error alone.
        """
        if self.server_type == "dragonfly":
            self._clear_watches()

    @property
    def _queueing(self) -> bool:
        """Whether a command sent now would be queued rather than run."""
        return self._transaction is not None and not self._transaction_paused

    def abort_transaction(self) -> None:
        """Stop queueing the way dragonfly does when a command fails to queue.

        Later commands run immediately and DISCARD reports there is no MULTI, but the queue
        built so far is kept: the next MULTI picks it up again, and only DISCARD or the
        EXEC that reports the failure throws it away.
        """
        self._transaction_paused = True
        self._transaction_failed = True

    def _forget_transaction(self) -> None:
        self._transaction = None
        self._transaction_paused = False
        self._transaction_failed = False

    # Transaction commands
    @command((), flags=[msgs.FLAG_NO_SCRIPT, msgs.FLAG_TRANSACTION])
    def discard(self) -> SimpleString:
        if not self._queueing:
            # A transaction dragonfly stopped queueing is thrown away here, unreported.
            self._forget_transaction()
            self._forget_watches_without_multi()
            raise SimpleError(msgs.WITHOUT_MULTI_MSG.format("DISCARD"))
        self._forget_transaction()
        self._clear_watches()
        return OK

    @command(name="exec", fixed=(), repeat=(), flags=[msgs.FLAG_NO_SCRIPT, msgs.FLAG_TRANSACTION])
    def exec_(self) -> Any:
        if not self._queueing:
            if self._transaction_failed:  # a transaction dragonfly stopped queueing
                self._forget_transaction()
                self._clear_watches()
                raise SimpleError(msgs.DRAGONFLY_EXECABORT_MSG)
            self._forget_watches_without_multi()
            raise SimpleError(msgs.WITHOUT_MULTI_MSG.format("EXEC"))
        if self._transaction_failed:
            self._forget_transaction()
            self._clear_watches()
            raise SimpleError(msgs.DRAGONFLY_EXECABORT_MSG if self.server_type == "dragonfly" else msgs.EXECABORT_MSG)
        transaction = self._transaction or []
        self._forget_transaction()
        watch_notified = self._watch_notified
        self._clear_watches()
        if watch_notified:
            return None
        result = []
        for func, sig, args in transaction:
            try:
                self._in_transaction = True
                ans = self._run_command(func, sig, args, False)
            except SimpleError as exc:
                ans = exc
            finally:
                self._in_transaction = False
            result.append(ans)
        return result

    @command((), flags=[msgs.FLAG_NO_SCRIPT, msgs.FLAG_TRANSACTION])
    def multi(self) -> SimpleString:
        if self._queueing:
            raise SimpleError(msgs.MULTI_NESTED_MSG)
        if self._transaction_paused:
            # Dragonfly picks the kept queue back up rather than starting a new one.
            self._transaction_paused = False
        else:
            self._transaction = []
        self._transaction_failed = False
        return OK

    @command((), flags=msgs.FLAG_NO_SCRIPT)
    def unwatch(self) -> SimpleString:
        self._clear_watches()
        return OK

    @command((Key(),), (Key(),), flags=[msgs.FLAG_NO_SCRIPT, msgs.FLAG_TRANSACTION])
    def watch(self, *keys: CommandItem) -> SimpleString:
        if self._queueing:
            if self.server_type == "dragonfly":
                self.abort_transaction()
                raise SimpleError(msgs.DRAGONFLY_NOT_IN_TRANSACTION_MSG.format("WATCH"))
            raise SimpleError(msgs.WATCH_INSIDE_MULTI_MSG)
        for key in keys:
            if key not in self._watches:
                self._watches.add((key.key, self._db))
                self._db.add_watch(key.key, self)
        return OK

    def notify_watch(self) -> None:
        self._watch_notified = True
