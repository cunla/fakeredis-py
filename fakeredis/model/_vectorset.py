import json
import math
import re
import struct
from typing import List, Dict, Any, Literal, Optional, Iterator, Self, Union

import numpy as np
from jsonpath_ng import JSONPath
from jsonpath_ng.exceptions import JsonPathParserError
from jsonpath_ng.ext import parse

from fakeredis import _msgs as msgs
from fakeredis._helpers import SimpleError

QUANTIZATION_TYPE = Literal["noquant", "bin", "int8"]


def _update_to_jsonpath_format(path: Union[bytes, str]) -> str:
    path_str = path.decode() if isinstance(path, bytes) else path
    path_str = path_str.replace("and", "&").replace("or", "|").replace("not", "!").replace(".", "@.")

    # Replace `v in [x, y, z]` with `(v=~'x|y|z')`
    def expand_in(m: re.Match) -> str:
        var = m.group(1)
        items = [item.strip().replace("'", "") for item in m.group(2).split(",")]
        return f"({var}=~'{'|'.join(items)}')"

    path_str = re.sub(r"(\S+)\s+in\s+\[([^]]+)]", expand_in, path_str)

    return f"$[?({path_str})]"


def _parse_jsonfilter(path: Union[str, bytes]) -> JSONPath:
    path_str: str = _update_to_jsonpath_format(path)
    try:
        return parse(path_str)
    except JsonPathParserError:
        raise SimpleError(msgs.JSON_PATH_DOES_NOT_EXIST.format(path_str))


def quantize_int8(x):
    qmin = -(2.0**7) if (x < 0).any() else 0  # Signed or unsigned range
    qmax = 2.0**7 - 1 if (x < 0).any() else 2.0**8 - 1

    min_val, max_val = x.min(), x.max()

    # Calculate the scale factor
    scale = (max_val - min_val) / (qmax - qmin)

    # Calculate the initial zero point and clamp it to the valid range
    initial_zero_point = qmin - min_val / scale
    zero_point = int(np.clip(initial_zero_point, qmin, qmax))

    # Quantize the values and round them
    q_x = zero_point + x / scale
    q_x = np.clip(q_x, qmin, qmax).round().astype(np.int8)  # Use np.int8 for the final data type

    return q_x, scale, zero_point


class Vector:
    def __init__(
        self, name: bytes, values: List[float], attributes: Optional[bytes], quantization: QUANTIZATION_TYPE, ef: int
    ) -> None:
        self.name = name
        self.values = values
        self.attributes = attributes
        self.quantization = quantization
        self.l2_norm = sum(v * v for v in values) ** 0.5
        if self.quantization == "bin":
            self.values = [1 if v > 0 else -1 for v in self.values]

    def __repr__(self):
        return f"Vector(name={self.name}, values={self.values}, attributes={self.attributes}, quantization={self.quantization})"

    def __hash__(self):
        return hash(self.name)

    @classmethod
    def from_vector_values(cls, values: List[float]) -> Self:
        return cls("", values, b"", "int8", 0)

    def raw(self) -> List[Any]:
        raw_bytes = struct.pack(f"{len(self.values)}f", *self.values)
        if self.quantization == "int8":
            norm_values = np.array(self.values) / self.l2_norm if self.l2_norm != 0 else np.array(self.values)
            range_val = float(np.max(np.abs(norm_values)))
            return [self.quantization.encode(), raw_bytes, self.l2_norm, range_val]
        if self.quantization == "bin":
            return [self.quantization.encode(), raw_bytes, self.l2_norm]

        return [b"f32", raw_bytes, self.l2_norm]

    def similarity(self, other: Self) -> float:
        me = np.array(self.values)
        o = np.array(other.values)
        denominator = self.l2_norm * other.l2_norm
        if denominator == 0:
            return 0.0
        return float(np.dot(me, o)) / denominator

    def accept_filter(self, filter_expression: Optional[bytes]) -> bool:
        if filter_expression is None:
            return True
        if self.attributes is None:
            return False
        json_obj = json.loads(self.attributes)
        return len(_parse_jsonfilter(filter_expression).find([json_obj])) > 0


