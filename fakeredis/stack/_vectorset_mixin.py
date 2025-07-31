from typing import Any, List, Optional

from fakeredis import _msgs as msgs
from fakeredis._commands import Key, command, CommandItem
from fakeredis._helpers import OK, SimpleError
from fakeredis.model import VectorSet


class VectorSetCommandsMixin:
    """`CommandsMixin` for enabling VectorSet compatibility in `fakeredis`."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @command(name="VCARD", fixed=(Key(VectorSet)), flags=msgs.FLAG_DO_NOT_CREATE)
    def vcard(self, key: CommandItem) -> Optional[bytes]:
        if key.value is None:
            return None
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        return key.value.card

    @command(name="VDIM", fixed=(Key(VectorSet)), flags=msgs.FLAG_DO_NOT_CREATE)
    def vdim(self, key: CommandItem) -> int:
        if key.value is None:
            raise SimpleError("ERR key does not exist")
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        return key.value.dimensions

    @command(name="VGETATTR", fixed=(Key(VectorSet), bytes), flags=msgs.FLAG_DO_NOT_CREATE)
    def vgetattr(self, key: CommandItem, elem: bytes) -> Optional[bytes]:
        if key.value is None:
            return None
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        if elem not in key.value:
            return None
        return key.value[elem].attributes

    @command(name="VSETATTR", fixed=(Key(VectorSet), bytes, bytes), flags=msgs.FLAG_DO_NOT_CREATE)
    def vsetattr(self, key: CommandItem, elem: bytes, attr: bytes) -> int:
        if key.value is None:
            return 0
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        if elem not in key.value:
            return 0
        key.value[elem].attributes = attr
        return OK

    @command(name="VADD", fixed=(Key(VectorSet)), flags=msgs.FLAG_DO_NOT_CREATE)
    def vadd(self, key: CommandItem, *args: bytes) -> int:
        # todo
        return 0

    @command(name="VEMB", fixed=(Key(VectorSet), bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vemb(self, key: CommandItem, *args: bytes) -> List[Optional[bytes]]:
        if key.value is None:
            raise SimpleError("ERR key does not exist")
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        # TODO
        return [None] * len(args)

    @command(name="VINFO", fixed=(Key(VectorSet)), flags=msgs.FLAG_DO_NOT_CREATE)
    def vinfo(self, key: CommandItem):
        if key.value is None:
            return None
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        # TODO
        return None

    @command(name="VLINKS", fixed=(Key(VectorSet), bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vlinks(self, key: CommandItem, elem: bytes, *args: bytes) -> List[Optional[bytes]]:
        if key.value is None:
            raise SimpleError("ERR key does not exist")
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        # TODO
        return [None] * len(args)

    @command(name="VRANDMEMBER", fixed=(Key(VectorSet)), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vrandmember(self, key: CommandItem, *args: bytes) -> Optional[bytes]:
        return None

    @command(name="VREM", fixed=(Key(VectorSet), bytes), flags=msgs.FLAG_DO_NOT_CREATE)
    def vrem(self, key: CommandItem, *args: bytes) -> int:
        if key.value is None:
            raise 0
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        # TODO
        return 0

    @command(name="VSIM", fixed=(Key(VectorSet)), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vsim(self, key: CommandItem, *args: bytes) -> int:
        if key.value is None:
            raise SimpleError("ERR key does not exist")
        return 0
