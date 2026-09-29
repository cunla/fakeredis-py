"""Keyspace and subkey notifications, published after a command has written its keys."""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable, Sequence
from typing import Any

from fakeredis._core import CommandItem
from fakeredis._helpers import compile_pattern
from fakeredis.commands_mixins._mixin_base import CommandsMixinBase
from fakeredis.model import Hash

LOGGER = logging.getLogger("fakeredis")


class NotificationsMixin(CommandsMixinBase):
    _db_num: int
    # Subkey (hash field) events recorded by the currently running command: (event, key, subkeys)
    _subkey_events: list[tuple[bytes, bytes, list[bytes]]]

    def _publish_to_channel(
        self, channel: bytes, message: bytes, pattern_regex: dict[bytes, re.Pattern[bytes]]
    ) -> None:
        msg = [b"message", channel, message]
        subs: Iterable[Any] = self._server.subscribers.get(channel, set())
        for sock in subs:
            sock.put_response(msg)

        for pattern, regex in pattern_regex.items():
            if regex.match(channel):
                pmsg = [b"pmessage", pattern, channel, message]
                for sock in self._server.psubscribers[pattern]:
                    sock.put_response(pmsg)

    def _keyspace_notifications(self, command_items: list[CommandItem], event: bytes) -> None:
        """Send keyspace notifications"""
        pattern_regex: dict[bytes, re.Pattern[bytes]] = {
            pattern: compile_pattern(pattern) for pattern in self._server.psubscribers
        }
        keyspace_channel_prefix: bytes = f"__keyspace@{self._db_num}__:".encode()
        keyevent_channel: bytes = f"__keyevent@{self._db_num}__:".encode() + event
        for command_item in command_items:
            if not command_item.is_modified:
                continue
            try:
                keyspace_channel = keyspace_channel_prefix + command_item.key

                for channel, message in [(keyspace_channel, event), (keyevent_channel, command_item.key)]:
                    self._publish_to_channel(channel, message, pattern_regex)
            except Exception as e:
                LOGGER.error(
                    f"Error sending keyspace notification for event `{event.decode()}` on key {command_item.key.decode()}: {e}"
                )

    def add_subkey_event(self, event: bytes, key: bytes, subkeys: Sequence[bytes]) -> None:
        """Record a subkey (e.g. hash field) event, to be published once the current command finishes."""
        if len(subkeys) > 0:
            self._subkey_events.append((event, key, list(subkeys)))

    def _subkey_notifications(self, command_items: list[CommandItem]) -> None:
        """Send subkey notifications (added in redis 8.8), currently emitted for hash fields only.

        Unlike key-level notifications above, these follow the `notify-keyspace-events` config: the `h` class flag must
        be set, and each of the S/T/I/V flags enables one channel type.
        """
        events, self._subkey_events = self._subkey_events, []
        for command_item in command_items:
            if isinstance(command_item.value, Hash):
                expired_fields = command_item.value.take_expired_fields()
                if expired_fields:
                    events.insert(0, (b"hexpired", command_item.key, expired_fields))
        if not events or self.version < (8, 8) or self._server.server_type != "redis":
            return
        config_flags = self._server.config.get(b"notify-keyspace-events", b"")
        if b"h" not in config_flags and b"A" not in config_flags:
            return
        if not any(flag in config_flags for flag in (b"S", b"T", b"I", b"V")):
            return
        pattern_regex: dict[bytes, re.Pattern[bytes]] = {
            pattern: compile_pattern(pattern) for pattern in self._server.psubscribers
        }
        db_num = str(self._db_num).encode()
        for event, key, subkeys in events:
            try:
                subkeys_payload = b",".join(b"%d:%s" % (len(subkey), subkey) for subkey in subkeys)
                # Events containing `|` are skipped for the channels using `|` as a delimiter, and keys containing `\n`
                # for the channel using `\n` as a delimiter.
                if b"S" in config_flags and b"|" not in event:
                    channel = b"__subkeyspace@%s__:%s" % (db_num, key)
                    self._publish_to_channel(channel, event + b"|" + subkeys_payload, pattern_regex)
                if b"T" in config_flags:
                    channel = b"__subkeyevent@%s__:%s" % (db_num, event)
                    message = b"%d:%s|%s" % (len(key), key, subkeys_payload)
                    self._publish_to_channel(channel, message, pattern_regex)
                if b"I" in config_flags and b"\n" not in key:
                    for subkey in subkeys:
                        channel = b"__subkeyspaceitem@%s__:%s\n%s" % (db_num, key, subkey)
                        self._publish_to_channel(channel, event, pattern_regex)
                if b"V" in config_flags and b"|" not in event:
                    channel = b"__subkeyspaceevent@%s__:%s|%s" % (db_num, event, key)
                    self._publish_to_channel(channel, subkeys_payload, pattern_regex)
            except Exception as e:
                LOGGER.error(
                    f"Error sending subkey notification for event `{event.decode()}` on key {key.decode()}: {e}"
                )
