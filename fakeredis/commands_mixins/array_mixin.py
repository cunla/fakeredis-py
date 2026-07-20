from typing import Any, List, Optional, Set, Tuple

from fakeredis import _msgs as msgs
from fakeredis._commands import Key, Int, command, CommandItem
from fakeredis._helpers import SimpleError, casematch
from fakeredis.commands_mixins._mixin_base import CommandsMixinBase
from fakeredis.model._array import Array

_ARRAY_WRONG_TYPE = msgs.WRONGTYPE_MSG
_INDEX_ERROR = "ERR index out of range"
_INVALID_SIZE = "ERR invalid size"
_UNKNOWN_OP = "ERR unknown operation"


def _parse_range_end(val: bytes, array: Array, is_start: bool) -> int:
    """Parse start/end arg: b'-' → 0, b'+' → max_index, otherwise int."""
    if val == b"-":
        return 0
    if val == b"+":
        return max(array._data.keys(), default=0)
    try:
        return int(val)
    except ValueError:
        raise SimpleError(msgs.INVALID_INT_MSG)


class ArrayCommandsMixin(CommandsMixinBase):
    # ── write commands ──────────────────────────────────────────────────────

    @command((Key(Array), Int, bytes), (bytes,))
    def arset(self, key: CommandItem, index: int, first_val: bytes, *more_vals: bytes) -> int:
        if index < 0:
            raise SimpleError(_INDEX_ERROR)
        arr: Array = key.value
        new_slots = 0
        for i, val in enumerate([first_val] + list(more_vals)):
            if arr.set(index + i, val):
                new_slots += 1
        key.updated()
        return new_slots

    @command((Key(Array), Int, bytes), (Int, bytes))
    def armset(self, key: CommandItem, *args: Any) -> int:
        # args: index1, val1, index2, val2, ...
        arr: Array = key.value
        new_slots = 0
        for i in range(0, len(args), 2):
            idx, val = args[i], args[i + 1]
            if idx < 0:
                raise SimpleError(_INDEX_ERROR)
            if arr.set(idx, val):
                new_slots += 1
        key.updated()
        return new_slots

    @command((Key(Array), bytes), (bytes,))
    def arinsert(self, key: CommandItem, first_val: bytes, *more_vals: bytes) -> int:
        arr: Array = key.value
        last_idx = arr._cursor
        for val in [first_val] + list(more_vals):
            arr.set(arr._cursor, val)
            arr.record_insert(arr._cursor)
            last_idx = arr._cursor
            arr._cursor += 1
        key.updated()
        return last_idx

    @command((Key(Array), Int, bytes), (bytes,))
    def arring(self, key: CommandItem, size: int, first_val: bytes, *more_vals: bytes) -> int:
        if size <= 0:
            raise SimpleError(_INVALID_SIZE)
        arr: Array = key.value
        if arr.length() > size:
            arr.truncate_at(size)
        last_idx = arr._cursor % size
        for val in [first_val] + list(more_vals):
            idx = arr._cursor % size
            arr.set(idx, val)
            arr.record_insert(idx)
            last_idx = idx
            arr._cursor += 1
        key.updated()
        return last_idx

    @command((Key(Array, 0), Int), (Int,))
    def ardel(self, key: CommandItem, first_idx: int, *more_idx: int) -> int:
        if not key:
            return 0
        arr: Array = key.value
        deleted = 0
        for idx in [first_idx] + list(more_idx):
            if arr.delete(idx):
                deleted += 1
        if deleted:
            key.updated()
        return deleted

    @command((Key(Array, 0), Int, Int), (Int, Int))
    def ardelrange(self, key: CommandItem, *args: int) -> int:
        if not key:
            return 0
        arr: Array = key.value
        # args: start1, end1, start2, end2, ...
        to_delete: Set[int] = set()
        for i in range(0, len(args), 2):
            start, end = args[i], args[i + 1]
            lo, hi = (start, end) if start <= end else (end, start)
            to_delete.update(k for k in arr._data if lo <= k <= hi)
        for idx in to_delete:
            arr.delete(idx)
        if to_delete:
            key.updated()
        return len(to_delete)

    @command((Key(Array, 0), Int))
    def arseek(self, key: CommandItem, index: int) -> int:
        if not key:
            return 0
        arr: Array = key.value
        arr._cursor = index
        key.updated()
        return 1

    # ── read commands ────────────────────────────────────────────────────────

    @command((Key(Array, None), Int))
    def arget(self, key: CommandItem, index: int) -> Optional[bytes]:
        if not key:
            return None
        arr: Array = key.value
        return arr.get(index)

    @command((Key(Array), Int, Int))
    def argetrange(self, key: CommandItem, start: int, end: int) -> List[Optional[bytes]]:
        if start <= end:
            indices = list(range(start, end + 1))
        else:
            indices = list(range(start, end - 1, -1))
        if not key:
            return [None] * len(indices)
        arr: Array = key.value
        return [arr.get(i) for i in indices]

    @command((Key(Array), Int), (Int,))
    def armget(self, key: CommandItem, first_idx: int, *more_idx: int) -> List[Optional[bytes]]:
        arr: Array = key.value
        return [arr.get(idx) for idx in [first_idx] + list(more_idx)]

    @command((Key(Array, 0),))
    def arlen(self, key: CommandItem) -> int:
        if not key:
            return 0
        arr: Array = key.value
        return arr.length()

    @command((Key(Array, 0),))
    def arcount(self, key: CommandItem) -> int:
        if not key:
            return 0
        arr: Array = key.value
        return arr.count()

    @command((Key(Array, 0),))
    def arnext(self, key: CommandItem) -> int:
        if not key:
            return 0
        arr: Array = key.value
        return arr._cursor

    @command((Key(Array, []), Int), (bytes,))
    def arlastitems(self, key: CommandItem, count: int, *args: bytes) -> List[bytes]:
        if not key:
            return []
        rev = any(casematch(a, b"rev") for a in args)
        arr: Array = key.value
        items = arr.lastitems(count)
        if rev:
            items = list(reversed(items))
        return items

    @command((Key(Array, []), bytes, bytes), (bytes,))
    def arscan(self, key: CommandItem, start_b: bytes, end_b: bytes, *args: bytes) -> List[Any]:
        if not key:
            return []
        arr: Array = key.value
        try:
            start = int(start_b)
            end = int(end_b)
        except ValueError:
            raise SimpleError(msgs.INVALID_INT_MSG)

        limit: Optional[int] = None
        i = 0
        while i < len(args):
            if casematch(args[i], b"limit"):
                if i + 1 >= len(args):
                    raise SimpleError(msgs.SYNTAX_ERROR_MSG)
                try:
                    limit = int(args[i + 1])
                except ValueError:
                    raise SimpleError(msgs.INVALID_INT_MSG)
                i += 2
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)

        pairs = arr.scan_range(start, end, limit)
        return [[idx, val] for idx, val in pairs]

    @command((Key(Array, []), bytes, bytes), (bytes,))
    def argrep(self, key: CommandItem, start_b: bytes, end_b: bytes, *args: bytes) -> List[Any]:
        if not key:
            return []
        arr: Array = key.value
        start = _parse_range_end(start_b, arr, is_start=True)
        end = _parse_range_end(end_b, arr, is_start=False)

        predicates: List[Tuple[str, str]] = []
        use_and = False
        limit: Optional[int] = None
        withvalues = False
        nocase = False

        i = 0
        while i < len(args):
            a = args[i]
            if casematch(a, b"exact") or casematch(a, b"match") or casematch(a, b"glob") or casematch(a, b"re"):
                if i + 1 >= len(args):
                    raise SimpleError(msgs.SYNTAX_ERROR_MSG)
                kind = a.lower().decode()
                predicates.append((kind, args[i + 1].decode(errors="replace")))
                i += 2
            elif casematch(a, b"and"):
                use_and = True
                i += 1
            elif casematch(a, b"or"):
                use_and = False
                i += 1
            elif casematch(a, b"limit"):
                if i + 1 >= len(args):
                    raise SimpleError(msgs.SYNTAX_ERROR_MSG)
                try:
                    limit = int(args[i + 1])
                except ValueError:
                    raise SimpleError(msgs.INVALID_INT_MSG)
                i += 2
            elif casematch(a, b"withvalues"):
                withvalues = True
                i += 1
            elif casematch(a, b"nocase"):
                nocase = True
                i += 1
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)

        if not predicates:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)

        matches = arr.grep_range(start, end, predicates, use_and, limit, nocase)
        result: List[Any] = []
        for idx, val in matches:
            if withvalues:
                result.append([idx, val])
            else:
                result.append(idx)
        return result

    @command((Key(Array, None), bytes, bytes, bytes), (bytes,))
    def arop(self, key: CommandItem, start_b: bytes, end_b: bytes, op_b: bytes, *args: bytes) -> Any:
        if not key:
            return None
        arr: Array = key.value
        try:
            start = int(start_b)
            end = int(end_b)
        except ValueError:
            raise SimpleError(msgs.INVALID_INT_MSG)

        op = op_b.lower().decode()
        operand: Optional[bytes] = None
        if op == "match":
            if not args:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            operand = args[0]
        elif op not in ("sum", "min", "max", "and", "or", "xor", "used"):
            raise SimpleError(_UNKNOWN_OP)

        return arr.op_range(start, end, op, operand)

    @command((Key(Array),), (bytes,))
    def arinfo(self, key: CommandItem, *args: bytes) -> Any:
        if not key:
            raise SimpleError("no such key")
        arr: Array = key.value
        full = any(casematch(a, b"full") for a in args)
        info: List[Any] = [
            b"count",
            arr.count(),
            b"len",
            arr.length(),
            b"next-insert-index",
            arr._cursor,
            b"slices",
            1,
            b"directory-size",
            1,
            b"super-dir-entries",
            0,
            b"slice-size",
            4096,
        ]
        if full:
            info += [
                b"dense-slices",
                0,
                b"sparse-slices",
                1,
                b"avg-dense-size",
                0.0,
                b"avg-dense-fill",
                0.0,
                b"avg-sparse-size",
                float(arr.count() * 4),
            ]
        return info
