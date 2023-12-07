from abc import ABC, abstractmethod
import os
import re
import threading
import time
import weakref
from collections import defaultdict
from collections.abc import MutableMapping
from typing import Any, Set, Callable, Dict, Optional, Iterator
import json


class SimpleString:
    def __init__(self, value: bytes) -> None:
        assert isinstance(value, bytes)
        self.value = value

    @classmethod
    def decode(cls, value: bytes) -> bytes:
        return value


class SimpleError(Exception):
    """Exception that will be turned into a frontend-specific exception."""

    def __init__(self, value: str) -> None:
        assert isinstance(value, str)
        self.value = value


class NoResponse:
    """Returned by pub/sub commands to indicate that no response should be returned"""

    pass


OK = SimpleString(b"OK")
QUEUED = SimpleString(b"QUEUED")
BGSAVE_STARTED = SimpleString(b"Background saving started")


def current_time() -> int:
    return int(time.time() * 1000)


def null_terminate(s: bytes) -> bytes:
    # Redis uses C functions on some strings, which means they stop at the
    # first NULL.
    ind = s.find(b"\0")
    if ind > -1:
        return s[:ind].lower()
    return s.lower()


def casematch(a: bytes, b: bytes) -> bool:
    return null_terminate(a) == null_terminate(b)


def encode_command(s: bytes) -> str:
    return s.decode(encoding="utf-8", errors="replace").lower()


def compile_pattern(pattern_bytes: bytes) -> re.Pattern:  # type: ignore
    """Compile a glob pattern (e.g., for keys) to a `bytes` regex.

    `fnmatch.fnmatchcase` doesn't work for this because it uses different
    escaping rules to redis, uses ! instead of ^ to negate a character set,
    and handles invalid cases (such as a [ without a ]) differently. This
    implementation was written by studying the redis implementation.
    """
    # It's easier to work with text than bytes, because indexing bytes
    # doesn't behave the same in Python 3. Latin-1 will round-trip safely.
    pattern: str = pattern_bytes.decode(
        "latin-1",
    )
    parts = ["^"]
    i = 0
    pattern_len = len(pattern)
    while i < pattern_len:
        c = pattern[i]
        i += 1
        if c == "?":
            parts.append(".")
        elif c == "*":
            parts.append(".*")
        elif c == "\\":
            if i == pattern_len:
                i -= 1
            parts.append(re.escape(pattern[i]))
            i += 1
        elif c == "[":
            parts.append("[")
            if i < pattern_len and pattern[i] == "^":
                i += 1
                parts.append("^")
            parts_len = len(parts)  # To detect if anything was added
            while i < pattern_len:
                if pattern[i] == "\\" and i + 1 < pattern_len:
                    i += 1
                    parts.append(re.escape(pattern[i]))
                elif pattern[i] == "]":
                    i += 1
                    break
                elif i + 2 < pattern_len and pattern[i + 1] == "-":
                    start = pattern[i]
                    end = pattern[i + 2]
                    if start > end:
                        start, end = end, start
                    parts.append(re.escape(start) + "-" + re.escape(end))
                    i += 2
                else:
                    parts.append(re.escape(pattern[i]))
                i += 1
            if len(parts) == parts_len:
                if parts[-1] == "[":
                    # Empty group - will never match
                    parts[-1] = "(?:$.)"
                else:
                    # Negated empty group - matches any character
                    assert parts[-1] == "^"
                    parts.pop()
                    parts[-1] = "."
            else:
                parts.append("]")
        else:
            parts.append(re.escape(c))
    parts.append("\\Z")
    regex: bytes = "".join(parts).encode("latin-1")
    return re.compile(regex, flags=re.S)


