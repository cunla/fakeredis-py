<div align="center">

# 🟥 fakeredis

### A fast, pure-Python implementation of the Redis protocol — no server required.

[![PyPI version](https://img.shields.io/pypi/v/fakeredis)](https://pypi.org/project/fakeredis/)
[![CI](https://github.com/cunla/fakeredis-py/actions/workflows/test.yml/badge.svg)](https://github.com/cunla/fakeredis-py/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/cunla/b756396efb895f0e34558c980f1ca0c7/raw/fakeredis-py.json)](https://github.com/cunla/fakeredis-py/actions/workflows/test.yml)
[![Downloads](https://img.shields.io/pypi/dm/fakeredis)](https://pypi.org/project/fakeredis/)
[![Python versions](https://img.shields.io/pypi/pyversions/fakeredis)](https://pypi.org/project/fakeredis/)
[![License](https://img.shields.io/pypi/l/fakeredis)](./LICENSE)
[![Open Source Helpers](https://www.codetriage.com/cunla/fakeredis-py/badges/users.svg)](https://www.codetriage.com/cunla/fakeredis-py)

[**Documentation**][readthedocs] · [**Supported commands**][readthedocs] · [**Changelog**](./docs/about/changelog.md) · [**Sponsor**](https://github.com/sponsors/cunla)

</div>

---

**fakeredis** is a drop-in replacement for [redis-py][redis-py] and [valkey-py][valkey-py] that runs entirely
in-memory. Write tests that depend on [Redis][redis], [Valkey][valkey], [DragonflyDB][dragonflydb], or
[KeyDB][keydb] — without spinning up a real server, a container, or a network connection.

```python
import fakeredis

r = fakeredis.FakeStrictRedis()
r.set("foo", "bar")
r.get("foo")  # b'bar'
```

That's it. No server to install, no port to manage, no teardown.

## ✨ Why fakeredis?

- 🚀 **Zero setup** — no Redis server, Docker, or network required. Pure Python.
- 🔌 **Drop-in compatible** — same API as `redis.Redis` and `redis.asyncio.Redis`.
- ⚡ **Fast & isolated** — in-memory, so tests run quickly and start from a clean slate.
- 🧩 **Multi-backend** — emulate Redis, Valkey, DragonflyDB, or KeyDB, and pin a specific server version.
- 📦 **Redis Stack support** — JSON, Bloom/Cuckoo filters, TimeSeries, and Geo commands.
- 🤝 **Share or isolate state** — one shared in-memory server across clients, or independent servers per test.

## 📥 Installation

```bash
pip install fakeredis
```

Optional extras enable additional command families:

```bash
pip install "fakeredis[lua]"          # EVAL / EVALSHA scripting
pip install "fakeredis[json]"         # JSON.* commands
pip install "fakeredis[bf]"           # Bloom / Cuckoo / Count-Min / Top-K filters
pip install "fakeredis[probabilistic]"  # alias for the probabilistic filters
pip install "fakeredis[valkey]"       # Valkey client compatibility
```

## 🚀 Quickstart

**Use it like `redis.Redis`:**

```python
import fakeredis

r = fakeredis.FakeStrictRedis()
r.lpush("queue", "a", "b", "c")
r.lrange("queue", 0, -1)  # [b'c', b'b', b'a']
```

**Share one in-memory server between clients:**

```python
server = fakeredis.FakeServer()
r1 = fakeredis.FakeStrictRedis(server=server)
r2 = fakeredis.FakeStrictRedis(server=server)

r1.set("greeting", "hello")
r2.get("greeting")  # b'hello' — same underlying data
```

**Async is supported too:**

```python
import fakeredis

async def main():
    r = fakeredis.FakeAsyncRedis()
    await r.set("foo", "bar")
    await r.get("foo")  # b'bar'
```

**Pin a server type and version:**

```python
# Behave like Redis 6...
r = fakeredis.FakeStrictRedis(version=6)
# ...or like Valkey
r = fakeredis.FakeStrictRedis(server_type="valkey")
```

### Using it in tests (pytest)

```python
import pytest
import fakeredis

@pytest.fixture
def redis_client():
    return fakeredis.FakeStrictRedis()

def test_cache_set(redis_client):
    redis_client.set("user:1", "alice")
    assert redis_client.get("user:1") == b"alice"
```

See the [official documentation][readthedocs] for the full list of supported commands and configuration options.

## ❤️ Sponsor

fakeredis-py is developed and maintained for free. If it saves you time, please consider
[becoming a sponsor](https://github.com/sponsors/cunla) — it directly supports continued development.

## 🤝 Contributing

Contributions are welcome! Check out the [contributing guide](./docs/about/contributing.md) and the
[open issues](https://github.com/cunla/fakeredis-py/issues) to get started.

[readthedocs]: https://fakeredis.readthedocs.io/
[redis-py]: https://github.com/redis/redis-py
[valkey-py]: https://github.com/valkey-io/valkey-py
[redis]: https://redis.io/
[valkey]: https://github.com/valkey-io/valkey
[dragonflydb]: https://dragonflydb.io/
[keydb]: https://docs.keydb.dev/
