import hashlib
from typing import Dict, Set, List, Union, Optional

from ._command_info import get_commands_by_category
from .._helpers import SimpleError


class Selector:
    def __init__(self, command: bytes, allowed: bool, keys: bytes, channels: bytes):
        self.command: bytes = command
        self.allowed: bool = allowed
        self.keys: bytes = keys
        self.channels: bytes = channels

    def as_array(self) -> List[bytes]:
        return [b"+" if self.allowed else b"-", self.command, b"keys", self.keys, b"channels", self.channels]

    @classmethod
    def from_bytes(cls, data: bytes) -> "Selector":
        keys = b""
        channels = b""
        command = b""
        allowed = False
        data = data.split(b" ")
        for item in data:
            if item.startswith(b"&"):  # channels
                channels = item
                continue
            if item.startswith(b"%RW"):  # keys
                item = item[3:]
            key = item
            if key.startswith(b"%"):
                key = key[2:]
            if key.startswith(b"~"):
                keys = item
                continue
            # command
            if item[0] == ord("+") or item[0] == ord("-"):
                command = item[1:]
                allowed = item[0] == ord("+")

        return cls(command, allowed, keys, channels)


class UserAccessControlList:
    def __init__(self):
        self._passwords: Set[bytes] = set()
        self.enabled: bool = True
        self._nopass: bool = False
        self._key_patterns: Set[bytes] = set()
        self._channel_patterns: Set[bytes] = set()
        self._commands: Dict[bytes, bool] = {b"@all": False}
        self._selectors: Dict[bytes, Selector] = dict()

    def reset(self):
        self.enabled = False
        self._nopass = False
        self._commands = {b"@all": False}
        self._passwords.clear()
        self._key_patterns.clear()
        self._channel_patterns.clear()
        self._selectors.clear()

    def set_nopass(self) -> None:
        self._nopass = True
        self._passwords.clear()

    def check_password(self, password: Optional[bytes]) -> bool:
        if self._nopass and not password:
            return True
        if not password:
            return False
        password_hex = hashlib.sha256(password).hexdigest().encode()
        return password_hex in self._passwords and self.enabled

    def add_password_hex(self, password_hex: bytes) -> None:
        self._nopass = False
        self._passwords.add(password_hex)

    def add_password(self, password: bytes) -> None:
        self._nopass = False
        password_hex = hashlib.sha256(password).hexdigest().encode()
        self.add_password_hex(password_hex)

    def remove_password_hex(self, password_hex: bytes) -> None:
        self._passwords.discard(password_hex)

    def remove_password(self, password: bytes) -> None:
        password_hex = hashlib.sha256(password).hexdigest().encode()
        self.remove_password_hex(password_hex)

    def add_command_or_category(self, selector: bytes) -> None:
        enabled, command = selector[0] == ord("+"), selector[1:]
        if command[0] == ord("@"):
            self._commands[command] = enabled
            category_commands = get_commands_by_category(command[1:])
            for command in category_commands:
                if command in self._commands:
                    del self._commands[command]
        else:
            self._commands[command] = enabled

    def add_key_pattern(self, key_pattern: bytes) -> None:
        self._key_patterns.add(key_pattern)

    def reset_key_patterns(self) -> None:
        self._key_patterns.clear()

    def reset_channels_patterns(self):
        self._channel_patterns.clear()

    def add_channel_pattern(self, channel_pattern: bytes) -> None:
        self._channel_patterns.add(channel_pattern)

    def add_selector(self, selector: bytes) -> None:
        selector = Selector.from_bytes(selector)
        self._selectors[selector.command] = selector

    def _get_selectors(self) -> List[List[bytes]]:
        results = []
        for command, selector in self._selectors.items():
            s = b"-@all " + (b"+" if selector.allowed else b"-") + command
            results.append([b"commands", s, b"keys", selector.keys, b"channels", selector.channels])
        return results

    def _get_commands(self) -> List[bytes]:
        res = list()
        for command, enabled in self._commands.items():
            inc = b"+" if enabled else b"-"
            res.append(inc + command)
        return res

    def _get_key_patterns(self) -> List[bytes]:
        return [b"~" + key_pattern for key_pattern in self._key_patterns]

    def _get_channel_patterns(self):
        return [b"&" + channel_pattern for channel_pattern in self._channel_patterns]

    def _get_flags(self) -> List[bytes]:
        flags = list()
        flags.append(b"on" if self.enabled else b"off")
        if self._nopass:
            flags.append(b"nopass")
        if "*" in self._key_patterns:
            flags.append(b"allkeys")
        if "*" in self._channel_patterns:
            flags.append(b"allchannels")
        return flags

    def as_array(self) -> List[Union[bytes, List[bytes]]]:
        results: List[Union[bytes, List[bytes]]] = list()
        results.extend(
            [
                b"flags",
                self._get_flags(),
                b"passwords",
                list(self._passwords),
                b"commands",
                b" ".join(self._get_commands()),
                b"keys",
                b" ".join(self._get_key_patterns()),
                b"channels",
                b" ".join(self._get_channel_patterns()),
                b"selectors",
                self._get_selectors(),
            ]
        )
        return results

    def _get_selectors_for_rule(self) -> List[bytes]:
        results: List[bytes] = list()
        for command, selector in self._selectors.items():
            s = b"-@all " + (b"+" if selector.allowed else b"-") + command
            channels = b"resetchannels" + ((b" " + selector.channels) if selector.channels != b"" else b"")
            results.append(b"(" + b" ".join([selector.keys, channels, s]) + b")")
        return results

    def as_rule(self) -> bytes:
        selectors = self._get_selectors_for_rule()
        channels = self._get_channel_patterns()
        if channels != [b"&*"]:
            channels = [b"resetchannels"] + channels
        rule_parts: List[bytes] = (
            self._get_flags()
            + [b"#" + password for password in self._passwords]
            + self._get_commands()
            + self._get_key_patterns()
            + channels
            + selectors
        )
        return b" ".join(rule_parts)


class AccessControlList:

    def __init__(self):
        self._user_acl: Dict[bytes, UserAccessControlList] = dict()

    def get_users(self) -> List[bytes]:
        return list(self._user_acl.keys())

    def get_user_acl(self, username: bytes) -> UserAccessControlList:
        return self._user_acl.setdefault(username, UserAccessControlList())

    def as_rules(self) -> List[bytes]:
        res: List[bytes] = list()
        for username, user_acl in self._user_acl.items():
            rule_str = b"user " + username + b" " + user_acl.as_rule()
            res.append(rule_str)
        return res

    def del_user(self, username: bytes) -> None:
        self._user_acl.pop(username, None)

    def validate_command(self, username: bytes, fields: List[bytes]):
        if username not in self._user_acl:
            return
        user_acl = self._user_acl[username]
        if not user_acl.enabled:
            raise SimpleError("ACL disabled")
        command = fields[0]