class VectorSet:
    def __init__(self, dimensions: int):
        self._dimensions = dimensions
        self._vectors: Dict[bytes, Vector] = dict()
        self._links: Dict[bytes, int] = dict()
        self._quant_type: Optional[str] = None
        self._node_uid_counter: int = 0
        self._max_level: int = 0
        self._node_levels: Dict[bytes, int] = dict()
        self._node_links: Dict[bytes, Dict[int, List[bytes]]] = dict()

    @staticmethod
    def _compute_level(node_index: int, m: int) -> int:
        if m <= 1:
            return 0
        return int(math.log(node_index + 1) / math.log(m))

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def card(self) -> int:
        return len(self._vectors)

    def vector_names(self) -> List[bytes]:
        return list(self._vectors.keys())

    def exists(self, name: bytes) -> bool:
        return name in self._vectors

    def add(self, vector: Vector, numlinks: int) -> None:
        if self._quant_type is None:
            self._quant_type = vector.quantization

        node_index = self._node_uid_counter
        self._node_uid_counter += 1

        level = self._compute_level(node_index, numlinks)
        self._node_levels[vector.name] = level
        if level > self._max_level:
            self._max_level = level

        # Build links for this node at each of its levels
        self._node_links[vector.name] = {}
        query = np.array(vector.values)
        for lvl in range(level + 1):
            candidates = [name for name, level in self._node_levels.items() if level >= lvl and name != vector.name]
            if candidates:
                scored = []
                for name in candidates:
                    cand = self._vectors[name]
                    cand_arr = np.array(cand.values)
                    norm = vector.l2_norm * cand.l2_norm
                    sim = float(np.dot(query, cand_arr)) / norm if norm > 0 else 0.0
                    scored.append((name, sim))
                scored.sort(key=lambda x: x[1], reverse=True)
                self._node_links[vector.name][lvl] = [n for n, _ in scored[:numlinks]]
            else:
                self._node_links[vector.name][lvl] = []

        self._vectors[vector.name] = vector
        self._links[vector.name] = numlinks

    def remove(self, name: bytes) -> int:
        if name not in self._vectors:
            return 0
        del self._vectors[name]
        del self._links[name]
        self._node_levels.pop(name, None)
        if name in self._node_links:
            del self._node_links[name]
        for levels_links in self._node_links.values():
            for neighbors in levels_links.values():
                if name in neighbors:
                    neighbors.remove(name)
        return 1

    def info(self) -> Dict[bytes, Any]:
        quant = self._quant_type or b"fp32"
        # Normalize quantization type name for the info response
        if quant == "noquant":
            quant = b"f32"
        return {
            b"quant-type": quant.encode() if isinstance(quant, str) else quant,
            b"vector-dim": self._dimensions,
            b"size": len(self._vectors),
            b"max-level": self._max_level,
            b"vset-uid": 1,
            b"hnsw-max-node-uid": self._node_uid_counter,
        }

    def links(self, name: bytes) -> Optional[Dict[int, List[bytes]]]:
        if name not in self._vectors:
            return None
        return self._node_links.get(name, {0: []})

    def range(
        self,
        min_value: Optional[bytes],
        include_min: bool,
        max_value: Optional[bytes],
        include_max: bool,
        count: Optional[int],
    ) -> List[bytes]:
        if count is not None and count < 0:
            count = None
        res: List[bytes] = []
        for name in self._vectors.keys():
            if (min_value is None or name > min_value or (include_min and name == min_value)) and (
                max_value is None or name < max_value or (include_max and name == max_value)
            ):
                res.append(name)
            if count is not None and len(res) >= count:
                break
        return res

    def __contains__(self, k: bytes) -> bool:
        return k in self._vectors

    def __getitem__(self, k: bytes) -> Vector:
        if k not in self._vectors:
            raise KeyError(f"Vector with name {k} does not exist.")
        return self._vectors[k]

    def __iter__(self) -> Iterator[Vector]:
        return iter(self._vectors.values())

    def get(self, k: bytes) -> Optional[Vector]:
        if k in self._vectors:
            return self._vectors[k]
        return None
