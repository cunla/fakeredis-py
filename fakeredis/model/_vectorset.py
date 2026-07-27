from __future__ import annotations

import json
import math
import re
import struct
from collections import OrderedDict
from collections.abc import Iterator
from functools import lru_cache
from typing import Any, Literal

import numpy as np
from jsonpath_ng import JSONPath
from jsonpath_ng.exceptions import JSONPathError
from jsonpath_ng.ext import parse

from fakeredis import _msgs as msgs
from fakeredis._helpers import SimpleError
from fakeredis._typing import Self

QUANTIZATION_TYPE = Literal["noquant", "bin", "int8"]


def _update_to_jsonpath_format(path: bytes | str) -> str:
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
def _parse_jsonfilter(path: str | bytes) -> JSONPath:
    path_str: str = _update_to_jsonpath_format(path)
    try:
        return parse(path_str)
    except JSONPathError:
        raise SimpleError(msgs.JSON_PATH_DOES_NOT_EXIST.format(path_str))


class Vector:
    def __init__(
        self, name: bytes, values: list[float], attributes: bytes | None, quantization: QUANTIZATION_TYPE, ef: int
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
    def from_vector_values(cls, values: list[float]) -> Self:
        return cls(b"", values, b"", "int8", 0)

    def raw(self) -> list[Any]:
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
        self._vectors: dict[bytes, Vector] = {}
        self._links: dict[bytes, int] = {}
        self._quant_type: str | None = None
        self._node_uid_counter: int = 0
        self._max_level: int = 0
        self._node_links: dict[bytes, dict[int, set[bytes]]] = {}
        # Row-oriented cache of the set, kept in sync with ``_vectors``: row ``i`` of
        # each array describes ``_row_vectors[i]``, in insertion order. Keeping the
        # matrix resident lets VADD and VSIM issue a single gemv instead of restacking
        # every stored vector on each call.
        self._row_vectors: list[Vector] = []
        self._matrix: np.ndarray = np.zeros((0, dimensions), dtype=np.float32)
        self._norms: np.ndarray = np.zeros(0, dtype=np.float64)
        self._row_levels: np.ndarray = np.zeros(0, dtype=np.int64)

    @staticmethod
    def _compute_level(node_index: int, m: int) -> int:
        if m <= 1:
            return 0
        return int(math.log(node_index + 1) / math.log(m))

    def _reserve(self, size: int) -> None:
        """Grow the cache arrays (doubling) so they can hold at least ``size`` rows."""
        capacity = self._matrix.shape[0]
        if size <= capacity:
            return
        new_capacity = max(8, capacity * 2, size)
        matrix = np.zeros((new_capacity, self._dimensions), dtype=np.float32)
        matrix[:capacity] = self._matrix
        norms = np.zeros(new_capacity, dtype=np.float64)
        norms[:capacity] = self._norms
        levels = np.zeros(new_capacity, dtype=np.int64)
        levels[:capacity] = self._row_levels
        self._matrix, self._norms, self._row_levels = matrix, norms, levels

    def _append_row(self, vector: Vector, level: int) -> None:
        row = len(self._row_vectors)
        self._reserve(row + 1)
        self._matrix[row] = vector._arr
        self._norms[row] = vector.l2_norm
        self._row_levels[row] = level
        self._row_vectors.append(vector)

    def _drop_row(self, name: bytes) -> None:
        """Remove ``name``'s row, shifting later rows down to preserve insertion order."""
        row = next(i for i, v in enumerate(self._row_vectors) if v.name == name)
        n = len(self._row_vectors)
        self._matrix[row : n - 1] = self._matrix[row + 1 : n]
        self._norms[row : n - 1] = self._norms[row + 1 : n]
        self._row_levels[row : n - 1] = self._row_levels[row + 1 : n]
        del self._row_vectors[row]

    def _similarities(self, query: Vector) -> np.ndarray:
        """Cosine similarity of every stored vector against ``query``, in row order."""
        n = len(self._row_vectors)
        norms = self._norms[:n] * query.l2_norm
        dots = (self._matrix[:n] @ query._arr).astype(np.float64)
        valid = norms > 0
        return np.where(valid, dots / np.where(valid, norms, 1.0), 0.0)

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def card(self) -> int:
        return len(self._vectors)

    def vector_names(self) -> list[bytes]:
        return list(self._vectors.keys())

    def exists(self, name: bytes) -> bool:
        return name in self._vectors

    def add(self, vector: Vector, numlinks: int) -> None:
        if self._quant_type is None:
            self._quant_type = vector.quantization

        # Re-adding an existing name replaces it; drop the stale row first so the cache
        # keeps one row per member.
        if vector.name in self._vectors:
            self._drop_row(vector.name)
            del self._vectors[vector.name]

        node_index = self._node_uid_counter
        self._node_uid_counter += 1

        level = self._compute_level(node_index, numlinks)
        self._max_level = max(self._max_level, level)

        # Build links for this node at each of its levels. Similarities do not depend on
        # the level, so they are computed once and each level just narrows the candidates.
        self._node_links[vector.name] = {}
        candidate_levels = self._row_levels[: len(self._row_vectors)]
        sims = self._similarities(vector)
        for lvl in range(level + 1):
            cand_rows = np.flatnonzero(candidate_levels >= lvl)
            if cand_rows.size == 0:
                self._node_links[vector.name][lvl] = set()
                continue
            cand_sims = sims[cand_rows]
            k = min(numlinks, cand_rows.size)
            if k < cand_rows.size:
                top_idx = np.argpartition(cand_sims, -k)[-k:]
                top_idx = top_idx[np.argsort(cand_sims[top_idx])[::-1]]
            else:
                top_idx = np.argsort(cand_sims)[::-1]
            self._node_links[vector.name][lvl] = {self._row_vectors[cand_rows[i]].name for i in top_idx}

        self._append_row(vector, level)
        self._vectors[vector.name] = vector
        self._links[vector.name] = numlinks

    def remove(self, name: bytes) -> int:
        if name not in self._vectors:
            return 0
        self._drop_row(name)
        del self._vectors[name]
        del self._links[name]
        if name in self._node_links:
            del self._node_links[name]
        for levels_links in self._node_links.values():
            for neighbors in levels_links.values():
                neighbors.discard(name)
        return 1

    def info(self) -> dict[bytes, Any]:
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

    def links(self, name: bytes) -> dict[int, list[bytes]] | None:
        if name not in self._vectors:
            return None
        node_links = self._node_links.get(name, {0: set()})
        return {lvl: list(neighbors) for lvl, neighbors in node_links.items()}

    def range(
        self,
        min_value: bytes | None,
        include_min: bool,
        max_value: bytes | None,
        include_max: bool,
        count: int | None,
    ) -> list[bytes]:
        if count is not None and count < 0:
            count = None
        res: list[bytes] = []
        for name in self._vectors:
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

    def get(self, k: bytes) -> Vector | None:
        if k in self._vectors:
            return self._vectors[k]
        return None

    def top_similar(
        self,
        query: Vector,
        filter_expression: bytes | None,
        count: int,
        epsilon: float | None,
        filter_ef: int | None = None,
    ) -> OrderedDict[Vector, float]:
        """Return the top-``count`` most similar vectors to ``query``.

        Vectors are examined in best-first order (most similar first), mimicking the
        exploration order of an HNSW search. When a ``filter_expression`` is supplied,
        ``filter_ef`` bounds the *filtering effort*: at most that many vectors are
        examined while looking for matches. Redis defaults this to ``count * 100`` and
        treats ``0`` as unlimited. A small ``filter_ef`` may therefore miss matches
        that lie far from the query vector, exactly as real Redis does.
        """
        all_vectors = self._row_vectors
        if not all_vectors:
            return OrderedDict()
        cosine = self._similarities(query)  # one BLAS gemv call over the resident matrix
        scores = (1.0 + cosine) / 2.0
        # Best-first exploration order: most similar candidate first.
        order = np.argsort(scores)[::-1]

        parsed_filter = None if filter_expression is None else _parse_jsonfilter(filter_expression)
        if filter_expression is None:
            max_effort = len(all_vectors)  # exact search when unfiltered
        elif filter_ef is None:
            max_effort = count * 100  # Redis default filtering effort
        elif filter_ef <= 0:
            max_effort = len(all_vectors)  # 0 means unlimited effort
        else:
            max_effort = filter_ef
        threshold = None if epsilon is None else 1.0 - epsilon

        results: OrderedDict[Vector, float] = OrderedDict()
        examined = 0
        for idx in order:
            if examined >= max_effort:
                break
            examined += 1
            vector = all_vectors[idx]
            if not self._passes_filter(vector, parsed_filter):
                continue
            score = float(scores[idx])
            if threshold is not None and score < threshold:
                continue
            results[vector] = score
            if len(results) >= count:
                break
        return results

    @staticmethod
    def _passes_filter(vector: Vector, parsed_filter: JSONPath | None) -> bool:
        if parsed_filter is None:
            return True
        if vector.attributes is None:
            return False
        return len(parsed_filter.find([json.loads(vector.attributes)])) > 0
