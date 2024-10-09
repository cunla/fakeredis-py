import secrets
from typing import Any, Tuple, List, Callable, Dict

from fakeredis import _msgs as msgs
from fakeredis._command_info import get_categories, get_commands_by_category
from fakeredis._commands import command, Int
from fakeredis._helpers import SimpleError, OK


class AclCommandsMixin:
    _get_command_info: Callable[[bytes], List[Any]]

    def __init(self, *args: Any, **kwargs: Any) -> None:
        super(AclCommandsMixin).__init__(*args, **kwargs)
        self.version: Tuple[int]
        self._server: Any

    def _check_user_password(self, username: bytes, password: bytes) -> bool:
        return self._server.acl.check_user_password(username, password)

    @property
    def _server_config(self) -> Dict[bytes, bytes]:
        return self._server.config

    @command(name="CONFIG SET", fixed=(bytes, bytes), repeat=(bytes, bytes))
    def config_set(self, *args: bytes):
        if len(args) % 2 != 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("CONFIG SET"))
        for i in range(0, len(args), 2):
            self._server_config[args[i]] = args[i + 1]
        return OK

    @command(name="AUTH", fixed=(), repeat=(bytes,))
    def auth(self, *args: bytes) -> bytes:
        if not 1 <= len(args) <= 2:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("AUTH"))
        username = None if len(args) == 1 else args[0]
        password = args[1] if len(args) == 2 else args[0]
        if (
            (username is None or username == b"default")
            and b"requirepass" in self._server_config
            and password == self._server_config[b"requirepass"]
        ):
            return OK
        if len(args) == 2 and self._check_user_password(username, password):
            return OK
        raise SimpleError(msgs.AUTH_FAILURE)

    @command(name="ACL CAT", fixed=(), repeat=(bytes,))
    def acl_cat(self, *category: bytes) -> List[bytes]:
        if len(category) == 0:
            res = get_categories()
        else:
            res = get_commands_by_category(category[0])
        return res

    @command(name="ACL GENPASS", fixed=(), repeat=(bytes,))
    def acl_genpass(self, *args: bytes) -> bytes:
        bits = Int.decode(args[0]) if len(args) > 0 else 256
        bits = bits + bits % 4  # Round to 4
        nbytes: int = bits // 8
        return secrets.token_hex(nbytes).encode()

    @command(name="ACL SETUSER", fixed=(bytes,), repeat=(bytes,))
    def acl_setuser(self, username: bytes, *args: bytes) -> bytes:
        for arg in args:
            if arg[0] == ord(">"):
                self._server.acl.add_user_password(username, arg[1:])
            elif arg[0] == ord("<"):
                self._server.acl.remove_user_password(username, arg[1:])
            elif arg[0] == ord("#"):
                self._server.acl.add_user_password_hex(username, arg[1:])
            elif arg[0] == ord("!"):
                self._server.acl.remove_user_password_hex(username, arg[1:])

        return OK
