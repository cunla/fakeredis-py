"""Dispatch rules where Dragonfly differs from Redis: commands it refuses in scripts and transactions, and the watches
it invalidates.
"""

from __future__ import annotations

from fakeredis._commands import Signature
from fakeredis._core import CommandItem, Database
from fakeredis.model import is_write_command

# Commands Dragonfly refuses inside a Lua script but Redis allows. The rest of its no-script set (SAVE, BGSAVE, SCRIPT,
# EVAL, MULTI/EXEC, the (P)SUBSCRIBE family, the blocking pops) already carries `FLAG_NO_SCRIPT` here.
DRAGONFLY_NO_SCRIPT_COMMANDS = frozenset({"flushdb", "flushall", "shutdown", "debug", "config", "client"})
# Dragonfly refuses to queue the (un)subscribe family inside a MULTI, where redis queues it.
DRAGONFLY_NO_TRANSACTION_COMMANDS = frozenset(
    {"subscribe", "unsubscribe", "psubscribe", "punsubscribe", "ssubscribe", "sunsubscribe"}
)
# Write commands whose keys dragonfly leaves clean unless it really wrote them: the ones that only read the keys beside
# their destination, and the two that bow out before touching the key at all -- a rejected MSETNX and a SETRANGE with an
# empty value. See `_dirty_watched_keys`.
DRAGONFLY_UNDIRTIED_COMMANDS = frozenset(
    {
        "bitop",
        "copy",
        "georadius",
        "georadiusbymember",
        "geosearchstore",
        "msetnx",
        "sdiffstore",
        "setrange",
        "sinterstore",
        "sort",
        "sunionstore",
        "zdiffstore",
        "zinterstore",
        "zrangestore",
        "zunionstore",
    }
)


def dirty_watched_keys(db: Database, sig: Signature, command_items: list[CommandItem]) -> None:
    """Invalidate the watches dragonfly invalidates and redis does not.

    Dragonfly dirties every key a write command runs against, so a `SET NX` that was
    rejected, or a `SREM` that removed nothing, still breaks a `WATCH` on the key. A
    key that does not exist stays clean, as do the keys of the commands listed in
    `DRAGONFLY_UNDIRTIED_COMMANDS`.
    """
    name = sig.name.split(" ")[0]
    if name in DRAGONFLY_UNDIRTIED_COMMANDS or not is_write_command(name.encode()):
        return
    for item in command_items:
        if not item.is_modified and db.has_watch(item.key) and item.key in db:
            db.notify_watch(item.key)
