# CLAUDE.md

Guidance for Claude Code when working in this repository.

fakeredis provides drop-in replacements for `redis.Redis` / `redis.asyncio.Redis` (and `valkey.Valkey`) that operate entirely in-memory, without a real Redis server.

## Commands

```bash
# Install all dependencies including optional extras
uv sync --all-extras

# Run tests (fake redis only)
uv run pytest -v -m "fake"

# Run a single test file
uv run pytest -v test/test_mixins/test_string_mixin.py

# Lint, format, type check
uv run ruff check --fix fakeredis/
uv run ruff format fakeredis/
uv run mypy fakeredis/

# Regenerate commands.json metadata (after adding/changing commands)
uv run python scripts/generate_command_info.py
```

## Testing

A real server on `localhost:6390` is required for **all** test runs (even `fake`-only): the session-scoped `real_server_details` fixture connects on startup and calls `pytest.exit()` if it can't reach one. Start one with any service from `docker-compose.yml`, e.g. `docker compose up -d redis8`.

**Markers** (combine with `-m`): `fake`, `real`, `slow`, `disconnected`, `tcp_server`, `resp2_only`, `resp3_only`, `load_lua_modules`, plus per-test markers below.

- Limit by server version: `@pytest.mark.supported_server_versions(min_redis_ver="7")` — kwargs: `min_redis_ver`, `max_redis_ver`, `min_valkey_ver`, `max_valkey_ver`
- Skip on a server type: `@pytest.mark.unsupported_server_types("valkey")`
- Limit by redis-py version: `@testtools.run_test_if_redispy_ver("gte", "4.2.0")`

When the server on port 6390 is a Valkey server, the conftest auto-selects `FakeValkey`/`valkey.StrictValkey` instead of the Redis client classes — no marker needed.

## Architecture

### Core Data Flow

```
Client (redis-py/valkey-py)
  → FakeConnection._connect() → FakeSocket
  → send_command() → command dispatch → Mixin method
  → Database read/write (with RwLock)
  → response queued in FakeSocket
  → read_response() → Client
```

### Key Modules

- **`_connection.py`** — `FakeConnection` (sync) and `FakeRedisMixin`; entry points `FakeRedis`, `FakeStrictRedis`
- **`aioredis.py`** — `AsyncFakeSocket`, `FakeAsyncConnection`, `FakeAsyncRedis` (async path using `asyncio.Queue`)
- **`_valkey.py`** — `FakeValkey` / `FakeAsyncValkey` entry points for the valkey-py client
- **`_server.py`** — `FakeServer`: holds all databases, script cache, pub/sub state, ACL; share one instance across connections to share state
- **`_commands.py`** — `SUPPORTED_COMMANDS` registry, `Signature`, `Key`, `CommandItem` classes
- **`_helpers.py`** — `Database` (in-memory dict with expiration), `SimpleString`, `SimpleError`
- **`_basefakesocket.py`** — base class for `FakeSocket`; core dispatch loop and response encoding
- **`commands_mixins/`** — one file per Redis data type/feature area; all mixed into `FakeSocket`
- **`stack/`** — optional Redis Stack modules (JSON, TimeSeries, Bloom/Cuckoo filters, TopK, T-Digest, VectorSet); activated when optional deps are present (extras: `json`, `bf`, `probabilistic`, `vectorset`; `lua` enables `EVAL`/`EVALSHA`)
- **`model/`** — data structure implementations (`ZSet`, `Hash`, `Stream`, `TimeSeries`, etc.)
- **`server_specific_commands/`** — server-specific extensions (e.g. DragonflyDB commands)
- **`_tcp_server.py`** — `FakeTcpServer`: exposes a `FakeServer` over a real TCP socket (used by `tcp_server` test marker)

### Command Implementation Pattern

Commands are methods on mixins in `commands_mixins/` (or `stack/`). The `@command` decorator registers them in `SUPPORTED_COMMANDS`:

```python
@command((Key(bytes), bytes))   # signature: key argument, then bytes value
def append(self, key: CommandItem, value: bytes) -> int:
    old = key.get(b"")
    if len(old) + len(value) > MAX_STRING_SIZE:
        raise SimpleError(msgs.STRING_OVERFLOW_MSG)
    key.update(old + value)
    return len(key.value)
```

- `Key(type_)` in the signature causes that argument to be auto-fetched from the database as a `CommandItem`
- `CommandItem.update()` marks the item dirty so it's written back
- Raise `SimpleError` (not Python exceptions) to return Redis error responses; message constants live in `_msgs.py`
- Use `name=` on `@command` for subcommands (`SCRIPT LOAD`), module commands (`JSON.GET`), or Python reserved words (`exec`)
- Use `extract_args(actual_args, expected)` from `_command_args_parsing.py` for optional/variadic args:
  - bare name → boolean flag; `+name` → one int; `++name` → two ints; `*name` → string; `.name` → float

### Adding a New Command

1. Implement the method with `@command(...)` in the appropriate mixin file in `commands_mixins/` (or `stack/` for module commands)
2. Write tests in the corresponding `test/test_mixins/` file — pytest injects a redis connection as `r`
3. Run `uv run python scripts/generate_command_info.py` to update `commands.json`
4. Run `uv run python scripts/generate_supported_commands_doc.py` to update `docs/` and include those changes in the PR
