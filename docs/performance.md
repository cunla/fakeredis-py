# Performance

How fast is fakeredis next to a real Redis server, and next to
[burner-redis](https://github.com/PrefectHQ/burner-redis), another in-process Redis replacement for Python?
This page shows the same operations timed on all three.

!!! note

    These are micro-benchmarks from one machine. Read them for the proportions rather than the absolute values, and
    [run them yourself](#running-the-benchmark) if a decision depends on them.

## In short

- **Simple commands** such as `GET`, `SET` or `HSET` take 21–37 µs with fakeredis, against 36–42 µs for a round trip
  to a Redis server on the same machine. burner-redis answers them in about 1 µs.
- **Pipelines:** a real server is faster than fakeredis here, at about 12 µs per command against 20 µs.
- **Replies with many elements** depend on how redis-py parses them. With redis-py's default parser, fakeredis is
  3–24 times faster than a real server on most 100,000-element replies, because it hands redis-py Python objects and
  skips the parsing. With [hiredis](https://github.com/redis/hiredis-py) installed it is the other way round for most
  of them: the real server is 2–3 times as fast as fakeredis (`HGETALL` is level), and somewhat faster on a small
  stream read such as a 10-entry `XRANGE`.
- **Lua scripts** are slower in fakeredis than on a real server with either parser.
- **Creating a client** and running its first command costs about 0.26 ms with fakeredis and 1.1–1.3 ms with a real
  server.
- **burner-redis is the fastest of the three by a wide margin** wherever it implements the command: 20–40 times
  faster than fakeredis on simple commands, and by a smaller, more varied factor on large replies. It is written in
  Rust and is called directly, without a client library in between. Lua scripts are the exception: there it is close
  to fakeredis.

## What is compared

| | What it is | How a command reaches it |
|---|---|---|
| **Redis** | Redis 8.10.2 in a container on the host network, reached over loopback TCP | redis-py encodes the command, the server answers over a socket, redis-py parses the reply |
| **Redis + hiredis** | The same server, with the `hiredis` package installed | As above, with the reply parsed in C |
| **fakeredis** | `FakeAsyncRedis`, 2.40.0 in development: `master` at `4ad978b5` with [#614](https://github.com/cunla/fakeredis-py/pull/614) and [#615](https://github.com/cunla/fakeredis-py/pull/615) applied | redis-py encodes the command, fakeredis parses and runs it in Python and returns Python objects |
| **fakeredis (sync)** | `FakeRedis`, the same code behind redis-py's sync client | As above, without the event loop |
| **burner-redis** | `BurnerRedis` 0.1.7, a Rust extension | A direct method call; redis-py is not involved |

burner-redis only has an asyncio API, so the asyncio clients are the like-for-like comparison, and the sync fakeredis
client is listed next to them because it is what most test suites use.

Speed is one of several differences between them. fakeredis runs on redis-py and valkey-py themselves, sync and
asyncio, so application code sees the client it uses in production, and it follows the behaviour of specific Redis,
Valkey and Dragonfly versions across the commands listed under [supported commands](supported-commands/index.md).
burner-redis describes itself as experimental and implements the subset of `redis.asyncio.Redis` that its authors'
projects need; commands outside it raise `NotImplementedError` (`INCR` below is one).

## Method

- Machine: 8-core arm64 Linux VM, CPython 3.14.6, redis-py 8.1.0. Measured on 2026-10-08.
- Each operation is awaited back to back on one connection, with no concurrency. The figure is the best of five
  rounds, each long enough to run for about 0.15 s (three calls per round for the whole-collection reads).
- Keys and values are short strings. The "large" collections hold 100,000 elements each.
- The rows that read from the large collections were checked to return the same amount of data from all three.

## Single commands

Time per call, in microseconds.

| µs per call | Redis | Redis + hiredis | fakeredis | fakeredis (sync) | burner-redis |
|---|---:|---:|---:|---:|---:|
| `SET` | 40.2 | 40.5 | 32.0 | 27.9 | 1.16 |
| `SET ... EX` | 42.2 | 42.8 | 37.4 | 33.0 | 1.25 |
| `GET` | 37.6 | 36.1 | 25.1 | 21.5 | 0.73 |
| `MGET` (10 keys) | 70.6 | 44.8 | 47.7 | 43.3 | 2.41 |
| `EXISTS` | 37.3 | 37.2 | 25.4 | 21.7 | 0.78 |
| `EXPIRE` | 38.2 | 38.0 | 30.4 | 26.0 | 0.76 |
| `TTL` | 36.1 | 35.7 | 24.7 | 21.0 | 0.74 |
| `SET` + `DEL` | 76.7 | 77.3 | 59.0 | 51.0 | 2.03 |
| `INCR` | 37.2 | 36.5 | 28.5 | 24.5 | n/a |
| `HSET` | 38.2 | 37.9 | 30.7 | 27.1 | 0.84 |
| `HGET` | 38.1 | 37.1 | 26.8 | 23.2 | 0.79 |
| `HGETALL` (10 fields) | 87.4 | 39.9 | 29.3 | 25.8 | 1.70 |
| `HINCRBY` | 37.6 | 37.2 | 31.1 | 27.2 | 0.83 |
| `SADD` | 37.1 | 37.2 | 27.7 | 24.0 | 0.80 |
| `SISMEMBER` | 37.2 | 37.2 | 26.7 | 23.1 | 0.72 |
| `SMEMBERS` (10 members) | 64.1 | 38.8 | 28.4 | 24.2 | 1.88 |
| `RPUSH` + `LPOP` | 74.2 | 74.1 | 54.3 | 46.8 | 2.21 |
| `LRANGE` (10 items) | 63.9 | 39.0 | 30.1 | 26.5 | 1.27 |
| `ZADD` | 38.2 | 38.0 | 30.7 | 26.9 | 0.85 |
| `ZSCORE` | 37.8 | 37.0 | 26.6 | 23.1 | 0.75 |
| `ZRANGE` (10 members, with scores) | 104 | 47.7 | 51.0 | 47.0 | 1.82 |
| `XADD` (`MAXLEN 1000`) | 41.6 | 40.4 | 43.4 | 39.0 | 1.36 |
| `XRANGE` (10 entries) | 155 | 47.4 | 57.1 | 53.1 | 3.75 |
| `XREAD` (10 entries) | 161 | 51.2 | 53.4 | 50.0 | 4.59 |
| `XADD` + `XREADGROUP` + `XACK` | 142 | 127 | 113 | 101 | 4.53 |
| `PUBLISH` (no subscribers) | 37.3 | 37.7 | 26.1 | 22.3 | 0.69 |
| `EVAL` (one `redis.call`) | 39.2 | 38.2 | 59.6 | 54.3 | 50.2 |

For a simple command, more than half of fakeredis' time is spent in redis-py's own client code, which burner-redis
does not go through.

## Pipelines

Time per command, in microseconds, for `SET`s sent in one pipeline.

| µs per command | Redis | Redis + hiredis | fakeredis | fakeredis (sync) | burner-redis |
|---|---:|---:|---:|---:|---:|
| 10 `SET`s in one pipeline | 17.0 | 15.7 | 22.5 | 19.7 | 1.24 |
| 100 `SET`s in one pipeline | 12.8 | 11.4 | 20.6 | 19.1 | 0.97 |
| 1,000 `SET`s in one pipeline | 11.8 | 10.3 | 20.6 | 19.3 | 0.97 |

A pipeline removes the per-command round trip, which is where a real server loses most of its time. What is left for
fakeredis is parsing and running each command in Python.

## Whole-collection reads

Time per call, in milliseconds, for a reply of 100,000 elements (10,000 for `MGET`).

| ms per call | Redis | Redis + hiredis | fakeredis | fakeredis (sync) | burner-redis |
|---|---:|---:|---:|---:|---:|
| `LRANGE 0 -1` | 251 | 5.37 | 10.3 | 11.0 | 3.34 |
| `SMEMBERS` | 267 | 13.2 | 25.1 | 29.2 | 25.1 |
| `HGETALL` | 522 | 34.6 | 38.8 | 41.2 | 22.0 |
| `ZRANGE 0 -1 WITHSCORES` | 648 | 74.5 | 211 | 216 | 13.1 |
| `XRANGE - +` | 1,219 | 112 | 378 | 382 | 36.7 |
| `KEYS big:key:*` | 264 | 10.4 | 27.1 | 27.7 | 14.0 |
| `MGET` (10,000 keys) | 34.0 | 9.47 | 29.3 | 28.8 | 2.34 |
| `scan_iter(count=1000)`, whole keyspace | 285 | 32.2 | 77.8 | 70.1 | 32.3 |

Without hiredis, a real server's time here is almost entirely redis-py parsing the reply in Python.

## Small reads from large collections

Time per call, in microseconds, on the same 100,000-element collections. None of the three slows down with the size
of the collection for these.

| µs per call | Redis | Redis + hiredis | fakeredis | fakeredis (sync) | burner-redis |
|---|---:|---:|---:|---:|---:|
| `GET` | 38.2 | 36.1 | 25.4 | 21.8 | 0.81 |
| `HGET` | 38.9 | 37.1 | 27.2 | 23.6 | 0.89 |
| `SISMEMBER` | 37.6 | 37.2 | 27.1 | 23.5 | 0.85 |
| `ZSCORE` | 38.1 | 37.0 | 26.9 | 23.4 | 0.86 |
| `LRANGE 0 9` | 64.8 | 38.0 | 30.4 | 26.7 | 1.23 |
| `ZRANGE 0 9` | 67.2 | 40.0 | 36.4 | 32.2 | 1.44 |
| `ZRANGEBYSCORE` (10 members from the middle) | 67.3 | 40.0 | 36.8 | 32.6 | 1.66 |
| `XRANGE - + COUNT 10` | 155 | 46.6 | 57.4 | 52.8 | 3.40 |
| `XREAD COUNT 10` (from the middle) | 167 | 54.1 | 54.5 | 50.5 | 4.20 |

## New client

Time, in microseconds, to create a client, run one `GET` and close it. This matters for test suites that build a
client per test. For fakeredis and burner-redis the client is new but the data store is reused or empty; for Redis it
includes opening the TCP connection.

| µs per call | Redis | Redis + hiredis | fakeredis | fakeredis (sync) | burner-redis |
|---|---:|---:|---:|---:|---:|
| Create a client, run one `GET`, close it | 1,251 | 1,095 | 264 | 252 | 19.7 |

## Running the benchmark

The tables are printed by [`scripts/benchmark.py`](https://github.com/cunla/fakeredis-py/blob/master/scripts/benchmark.py).
It needs a real server to compare with, and flushes the database the URL points at.

```bash
docker run -d --network host redis:8.10 redis-server --port 6398 --save "" --appendonly no

# redis-py's default parser
uv run --with burner-redis python scripts/benchmark.py --redis-url redis://localhost:6398/15

# with hiredis
uv run --with burner-redis --with hiredis python scripts/benchmark.py --redis-url redis://localhost:6398/15
```

The server runs on the host network because a published container port adds a proxy hop: about 11 µs per command
on the machine used here.
