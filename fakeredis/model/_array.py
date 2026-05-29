import re
from typing import Dict, List, Optional, Tuple


from fakeredis.model._base_type import BaseModel


class Array(BaseModel):
    _model_type = b"array"

    def __init__(self) -> None:
        self._data: Dict[int, bytes] = {}
        self._cursor: int = 0
        # ordered dict used as ordered set: index -> None, keyed by last-insert time
        self._insertion_order: Dict[int, None] = {}

    def __len__(self) -> int:
        return len(self._data)

    def length(self) -> int:
        """ARLEN: max_index + 1, or 0 if empty."""
        if not self._data:
            return 0
        return max(self._data) + 1

    def count(self) -> int:
        """ARCOUNT: number of non-empty (set) elements."""
        return len(self._data)

    def get(self, index: int) -> Optional[bytes]:
        return self._data.get(index)

    def set(self, index: int, value: bytes) -> bool:
        """Set value at index. Returns True if slot was previously empty."""
        is_new = index not in self._data
        self._data[index] = value
        return is_new

    def delete(self, index: int) -> bool:
        """Delete element at index. Returns True if something was deleted."""
        if index in self._data:
            del self._data[index]
            self._insertion_order.pop(index, None)
            return True
        return False

    def truncate_at(self, size: int) -> None:
        """Remove all elements at index >= size (used by ARRING)."""
        for k in [k for k in self._data if k >= size]:
            self.delete(k)

    def record_insert(self, index: int) -> None:
        """Record an ARINSERT/ARRING insertion for ARLASTITEMS tracking."""
        self._insertion_order.pop(index, None)
        self._insertion_order[index] = None

    def lastitems(self, count: int) -> List[bytes]:
        """Return the last `count` inserted values (oldest-first)."""
        existing = [i for i in self._insertion_order if i in self._data]
        recent = existing[-count:] if count < len(existing) else existing
        return [self._data[i] for i in recent]

    def scan_range(self, start: int, end: int, limit: Optional[int] = None) -> List[Tuple[int, bytes]]:
        """Return existing index-value pairs in [start, end] (inclusive).

        If start > end the range is traversed in descending order.
        Stops after `limit` pairs if given.
        """
        if start <= end:
            indices = sorted(k for k in self._data if start <= k <= end)
        else:
            indices = sorted((k for k in self._data if end <= k <= start), reverse=True)
        if limit is not None:
            indices = indices[:limit]
        return [(i, self._data[i]) for i in indices]

    def grep_range(
        self,
        start: int,
        end: int,
        predicates: List[Tuple[str, str]],
        use_and: bool,
        limit: Optional[int],
        nocase: bool,
    ) -> List[Tuple[int, bytes]]:
        """Return (index, value) pairs in range matching the textual predicates."""
        if start <= end:
            indices = sorted(k for k in self._data if start <= k <= end)
        else:
            indices = sorted((k for k in self._data if end <= k <= start), reverse=True)

        results: List[Tuple[int, bytes]] = []
        for idx in indices:
            val = self._data[idx]
            text = val.decode(errors="replace")
            if nocase:
                text = text.lower()

            matches = []
            for kind, pattern in predicates:
                p = pattern.lower() if nocase else pattern
                if kind == "exact":
                    matches.append(text == p)
                elif kind == "match":
                    matches.append(p in text)
                elif kind == "glob":
                    matches.append(_glob_match(p, text))
                elif kind == "re":
                    flags = re.IGNORECASE if nocase else 0
                    matches.append(bool(re.search(pattern, val.decode(errors="replace"), flags)))

            if not matches:
                continue
            hit = all(matches) if use_and else any(matches)
            if hit:
                results.append((idx, val))
                if limit is not None and len(results) >= limit:
                    break
        return results

    def op_range(self, start: int, end: int, operation: str, operand: Optional[bytes] = None):
        """Perform an aggregate operation on elements in [start, end]."""
        if start > end:
            start, end = end, start
        values = [self._data[k] for k in self._data if start <= k <= end]

        if operation == "used":
            return len(values)
        if operation == "match":
            return sum(1 for v in values if v == operand)

        if not values:
            return None

        if operation in ("and", "or", "xor"):
            result = 0
            for v in values:
                try:
                    n = int(float(v))
                except (ValueError, OverflowError):
                    n = 0
                if operation == "and":
                    result = result & n if result != 0 or values.index(v) > 0 else n
                elif operation == "or":
                    result |= n
                elif operation == "xor":
                    result ^= n
            return result

        # SUM, MIN, MAX
        nums = []
        for v in values:
            try:
                nums.append(float(v))
            except (ValueError, OverflowError):
                pass
        if not nums:
            return None
        if operation == "sum":
            total = sum(nums)
            if total == int(total):
                return str(int(total)).encode()
            return str(total).encode()
        if operation == "min":
            m = min(nums)
            if m == int(m):
                return str(int(m)).encode()
            return str(m).encode()
        if operation == "max":
            m = max(nums)
            if m == int(m):
                return str(int(m)).encode()
            return str(m).encode()
        return None


def _glob_match(pattern: str, text: str) -> bool:
    """Translate a glob pattern to regex and match."""
    regex = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".").replace(r"\[", "[").replace(r"\]", "]")
    return bool(re.fullmatch(regex, text))
