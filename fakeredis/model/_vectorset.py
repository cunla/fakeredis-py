from typing import List, Dict


class Vector:
    def __init__(self, name: str, values: List[float], attributes: bytes) -> None:
        self.name = name
        self.values = values
        self.attributes = attributes

    def __repr__(self):
        return f"Vector(name={self.name}, values={self.values}, attributes={self.attributes})"


class VectorSet:
    def __init__(self, dimensions: int):
        self._dimensions = dimensions
        self._vectors: Dict[bytes, Vector] = dict()

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def card(self) -> int:
        return len(self._vectors)

    def __contains__(self, k: bytes) -> bool:
        return k in self._vectors

    def __getitem__(self, k: bytes) -> Vector:
        if k not in self._vectors:
            raise KeyError(f"Vector with name {k} does not exist.")
        return self._vectors[k]
