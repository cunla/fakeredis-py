# CLAUDE.md — tests

Guidance for Claude Code when working on the fakeredis test suite.

## Running tests

```bash
# Run tests (fake redis only)
uv run pytest -v -m "fake"

# Run a single test file
uv run pytest -v test/test_mixins/test_string_commands.py
```

A real server on `localhost:6390` is required for **all** test runs (even `fake`-only): the session-scoped
`real_server_details` fixture connects on startup and calls `pytest.exit()` if it can't reach one. Start one with any
service from `docker-compose.yml`, e.g. `docker compose up -d redis8`. Every service maps to port 6390, so run one at a
time.

The fake server is built to match the real one: `fake_server` takes the real server's type and version, so the same test
runs against a fake Redis 6.2, Valkey 9 or Dragonfly depending on what is on port 6390.

When the server on port 6390 is a Valkey server, the conftest auto-selects `FakeValkey`/`valkey.StrictValkey` instead of
the Redis client classes — no marker needed.

The `valkey/valkey` images have no JSON, Bloom, TimeSeries or other Stack modules. With the extras installed locally,
the real-server variants in `test/test_stack/` fail with `unknown command 'JSON.SET'` and the like. CI never hits this
because its Valkey jobs run without extras, so `pytest.importorskip` skips those files. Against Valkey, run Stack tests
with `-m fake`, or switch to `redis8`.

## Fixtures (`test/conftest.py`)

- `r` — a sync client, flushed before and after the test. Parametrized over `Strict2`, `FakeStrict2`, `Strict3` and
  `FakeStrict3`: real/fake × RESP2/RESP3. Write each test so it passes against both the real server and fakeredis.
- `async_redis` — the async equivalent, parametrized over fake/real × RESP2/RESP3.
- `create_connection` — the factory behind `r`; call `create_connection(db=..., **kwargs)` for extra clients on the same
  server.
- `real_server_details` — a `ServerDetails` with `server_type` (`redis`, `valkey`, `dragonfly`, `kividb`) and versions;
  use it when the expected reply differs by server.
- `fake_server`, `tcp_server_address` — the shared `FakeServer`, and a `TcpFakeServer` serving it over TCP.

## Markers

Combine with `-m`: `fake`, `real`, `slow`, `disconnected`, `tcp_server`, `resp2_only`, `resp3_only`, `load_lua_modules`,
plus the per-test markers below.

- Limit by server version: `@pytest.mark.supported_server_versions(min_redis_ver="7")` — kwargs: `min_redis_ver`,
  `max_redis_ver`, `min_valkey_ver`, `max_valkey_ver`
- Skip on a server type: `@pytest.mark.unsupported_server_types("valkey")`
- Run only the fake variants of a test: `@pytest.mark.fake_only`
- Decode replies to `str`: `@pytest.mark.decode_responses`
- Limit by redis-py version: `@testtools.run_test_if_redispy_ver("gte", "4.2.0")`

## Helpers (`test/testtools.py`)

- `raw_command(r, *args)` — sends a command without redis-py's response parsing. Use it for new commands and new
  arguments: redis-py validates some arguments client-side (e.g. `AGGREGATE COUNT` needs redis-py 8.0, hash field expiry
  helpers need 5.0), so a helper call can fail or be skipped on older redis-py even though fakeredis is correct. Replies
  come back unparsed and differ between RESP2 and RESP3, so normalize both.
- `RESPONSE_ERRORS`, `CONNECTION_ERRORS` — the error classes for redis-py and, when it is installed, valkey-py. Use
  `pytest.raises(RESPONSE_ERRORS, match=...)` rather than `redis.ResponseError`, which a Valkey client never raises.
  valkey-py is an optional extra, so import these instead of importing `valkey` in a test file.
- `resp_conversion(r, val_resp3, val_resp2)` — picks the expected value for the client's protocol.
- `run_test_if_redispy_ver`, `run_test_if_lupa` — skip markers for the redis-py version and for `lupa`.
- Server-specific expectations: `far_future_expiry`, `null_array_reply`, `empty_blocking_reply` and the `json_*_reply`
  helpers.

## Layout

- `test_mixins/` — one file per command mixin; new command tests go in the matching file.
  `test_specific_redis_versions/` holds tests for commands added in a given Redis release (`test_redis_8_8_increx.py`).
- `test_stack/` — Redis Stack modules (JSON, Bloom, Cuckoo, CMS, TopK, T-Digest, TimeSeries, VectorSet); skipped unless
  the extras are installed.
- `test_async/` — the async client.
- `test_dragonfly/`, `test_kividb/`, `test_valkey/` — server-specific behavior.
- `test_tcp_server/` — `TcpFakeServer` (`tcp_server` marker).
- `test_internals/` — fakeredis internals (argument parsing, expiry tracking, ACL, connection setup).
- `test_hypothesis/` — stateful differential tests that run random command sequences against fake and real servers and
  compare. Set `FAKEREDIS_HYPOTHESIS_EXAMPLES` to change the example count (default 250).

## Known flakes

`test_mixins/test_streams_commands.py::test_xadd_redis__green` can fail on `-m real` with `assert <ts> <= <ts - 1>`. The
Docker server's clock can sit about 1 ms behind the host's. It fails on a clean tree too, so it isn't a regression.