class Database(MutableMapping):  # type: ignore
    def __init__(self, lock: Optional[threading.Lock], *args: Any, **kwargs: Any) -> None:
        self._dict: Dict[bytes, Any] = dict(*args, **kwargs)
        self.time = 0.0
        # key to the set of connections
        self._watches: Dict[bytes, weakref.WeakSet[Any]] = defaultdict(weakref.WeakSet)
        self.condition = threading.Condition(lock)
        self._change_callbacks: Set[Callable[[], None]] = set()

    def swap(self, other: "Database") -> None:
        self._dict, other._dict = other._dict, self._dict
        self.time, other.time = other.time, self.time

    def notify_watch(self, key: bytes) -> None:
        for sock in self._watches.get(key, set()):
            sock.notify_watch()
        self.condition.notify_all()
        for callback in self._change_callbacks:
            callback()

    def add_watch(self, key: bytes, sock: Any) -> None:
        self._watches[key].add(sock)

    def remove_watch(self, key: bytes, sock: Any) -> None:
        watches = self._watches[key]
        watches.discard(sock)
        if not watches:
            del self._watches[key]

    def add_change_callback(self, callback: Callable[[], None]) -> None:
        self._change_callbacks.add(callback)

    def remove_change_callback(self, callback: Callable[[], None]) -> None:
        self._change_callbacks.remove(callback)

    def clear(self) -> None:
        for key in self:
            self.notify_watch(key)
        self._dict.clear()

    def expired(self, item: Any) -> bool:
        return item.expireat is not None and item.expireat < self.time

    def _remove_expired(self) -> None:
        for key in list(self._dict):
            item = self._dict[key]
            if self.expired(item):
                del self._dict[key]

    def __getitem__(self, key: bytes) -> Any:
        item = self._dict[key]
        if self.expired(item):
            del self._dict[key]
            raise KeyError(key)
        return item

    def __setitem__(self, key: bytes, value: Any) -> None:
        self._dict[key] = value

    def __delitem__(self, key: bytes) -> None:
        del self._dict[key]

    def __iter__(self) -> Iterator[bytes]:
        self._remove_expired()
        return iter(self._dict)

    def __len__(self) -> int:
        self._remove_expired()
        return len(self._dict)

    def __hash__(self) -> int:
        return hash(super(object, self))

    def __eq__(self, other: object) -> bool:
        return super(object, self) == other


