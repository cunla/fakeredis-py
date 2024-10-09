import hashlib
from typing import Dict, Set, List, Tuple


class UserAccessControlList:
    def __init__(self):
        self._passwords: Set[str] = set()
        self._enabled: bool = True
        self._nopass: bool = False
        self._key_patterns: Set[bytes] = set()
        self._channel_patterns: Set[bytes] = set()
        self._categories: Dict[bytes, bool] = {b"all": False}
        self._commands: Dict[bytes, bool] = dict()
        self._selectors: Dict[bytes, Tuple[bool, bytes, bytes]] = dict()

    def reset(self):
        self._enabled = False
        self._nopass = False
        self._passwords.clear()
        self._key_patterns.clear()
        self._channel_patterns.clear()
        self._categories = {b"all": False}
        self._selectors.clear()

    def set_enable(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_nopass(self) -> None:
        self._nopass = True
        self._passwords.clear()

    def check_password(self, password: bytes) -> bool:
        password_hex = hashlib.sha256(password).hexdigest()
        return password_hex in self._passwords and self._enabled

    def add_password_hex(self, password_hex: str) -> None:
        self._nopass = True
        self._passwords.add(password_hex)

    def add_password(self, password: bytes) -> None:
        password_hex = hashlib.sha256(password).hexdigest()
        self.add_password_hex(password_hex)

    def remove_password_hex(self, password_hex: str) -> None:
        self._passwords.discard(password_hex)

    def remove_password(self, password: bytes) -> None:
        password_hex = hashlib.sha256(password).hexdigest()
        self.remove_password_hex(password_hex)

    def add_command_or_category(self, selector: bytes) -> None:
        enabled, command = selector[0] == ord("+"), selector[1:]
        if command[0] == ord("@"):
            self._categories[command[1:]] = enabled
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

    def as_rule(self) -> bytes:
        results = []
        results.append(b"on" if self._enabled else b"off")
        if self._nopass:
            results.append(b"nopass")
        results.extend(b"#" + password.encode() for password in self._passwords)
        results.extend(b"~" + key_pattern for key_pattern in self._key_patterns)
        if len(self._channel_patterns) == 0:
            results.append(b"resetchannels")
        else:
            results.extend(b"&" + channel_pattern for channel_pattern in self._channel_patterns)
        if len(self._categories) == 0:
            results.append(b"-@all")
        else:
            results.extend(b"+@" + category for category in self._categories)
        return b" ".join(results)

    def _get_selectors(self) -> List[List[bytes]]:
        results = []
        for command, data in self._selectors.items():
            selector = (b"+" if data[0] else b"-") + command
            results.append([selector, b"keys", b"~" + data[1], b"channels", b"&" + data[2]])
        return results

    def _get_commands(self) -> List[bytes]:
        res = list()
        for category, enabled in self._categories.items():
            inc = b"+" if enabled else b"-"
            res.append(inc + b"@" + category)
        for command, enabled in self._commands.items():
            inc = b"+" if enabled else b"-"
            res.append(inc + command)
        return res

    def _get_key_patterns(self) -> List[bytes]:
        return [b"~" + key_pattern for key_pattern in self._key_patterns]

    def as_array(self) -> List[bytes]:
        flags = list()
        flags.append(b"on" if self._enabled else b"off")
        if self._nopass:
            flags.append(b"nopass")
        if "*" in self._key_patterns:
            flags.append(b"allkeys")
        if "*" in self._channel_patterns:
            flags.append(b"allchannels")
        results = list()
        results.extend([b"flags", flags])
        results.extend([b"passwords", [b"#" + password.encode() for password in self._passwords]])
        results.extend([b"commands", b" ".join(self._get_commands())])
        results.extend([b"keys", b" ".join(self._get_key_patterns())])
        results.extend([b"channels", self._channel_patterns or [b""]])
        results.extend([b"selectors", self._get_selectors()])
        return results


class AccessControlList:

    def __init__(self):
        self._user_acl: Dict[bytes, UserAccessControlList] = dict()

    def get_user_acl(self, username: bytes) -> UserAccessControlList:
        return self._user_acl.setdefault(username, UserAccessControlList())

    def as_rules(self) -> List[bytes]:
        return [username + b" " + user_acl.as_rule() for username, user_acl in self._user_acl.items()]

    def del_user(self, username: bytes) -> None:
        self._user_acl.pop(username, None)
