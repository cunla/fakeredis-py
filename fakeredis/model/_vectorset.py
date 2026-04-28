import json
import math
import re
import struct
from collections import OrderedDict
from functools import lru_cache
from typing import List, Dict, Any, Literal, Optional, Iterator, Self, Union, Set

import numpy as np
from jsonpath_ng import JSONPath
from jsonpath_ng.exceptions import JSONPathError
from jsonpath_ng.ext import parse

from fakeredis import _msgs as msgs
from fakeredis._helpers import SimpleError

QUANTIZATION_TYPE = Literal["noquant", "bin", "int8"]


def _update_to_jsonpath_format(path: Union[bytes, str]) -> str:
    path_str = path.decode() if isinstance(path, bytes) else path
    path_str = re.sub(r"\band\b", "&", path_str)
    path_str = re.sub(r"\bor\b", "|", path_str)
    path_str = re.sub(r"\bnot\b", "!", path_str)
    path_str = path_str.replace(".", "@.")

    # Replace `v in [x, y, z]` with `(v=~'x|y|z')`
    def expand_in(m: re.Match[str]) -> str:
        var = m.group(1)
        items = [item.strip().replace("'", "") for item in m.group(2).split(",")]
        return f"({var}=~'{'|'.join(items)}')"

    path_str = re.sub(r"(\S+)\s+in\s+\[([^]]+)]", expand_in, path_str)

    return f"$[?({path_str})]"


@lru_cache(maxsize=64)
def _parse_jsonfilter(path: Union[str, bytes]) -> JSONPath:
    path_str: str = _update_to_jsonpath_format(path)
    try:
        return parse(path_str)
    except JSONPathError:
        raise SimpleError(msgs.JSON_PATH_DOES_NOT_EXIST.format(path_str))


class Vector:
    def __init__(
        self, name: bytes, values: List[float], attributes: Optional[bytes], quantization: QUANTIZATION_TYPE, ef: int
    ) -> None:
        self.name = name
        self.values = values
        self.attributes = attributes
        self.quantization = quantization
        _raw = np.array(values, dtype=np.float32)
        self.l2_norm = float(np.linalg.norm(_raw))
        if self.quantization == "bin":
            self.values = [1 if v > 0 else -1 for v in self.values]
            self._arr = np.array(self.values, dtype=np.float32)
        else:
            self._arr = _raw

    def __repr__(self) -> str:
        return f"Vector(name={self.name!r}, values={self.values}, attributes={self.attributes!r}, quantization={self.quantization})"

    def __hash__(self) -> int:
        return hash(self.name)

    @classmethod
    def from_vector_values(cls, values: List[float]) -> Self:
        return cls(b"", values, b"", "int8", 0)

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
        denominator = self.l2_norm * other.l2_norm
        if denominator == 0:
            return 0.5
        cosine_sim: float = float(np.dot(self._arr, other._arr)) / denominator
        return (1.0 + cosine_sim) / 2.0


class VectorSet:
    def __init__(self, dimensions: int):
        self._dimensions = dimensions
        self._vectors: Dict[bytes, Vector] = dict()
        self._links: Dict[bytes, int] = dict()
        self._quant_type: Optional[str] = None
        self._node_uid_counter: int = 0
        self._max_level: int = 0
        self._node_levels: Dict[bytes, int] = dict()
        self._node_links: Dict[bytes, Dict[int, Set[bytes]]] = dict()

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
        query_arr = vector._arr
        query_norm = vector.l2_norm
        for lvl in range(level + 1):
            cand_names = [n for n, node_lvl in self._node_levels.items() if node_lvl >= lvl and n != vector.name]
            if cand_names:
                cand_vecs = [self._vectors[n] for n in cand_names]
                cand_matrix = np.stack([c._arr for c in cand_vecs])
                cand_norms = np.array([c.l2_norm for c in cand_vecs], dtype=np.float64) * query_norm
                dots = (cand_matrix @ query_arr).astype(np.float64)
                valid = cand_norms > 0
                sims = np.where(valid, dots / np.where(valid, cand_norms, 1.0), 0.0)
                k = min(numlinks, len(cand_names))
                if k < len(cand_names):
                    top_idx = np.argpartition(sims, -k)[-k:]
                    top_idx = top_idx[np.argsort(sims[top_idx])[::-1]]
                else:
                    top_idx = np.argsort(sims)[::-1]
                self._node_links[vector.name][lvl] = {cand_names[i] for i in top_idx}
            else:
                self._node_links[vector.name][lvl] = set()

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
                neighbors.discard(name)
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
        node_links = self._node_links.get(name, {0: set()})
        return {lvl: list(neighbors) for lvl, neighbors in node_links.items()}

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
            raise KeyError(f"Vector with name {k!r} does not exist.")
        return self._vectors[k]

    def __iter__(self) -> Iterator[Vector]:
        return iter(self._vectors.values())

    def get(self, k: bytes) -> Optional[Vector]:
        if k in self._vectors:
            return self._vectors[k]
        return None

    def top_similar(
        self,
        query: Vector,
        filter_expression: Optional[bytes],
        count: int,
        epsilon: Optional[float],
    ) -> "OrderedDict[Vector, float]":
        """Return top-k most similar vectors using a single batched matrix operation."""
        candidates = self.accept_filter(filter_expression)
        if not candidates:
            return OrderedDict()
        arr_matrix = np.stack([v._arr for v in candidates])  # (n, d) float32
        norms = np.array([v.l2_norm for v in candidates], dtype=np.float64) * query.l2_norm
        dots = (arr_matrix @ query._arr).astype(np.float64)  # one BLAS gemv call
        valid = norms > 0
        cosine = np.where(valid, dots / np.where(valid, norms, 1.0), 0.0)
        scores = (1.0 + cosine) / 2.0
        if epsilon is not None:
            mask = scores >= 1.0 - epsilon
            candidates = [v for v, keep in zip(candidates, mask) if keep]
            scores = scores[mask]
        n = len(candidates)
        if n == 0:
            return OrderedDict()
        k = min(count, n)
        if k < n:
            top_idx = np.argpartition(scores, -k)[-k:]
            top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]
        else:
            top_idx = np.argsort(scores)[::-1]
        return OrderedDict((candidates[i], float(scores[i])) for i in top_idx)

    def accept_filter(self, filter_expression: Optional[bytes]) -> list[Vector]:
        if filter_expression is None:
            return list(self._vectors.values())
        parsed_expression = _parse_jsonfilter(filter_expression)
        res = [
            i
            for i in self._vectors.values()
            if i.attributes is not None and (len(parsed_expression.find([json.loads(i.attributes)])) > 0)
        ]
        return res
