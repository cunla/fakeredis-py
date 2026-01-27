from typing import Any, List, Optional

from fakeredis import _msgs as msgs
from fakeredis._commands import Key, command, CommandItem
from fakeredis._helpers import OK, SimpleError, casematch
from fakeredis.model import VectorSet, Vector


class VectorSetCommandsMixin:
    """`CommandsMixin` for enabling VectorSet compatibility in `fakeredis`."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def _set_attributes(self, v: Vector, attr: bytes) -> None:
        v.attributes = attr

    @command(name="VCARD", fixed=(Key(VectorSet),), flags=msgs.FLAG_DO_NOT_CREATE)
    def vcard(self, key: CommandItem) -> Optional[bytes]:
        if key.value is None:
            return None
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        return key.value.card

    @command(name="VDIM", fixed=(Key(VectorSet),), flags=msgs.FLAG_DO_NOT_CREATE)
    def vdim(self, key: CommandItem) -> int:
        if key.value is None:
            raise SimpleError("ERR key does not exist")
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        return key.value.dimensions

    @command(name="VGETATTR", fixed=(Key(VectorSet), bytes), flags=msgs.FLAG_DO_NOT_CREATE)
    def vgetattr(self, key: CommandItem, member: bytes) -> Optional[bytes]:
        if key.value is None:
            return None
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        if member not in key.value:
            return None
        return key.value[member].attributes

    @command(name="VSETATTR", fixed=(Key(VectorSet), bytes, bytes), flags=msgs.FLAG_DO_NOT_CREATE)
    def vsetattr(self, key: CommandItem, member: bytes, attr: bytes) -> int:
        if key.value is None:
            return 0
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        if member not in key.value:
            return 0
        self._set_attributes(key.value[member], attr)
        return OK

    @command(name="VADD", fixed=(Key(VectorSet),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vadd(self, key: CommandItem, *args: bytes) -> int:
        i = 0
        reduce, cas, vector_values, name, attributes = None, None, None, None, None

        while i < len(args):
            if casematch(args[i], b"cas"):
                cas = True  # unused for now
                i += 1
            elif casematch(args[i], b"reduce") and i + 1 < len(args):
                reduce = args[i + 1]
                i += 2
            elif casematch(args[i], b"values") and i + 1 < len(args):
                num_values = int(args[i + 1])
                i += 2
                if i + num_values > len(args):  # VALUES num_values values element
                    raise SimpleError("ERR wrong number of arguments for 'VADD' command")
                vector_values = [float(v) for v in args[i : i + num_values]]
                name = args[i + num_values]
                i += num_values
            elif casematch(args[i], b"setattr") and i + 1 < len(args):
                attributes = args[i + 1]
                i += 2
            i += 1
        cas = cas or False
        vector_set = key.value or VectorSet(reduce or len(vector_values))
        if vector_set.exists(name):
            return 0
        vector = Vector(name.decode(), vector_values, attributes or b"")
        vector_set.add(vector)
        key.update(vector_set)
        return 1

    @command(name="VEMB", fixed=(Key(VectorSet), bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vemb(self, key: CommandItem, *args: bytes) -> List[Optional[bytes]]:
        if key.value is None:
            raise SimpleError("ERR key does not exist")
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        # TODO
        return [None] * len(args)

    @command(name="VINFO", fixed=(Key(VectorSet),), flags=msgs.FLAG_DO_NOT_CREATE)
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

    @command(name="VRANDMEMBER", fixed=(Key(VectorSet),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vrandmember(self, key: CommandItem, *args: bytes) -> Optional[bytes]:
        return None

    @command(name="VREM", fixed=(Key(VectorSet), bytes), flags=msgs.FLAG_DO_NOT_CREATE)
    def vrem(self, key: CommandItem, member: bytes) -> int:
        if key.value is None:
            return 0
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        return key.value.remove(member)

    @command(name="VSIM", fixed=(Key(VectorSet),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vsim(self, key: CommandItem, *args: bytes) -> int:
        if key.value is None:
            raise SimpleError("ERR key does not exist")
        return 0
