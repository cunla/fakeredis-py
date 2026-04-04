import itertools
import random
import struct
from collections import OrderedDict
from typing import Any, List, Optional, Union, Dict

from fakeredis import _msgs as msgs
from fakeredis._commands import Key, command, CommandItem, StringTest
from fakeredis._helpers import SimpleError, casematch
from fakeredis.model import VectorSet, Vector

VSET_ERR_NOTEXIST = "ERR key does not exist"


class VectorSetCommandsMixin:
    """`CommandsMixin` for enabling VectorSet compatibility in `fakeredis`."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    @command(name="VCARD", fixed=(Key(VectorSet),), flags=msgs.FLAG_DO_NOT_CREATE)
    def vcard(self, key: CommandItem) -> Optional[int]:
        if key.value is None:
            return None
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        return key.value.card

    @command(name="VDIM", fixed=(Key(VectorSet),), flags=msgs.FLAG_DO_NOT_CREATE)
    def vdim(self, key: CommandItem) -> int:
        if key.value is None:
            raise SimpleError(VSET_ERR_NOTEXIST)
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
        key.value[member].attributes = attr
        key.update(key.value)
        return 1

    @command(name="VADD", fixed=(Key(VectorSet),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vadd(self, key: CommandItem, *args: bytes) -> int:
        i = 0
        numlinks, reduce, cas, vector_values, name, attributes, quantization, ef = [None] * 8

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
                if quantization == "q8":
                    quantization = "int8"
                i += 1
            elif casematch(args[i], b"values") and i + 1 < len(args):
                num_values = int(args[i + 1])
                i += 2
                if i + num_values > len(args):  # VALUES num_values values element
                    raise SimpleError(msgs.WRONG_ARGS_MSG6.format("VADD"))
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
            vector_values = vector_values[:dimensions]

        if vector_set.exists(name):
            return 0

        vector = Vector(name, vector_values, attributes, quantization or "int8", ef)
        vector_set.add(vector, numlinks or 16)
        key.update(vector_set)
        return 1

    @command(name="VEMB", fixed=(Key(VectorSet), bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vemb(self, key: CommandItem, element: bytes, *args: bytes) -> List[float]:
        if key.value is None:
            return None
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
            return vector.raw()
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

    @command(
        name="VRANGE",
        fixed=(Key(VectorSet), StringTest, StringTest),
        repeat=(bytes,),
        flags=msgs.FLAG_DO_NOT_CREATE,
    )
    def vrange(self, key: CommandItem, _min: StringTest, _max: StringTest, *args: bytes) -> List[bytes]:
        if len(args) > 1:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("VRANGE"))
        if key.value is None:
            return []
        vset = key.value
        if not isinstance(vset, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        count = None
        if len(args) == 1:
            count = int(args[0])
        if count == 0:
            return []
        res = vset.range(_min.value, _min.inclusive, _max.value, _max.inclusive, count)
        return res

    @command(name="VSIM", fixed=(Key(VectorSet),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vsim(self, key: CommandItem, *args: bytes) -> Union[List[bytes], Dict[bytes, float]]:
        """
        VSIM key (ELE | FP32 | VALUES num) (vector | element) [WITHSCORES] [WITHATTRIBS] [COUNT num]
          [EPSILON delta] [EF search-exploration-factor] [FILTER expression] [FILTER-EF max-filtering-effort]
          [TRUTH] [NOTHREAD]
        """
        if key.value is None:
            return []
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        vector_set: VectorSet = key.value
        vector: Optional[Vector] = None  # The vector to compare against.
        with_scores, with_attributes, count, epsilon, filter_expression = False, False, 10, None, None
        i = 0
        while i < len(args):
            if casematch(args[i], b"ele") and i + 1 < len(args):
                if vector is not None:
                    raise SimpleError("ERR ELE | FP32 | VALUES num")
                vector = key.value.get(args[i + 1])
                if vector is None:
                    raise SimpleError("element not found in set")
                i += 2
            elif casematch(args[i], b"fp32") and i + 1 < len(args):
                if vector is not None:
                    raise SimpleError("ERR ELE | FP32 | VALUES num")
                byte_array = args[i + 1]
                vector_values = list(struct.unpack(f"{len(byte_array) // 4}f", byte_array))
                vector = Vector.from_vector_values(vector_values)
                i += 2
            elif casematch(args[i], b"values") and i + 1 < len(args):
                if vector is not None:
                    raise SimpleError("ERR ELE | FP32 | VALUES num")
                num_values = int(args[i + 1])
                i += 2
                if i + num_values > len(args):  # VALUES num_values values element
                    raise SimpleError(msgs.WRONG_ARGS_MSG6.format("VADD"))
                vector_values = [float(v) for v in args[i : i + num_values]]
                vector = Vector.from_vector_values(vector_values)
                i += num_values
            elif casematch(args[i], b"withscores"):
                with_scores = True
                i += 1
            elif casematch(args[i], b"withattribs"):
                with_attributes = True
                i += 1
            elif casematch(args[i], b"count") and i + 1 < len(args):
                count = int(args[i + 1])
                i += 2
            elif casematch(args[i], b"epsilon") and i + 1 < len(args):
                epsilon = float(args[i + 1])
                i += 2
            elif casematch(args[i], b"ef") and i + 1 < len(args):
                ef = int(args[i + 1])  # noqa: F841
                i += 2
            elif casematch(args[i], b"filter") and i + 1 < len(args):
                filter_expression = args[i + 1]
                i += 2
            elif casematch(args[i], b"filter-ef") and i + 1 < len(args):
                filter_expression_ef = args[i + 1]  # noqa: F841
                i += 2
            elif casematch(args[i], b"truth"):
                i += 1
            elif casematch(args[i], b"nothread"):
                i += 1
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)

        if vector is None:
            raise SimpleError(VSET_ERR_NOTEXIST)
        res: Dict[Vector, float] = {v: v.similarity(vector) for v in vector_set if v.accept_filter(filter_expression)}
        if epsilon is not None:
            res = {k: v for k, v in res.items() if v >= 1 - epsilon}
        res = OrderedDict(itertools.islice(sorted(res.items(), key=lambda t: t[1], reverse=True), count))
        if with_scores and with_attributes:
            if self._client_info.protocol_version == 2:
                return list(itertools.chain.from_iterable([[k.name, v, k.attributes] for k, v in res.items()]))
            return {k.name: [v, k.attributes] for k, v in res.items()}
        if with_scores:
            return {k.name: v for k, v in res.items()}
        if with_attributes:
            return {k.name: k.attributes for k in res}
        return [k.name for k in res]

    @command(name="VINFO", fixed=(Key(VectorSet),), flags=msgs.FLAG_DO_NOT_CREATE)
    def vinfo(self, key: CommandItem):
        if key.value is None:
            return None
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        info = key.value.info()
        return info

    @command(name="VLINKS", fixed=(Key(VectorSet), bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def vlinks(self, key: CommandItem, elem: bytes, *args: bytes):
        if key.value is None:
            return None
        if not isinstance(key.value, VectorSet):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        vset: VectorSet = key.value
        if elem not in vset:
            return None
        with_scores = len(args) > 0 and casematch(args[0], b"withscores")
        node_links = vset.links(elem)
        levels = sorted(node_links.keys())
        if not with_scores:
            # Both RESP2 and RESP3: list of lists of bytes names per layer
            return [node_links[lvl] for lvl in levels]
        query_vector = vset[elem]
        result = []
        for lvl in levels:
            layer_dict = {}
            for name in node_links[lvl]:
                if name in vset:
                    layer_dict[name] = vset[name].similarity(query_vector)
            result.append(layer_dict)
        return result