class PersistentDatabase(Database):
    def __init__(
        self,
        lock: Optional[threading.Lock],
        filename: str = "redis.json",
        initial_values: Optional[dict] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(lock, *args, **kwargs)
        self.filename = filename
        self._load(initial_values)

    def _load(self, default_values: Optional[dict] = None) -> None:
        try:
            with open(self.filename, 'r') as file:
                file_content = file.read()
                self._dict = json.loads(file_content) if file_content else {}
        except (FileNotFoundError, json.JSONDecodeError):
            self._dict = default_values if isinstance(default_values, dict) else {}
            self._save()

    def _save(self) -> None:
        with open(self.filename, 'w') as file:
            json.dump(self._dict, file)

    def __getitem__(self, key: bytes) -> Any:
        self._load()
        return super().__getitem__(key)

    def clear(self) -> None:
        super().clear()
        self._save()

    def __eq__(self, other: object) -> bool:
        if isinstance(other, PersistentDatabase):
            self._load()
            other._load()
            return self._dict == other._dict
        return False

    def __iter__(self) -> Iterator[bytes]:
        # Load from persistent storage before iteration
        self._load()
        # Iterator of the current state of the dictionary
        return super().__iter__()

    def __len__(self) -> int:
        # Load from persistent storage to get the current length
        self._load()
        # Length of the current state of the dictionary
        return super().__len__()

    def _reload_state(self, default_values: Optional[dict] = None):
        """
        Reload the state from the file before any write operation.
        """
        try:
            with open(self.filename, 'r') as file:
                file_content = file.read()
                self._dict = json.loads(file_content) if file_content else {}
        except (FileNotFoundError, json.JSONDecodeError):
            self._dict = default_values if isinstance(default_values, dict) else {}
            self._save()

    def __setitem__(self, key: bytes, value: Any) -> None:
        self._reload_state()
        super().__setitem__(key, value)
        self._save()

    def __delitem__(self, key: bytes) -> None:
        self._reload_state()
        super().__delitem__(key)
        self._save()

    def swap(self, other: "PersistentDatabase") -> None:
        self._reload_state()
        other._reload_state()
        super().swap(other)
        self._save()
        other._save()


class Lock(ABC):
    @abstractmethod
    def __enter__(self):
        raise NotImplementedError

    @abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        raise NotImplementedError


class FileLock(Lock):
    def __init__(self, filepath, timeout=1):
        self.lock_file_path = filepath + ".lock"
        self.timeout = timeout

    def __enter__(self):
        start_time = time.time()
        while os.path.exists(self.lock_file_path):
            time.sleep(0.1)
            if time.time() - start_time > self.timeout:
                raise TimeoutError("Lock acquisition timed out")
        with open(self.lock_file_path, 'w') as lock_file:
            lock_file.write('locked')
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if os.path.exists(self.lock_file_path):
            os.remove(self.lock_file_path)


class DBLock(Lock):
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        self.conn.autocommit = False
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            # If an exception occurred, roll back the transaction
            self.conn.rollback()
        else:
            # Otherwise, commit the transaction
            self.conn.commit()
        self.conn.autocommit = True


class PersistentWithLockingDatabase(PersistentDatabase):
    def __init__(
        self,
        lock: Optional[threading.Lock | Lock],
        filename: str = "redis.json",
        initial_values: Optional[dict] = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(filename, initial_values, *args, **kwargs)
        self.lock = lock

    def _load(self, default_values: Optional[dict] = None) -> None:
        with self.lock:
            if not os.path.exists(self.filename):
                with open(self.filename, 'w') as file:
                    json.dump({"_version": 0}, file)
            super()._load(default_values)

    def _save(self) -> None:
        with self.lock:
            current_data = {}
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as file:
                    current_data = json.load(file)
            current_data["_version"] = current_data.get("_version", 0) + 1
            current_data.update(self._dict)
            with open(self.filename, 'w') as file:
                json.dump(current_data, file)

    def __delitem__(self, key: bytes) -> None:
        with self.lock:
            super().__delitem__(key)

    def swap(self, other: "PersistentWithLockingDatabase") -> None:
        with self.lock:
            with other.lock:
                # Locking for the current database
                super().swap(other)

    def __iter__(self) -> Iterator[bytes]:
        with self.lock:
            # Acquire file lock before iteration
            return super().__iter__()

    def __len__(self) -> int:
        with self.lock:
            # Acquire file lock before calculating length
            return super().__len__()

    def __setitem__(self, key: bytes, value: Any) -> None:
        with self.lock:
            super().__setitem__(key, value)

    def clear(self) -> None:
        with self.lock:
            super().clear()


class PersistentWithLockingWithPostgresDatabase(PersistentWithLockingDatabase):
    def __init__(self, conn, table_name: str = "kv_store", id: int = 1, *args, **kwargs):
        self.conn = conn
        self.table_name = table_name
        self.row_id = id
        db_lock = DBLock(conn)  # Initialize DBLock with the connection
        super().__init__(db_lock, *args, **kwargs)
        self._ensure_table_exists()

    def _ensure_table_exists(self):
        with super().lock:
            with self.conn.cursor() as cursor:
                # Create the table if it does not exist
                cursor.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id SERIAL PRIMARY KEY,
                        data JSONB NOT NULL
                    );
                """
                )

                # Insert a row with id = 1 if it does not exist
                cursor.execute(
                    f"""
                                    INSERT INTO {self.table_name} (id, data)
                                    VALUES (%s, '{{}}'::jsonb)
                                    ON CONFLICT (id) DO NOTHING;
                                """,
                    (self.row_id,),
                )

    # Overriding methods to use PostgreSQL transactions
    def _load(self, default_values: Optional[dict] = None) -> None:
        with super().lock:
            with self.conn.cursor() as cursor:
                cursor.execute(f"SELECT data FROM {self.table_name} WHERE id = 1;")
                row = cursor.fetchone()
                if row:
                    self._dict = row[0]
                else:
                    self._dict = default_values if isinstance(default_values, dict) else {}
                    self._save()

    def _save(self) -> None:
        with super().lock:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    UPDATE {self.table_name} SET data = %s WHERE id = %s;
                """,
                    (json.dumps(self._dict), self.row_id),
                )

                # Check if the update was successful
                if cursor.rowcount == 0:
                    # No rows were updated, so insert a new row
                    cursor.execute(
                        f"""
                        INSERT INTO {self.table_name} (id, data) VALUES (%s, %s);
                    """,
                        (self.row_id, json.dumps(self._dict)),
                    )

    # Override other methods similarly...

    def close(self):
        self.conn.close()


def valid_response_type(value: Any, nested: bool = False) -> bool:
    if isinstance(value, NoResponse) and not nested:
        return True
    if value is not None and not isinstance(
            value, (bytes, SimpleString, SimpleError, float, int, list)
    ):
        return False
    if isinstance(value, list):
        if any(not valid_response_type(item, True) for item in value):
            return False
    return True


class FakeSelector(object):
    def __init__(self, sock: Any):
        self.sock = sock

    def check_can_read(self, timeout: Optional[int]) -> bool:
        if self.sock.responses.qsize():
            return True
        if timeout is not None and timeout <= 0:
            return False

        # A sleep/poll loop is easier to mock out than messing with condition
        # variables.
        start = time.time()
        while True:
            if self.sock.responses.qsize():
                return True
            time.sleep(0.01)
            now = time.time()
            if timeout is not None and now > start + timeout:
                return False

    @staticmethod
    def check_is_ready_for_command(_: Any) -> bool:
        return True
