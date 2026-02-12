import random
import struct
from typing import Any, List, Optional, Union

from fakeredis import _msgs as msgs
from fakeredis._commands import Key, command, CommandItem, StringTest
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
        numlinks, reduce, cas, vector_values, name, attributes, quantization, ef = (
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        )

        while i < len(args):
            if casematch(args[i], b"ef") and i + 1 < len(args):
                ef = int(args[i + 1])
                i += 2
            elif casematch(args[i], b"m") and i + 1 < len(args):
                numlinks = int(args[i + 1])
                i += 2
            elif casematch(args[i], b"cas"):
                cas = True  # unused for now
                i += 1
            elif casematch(args[i], b"reduce") and i + 1 < len(args):
                reduce = int(args[i + 1])
                i += 2
            elif casematch(args[i], b"fp32") and i + 2 < len(args):
                byte_array = args[i + 1]
                # convert byte array to list of floats
                vector_values = list(struct.unpack(f"{len(byte_array) // 4}f", byte_array))
                name = args[i + 2]
                i += 3
            elif casematch(args[i], b"bin") or casematch(args[i], b"q8") or casematch(args[i], b"noquant"):
                if quantization is not None:
                    raise SimpleError("ERR multiple quantization types specified")
                quantization = args[i].lower().decode()
                i += 1
            elif casematch(args[i], b"values") and i + 1 < len(args):
                num_values = int(args[i + 1])
                i += 2
                if i + num_values > len(args):  # VALUES num_values values element
                    raise SimpleError("ERR wrong number of arguments for 'VADD' command")
                vector_values = [float(v) for v in args[i : i + num_values]]
                name = args[i + num_values]
                i += num_values + 1
            elif casematch(args[i], b"setattr") and i + 1 < len(args):
                attributes = args[i + 1]
                i += 2
            else:
                raise SimpleError("ERR syntax error in 'VADD' command")
        cas = cas or False
        if reduce is not None and key.value is not None:
            raise SimpleError("ERR cannot add projection to existing set without projection")
        if reduce is not None and reduce < 0:
            raise SimpleError("ERR invalid vector specification")
        vector_set = key.value or VectorSet(reduce or len(vector_values))
        dimensions = vector_set.dimensions

        if len(vector_values) != dimensions:
            # If reduce is specified, we allow vectors with more dimensions and just ignore the extra values.
            pass

        if vector_set.exists(name):
            return 0

        vector = Vector(name.decode(), vector_values, attributes or b"", quantization or "noquant", ef)
        vector_set.add(vector, numlinks or 16)
        key.update(vector_set)
        return 1

    @command(name="VEMB", fixed=(Key(VectorSet), bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vemb(self, key: CommandItem, element: bytes, *args: bytes):
        if key.value is None:
            raise SimpleError("ERR key does not exist")
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        if element not in key.value:
            return None
        if len(args) > 1:
            raise SimpleError("ERR wrong number of arguments for 'VEMB' command")
        raw = False
        if len(args) > 0 and casematch(args[0], b"raw"):
            raw = True
        vector: Vector = key.value[element]

        # Return raw format if requested
        if raw:
            # For now, we're storing vectors as fp32 (no quantization in the basic implementation)
            # Return raw format with quantization info
            raw_bytes = struct.pack(f"{len(vector.values)}f", *vector.values)

            l2_norm = sum(v * v for v in vector.values) ** 0.5
            # Return dict with quantization info
            return {
                b"quantization": vector.quantization,
                b"raw": raw_bytes,
                b"l2": l2_norm,
            }

        # Return the vector values as a list of floats
        return vector.values

    @command(name="VRANDMEMBER", fixed=(Key(VectorSet),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vrandmember(self, key: CommandItem, *args: bytes) -> Optional[Union[bytes, List[bytes]]]:
        if key.value is None:
            return None if len(args) == 0 else []
        try:
            count = 1 if len(args) == 0 else int(args[0])
        except ValueError:
            raise SimpleError("ERR COUNT value is not an integer")
        vector_set: VectorSet = key.value
        vector_names = vector_set.vector_names()
        if count < 0:  # Allow repetitions
            res = random.choices(sorted(vector_names), k=-count)
        else:  # Unique values from hash
            count = min(count, len(vector_names))
            res = random.sample(sorted(vector_names), count)
        return res[0] if len(args) == 0 else res

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
        # todo
        return 0

    @command(
        name="VRANGE",
        fixed=(Key(VectorSet), StringTest, StringTest),
        repeat=(bytes,),
        flags=msgs.FLAG_DO_NOT_CREATE,
    )
    def vrange(self, key: CommandItem, _min: StringTest, _max: StringTest, *args: bytes) -> int:
        if len(args) > 1:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("VRANGE"))
        if key.value is None:
            raise SimpleError("ERR key does not exist")
        if len(args) == 1:
            count = int(args[0])
        # todo
        print(count)
        return 0

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
