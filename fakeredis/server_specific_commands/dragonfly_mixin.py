from typing import Callable

from fakeredis._commands import command, Key, Int, CommandItem
from fakeredis._helpers import Database


class DragonflyCommandsMixin(object):
    _expireat: Callable[[CommandItem, int], int]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db: Database

    @command(name="SADDEX", fixed=(Key(set), Int, bytes), repeat=(bytes,), server_types=("dragonfly",))
    def saddex(self, key: CommandItem, seconds: int, *members: bytes) -> int:
        old_size = len(key.value)
        key.value.update(members)
        key.updated()
        self._expireat(key, self._db.time + seconds)
        return len(key.value) - old_size
