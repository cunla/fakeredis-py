from typing import Any, Tuple, List, Callable

from fakeredis._command_info import get_categories, get_commands_by_category
from fakeredis._commands import command


class AclCommandsMixin:
    _get_command_info: Callable[[bytes], List[Any]]

    def __init(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.version: Tuple[int]

    @command(name="ACL CAT", fixed=(), repeat=(bytes,))
    def acl_cat(self, *category: bytes) -> List[bytes]:
        if len(category) == 0:
            res = get_categories()
        else:
            res = get_commands_by_category(category[0])
        return res
