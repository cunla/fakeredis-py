import json
import struct
from typing import List, Dict, Any, Literal, Optional, Iterator, Self, Union

import numpy as np
from jsonpath_ng import JSONPath
from jsonpath_ng.exceptions import JsonPathParserError
from jsonpath_ng.ext import parse

from fakeredis import _msgs as msgs
from fakeredis._helpers import SimpleError

QUANTIZATION_TYPE = Literal["noquant", "bin", "int8"]


def _format_path(path: Union[bytes, str]) -> str:
    path_str = path.decode() if isinstance(path, bytes) else path
    path_str = " & ".join(["@" + i.strip() for i in path_str.split("&")])
    return f"$[?({path_str})]"


def _parse_jsonfilter(path: Union[str, bytes]) -> JSONPath:
    path_str: str = _format_path(path)
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
            q_values, scale, zero_point = quantize_int8(np.array(self.values))
            return [self.quantization.encode(), raw_bytes, self.l2_norm, scale, zero_point]
        if self.quantization == "bin":
            return [self.quantization.encode(), raw_bytes, self.l2_norm]

        return [b"f32", raw_bytes, self.l2_norm]

    def similarity(self, other: Self) -> float:
        me = np.array(self.values)
        other = np.array(other.values)
        return float(np.dot(me, other) / (np.linalg.norm(me) * np.linalg.norm(other)))

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
        self._vectors[vector.name] = vector
        self._links[vector.name] = numlinks  # type: ignore

    def remove(self, name: bytes) -> int:
        if name not in self._vectors:
            return 0
        del self._vectors[name]
        del self._links[name]
        return 1

    def info(self) -> Dict[str, Any]:
        return {
            "quant-type": "fp32",
            "vector-dim": self._dimensions,
            "size": len(self._vectors),
            "max-level": 0,  # TODO
            "vset-uid": 1,  # TODO
            "hnsw-max-node-uid": 0,  # TODO
        }

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
