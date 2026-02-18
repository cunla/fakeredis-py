from typing import List, Dict, Any, Literal, Optional

QUANTIZATION_TYPE = Literal["noquant", "bin", "q8"]


class Vector:
    def __init__(
        self, name: str, values: List[float], attributes: bytes, quantization: QUANTIZATION_TYPE, ef: int
    ) -> None:
        self.name = name
        self.values = values
        self.attributes = attributes
        self.quantization = quantization
        if self.quantization == "bin":
            self.values = [1 if v > 0 else -1 for v in self.values]

    def __repr__(self):
        return f"Vector(name={self.name}, values={self.values}, attributes={self.attributes}, quantization={self.quantization})"


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
        self._vectors[vector.name.encode()] = vector
        self._links[vector.name.encode()] = numlinks  # type: ignore

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
