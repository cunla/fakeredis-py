import hashlib
from typing import Dict, Set


class UserAccessControlList:
    def __init__(self):
        self._passwords: Set[str] = set()

    def check_password(self, password: bytes) -> bool:
        password_hex = hashlib.sha256(password).hexdigest()
        return password_hex in self._passwords

    def add_password_hex(self, password_hex: str) -> None:
        self._passwords.add(password_hex)

    def add_password(self, password: bytes) -> None:
        password_hex = hashlib.sha256(password).hexdigest()
        self.add_password_hex(password_hex)

    def remove_password_hex(self, password_hex: str) -> None:
        self._passwords.discard(password_hex)

    def remove_password(self, password: bytes) -> None:
        password_hex = hashlib.sha256(password).hexdigest()
        self.remove_password_hex(password_hex)


class AccessControlList:

    def __init__(self):
        self._user_acl: Dict[bytes, UserAccessControlList] = dict()

    def check_user_password(self, username: bytes, password: bytes) -> bool:
        if username not in self._user_acl:
            return False
        return self._user_acl[username].check_password(password)

    def add_user_password_hex(self, username: bytes, password_hex: str) -> None:
        self._user_acl.setdefault(username, UserAccessControlList()).add_password_hex(password_hex)

    def add_user_password(self, username: bytes, password: bytes) -> None:
        self._user_acl.setdefault(username, UserAccessControlList()).add_password(password)

    def remove_user_password_hex(self, username: bytes, password_hex: str) -> None:
        self._user_acl.setdefault(username, UserAccessControlList()).remove_password_hex(password_hex)

    def remove_user_password(self, username: bytes, password: bytes) -> None:
        self._user_acl.setdefault(username, UserAccessControlList()).remove_password(password)
