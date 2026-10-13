# Comparison with Redis

fakeredis gives Python code a Redis to talk to without a server: the real redis-py or valkey-py client, backed by
an in-memory implementation of the commands. This page puts it next to the alternative it is most often weighed
against: a **real Redis server**, usually in a container.

It covers what each one supports first, and [how fast each one is](#performance) second.

## Which one to use

- **fakeredis** when the code under test uses redis-py or valkey-py and should run unchanged, with no server to
  start. It implements most of the command set, the Redis Stack modules, and the differences between Redis, Valkey
  and Dragonfly versions.
- **A real server** when the test is about Redis itself: persistence, replication, clustering, memory limits, or
  timing under load. Nothing else behaves exactly like it.

## Features

|                                                                      | fakeredis                                                       | Redis server                       |
|----------------------------------------------------------------------|-----------------------------------------------------------------|------------------------------------|
| What it is                                                           | A pure-Python library, in-process                               | A server process                   |
| Needs a server or container                                          | No                                                              | Yes                                |
| Client used by the application                                       | redis-py or valkey-py itself, with a fake connection underneath | Any Redis client                   |
| Sync API                                                             | Yes                                                             | Yes                                |
| asyncio API                                                          | Yes                                                             | Yes                                |
| Reachable from other processes and languages                         | Yes, through [`TcpFakeServer`](index.md)                        | Yes                                |
| Client options (`decode_responses`, `db`, `protocol`, `from_url`, …) | Yes, they are redis-py's                                        | Yes                                |
| Multiple databases (`SELECT`)                                        | Yes                                                             | Yes                                |
| RESP2 and RESP3 reply shapes                                         | Yes                                                             | Yes                                |
| Transactions (`MULTI` / `EXEC` / `WATCH`)                            | Yes                                                             | Yes                                |
| Lua scripting                                                        | Lua 5.1 to 5.4, with the `lua` extra                            | Lua 5.1                            |
| Pub/sub                                                              | Yes, including sharded pub/sub                                  | Yes                                |
| Keyspace notifications                                               | Yes                                                             | Yes                                |
| ACL users                                                            | Yes                                                             | Yes                                |
| JSON, time series, probabilistic and vector set commands             | Yes, with extras                                                | Yes (built into Redis 8)           |
| Emulates other servers                                               | Valkey, Dragonfly and KiviDB, and specific versions of each     | –                                  |
| Persistence                                                          | No, memory only                                                 | RDB and AOF                        |
| Python versions                                                      | 3.8 and later                                                   | Any                                |
| Installation                                                         | A pure-Python wheel                                             | A server binary or container image |
| License                                                              | BSD-3-Clause                                                    | RSALv2, SSPLv1 or AGPLv3           |

## Command coverage

Of the 395 core commands Redis documents (cluster commands aside), fakeredis implements **312**. It also implements
all 93 commands of the JSON, time series and probabilistic modules. The
[supported commands](supported-commands/index.md) pages list them group by group.

For comparison, [burner-redis](https://github.com/PrefectHQ/burner-redis), an in-process Redis-compatible database
written in Rust with Python bindings, implements **74** of the core commands in version 0.1.7, and does not support
JSON commands or any of the other module commands. It describes itself as experimental, so expect that to change.

What that means in practice:

- fakeredis implements every command in most groups, including the JSON, time series and probabilistic modules.
  The scripting commands it lacks are the read-only `EVAL_RO` / `EVALSHA_RO` variants and `SCRIPT DEBUG` / `KILL`;
  `EVAL`, `EVALSHA`, the `SCRIPT` commands, and the `FUNCTION` and `FCALL` family are there. Most of the server
  group it lacks is administration of a real server (replication, cluster, memory, latency and module management).
- burner-redis covers streams and lists well, which is what its authors' task queue needs, and the basics of the
  other types. Everyday commands outside that set are missing: `INCR`, `APPEND`, `MSET`, `RENAME`, `TYPE`, `HKEYS`,
  `HLEN`, `SCARD`, `SINTER`, `ZRANK`, `ZINCRBY`, `PING`, `FLUSHDB` and `DBSIZE`, for example. Calling one fails, and
  so does a Lua script that uses it.
- Search (`FT.*`) is not implemented by either library.

## Client and behaviour

- **Drop-in for redis-py.** A `FakeRedis` *is* a `redis.Redis` (or a `valkey.Valkey`), so everything redis-py does on
  the client side works as it does against a server: argument encoding, response callbacks, `decode_responses`,
  connection pools, `from_url`, locks, pipelines and pub/sub objects.
- **Errors.** fakeredis reproduces Redis' error messages, which redis-py turns into the same exception subclasses a
  server would cause.
- **Server differences.** fakeredis takes a `server_type` and a `version`, and answers the way that server does where
  they differ, so a suite can be run against the behaviour of the server used in production.
- **Checked against real servers.** fakeredis' tests run against a real server as well as against fakeredis, and
  have to pass on both.

## Performance

How fast each one answers, measured with the same operations on both.

!!! note

    These are micro-benchmarks from one machine. Read them for the proportions rather than the absolute values, and
    [run them yourself](#running-the-benchmark) if a decision depends on them.

### In short

- **Simple commands** such as `GET`, `SET` or `HSET` take 21–37 µs with fakeredis, against 36–42 µs for a round trip
  to a Redis server on the same machine.
- **Creating a client** and running its first command costs about 0.26 ms with fakeredis and 1.1–1.3 ms with a real
  server.
- **Replies with many elements** depend on how redis-py parses them. With redis-py's default parser, fakeredis is
  3–24 times faster than a real server on most 100,000-element replies, because it hands redis-py Python objects and
  skips the parsing. With [hiredis](https://github.com/redis/hiredis-py) installed it is the other way round for most
  of them: the real server is 2–3 times as fast as fakeredis (`HGETALL` is level), and somewhat faster on a small
  stream read such as a 10-entry `XRANGE`.
- **Pipelines:** a real server is faster than fakeredis here, at about 12 µs per command against 20 µs.
- **Lua scripts** are slower in fakeredis than on a real server with either parser.

### What is measured

|                      | What it is                                                                                                                                                                                     | How a command reaches it                                                                        |
|----------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| **fakeredis**        | `FakeAsyncRedis`, 2.40.0 in development: `master` at `4ad978b5` with [#614](https://github.com/cunla/fakeredis-py/pull/614) and [#615](https://github.com/cunla/fakeredis-py/pull/615) applied | redis-py encodes the command, fakeredis parses and runs it in Python and returns Python objects |
| **fakeredis (sync)** | `FakeRedis`, the same code behind redis-py's sync client                                                                                                                                       | As above, without the event loop                                                                |
| **Redis**            | Redis 8.10.2 in a container on the host network, reached over loopback TCP                                                                                                                     | redis-py encodes the command, the server answers over a socket, redis-py parses the reply       |
| **Redis + hiredis**  | The same server, with the `hiredis` package installed                                                                                                                                          | As above, with the reply parsed in C                                                            |

The Redis columns use redis-py's asyncio client, so `FakeAsyncRedis` is the like-for-like comparison; the sync
fakeredis client is listed next to it because it is what most test suites use.

### Method

- Machine: 8-core arm64 Linux VM, CPython 3.14.6, redis-py 8.1.0. Measured on 2026-10-08.
- Each operation is awaited back to back on one connection, with no concurrency. The figure is the best of five
  rounds, each long enough to run for about 0.15 s (three calls per round for the whole-collection reads).
- Keys and values are short strings. The "large" collections hold 100,000 elements each.
- The rows that read from the large collections were checked to return the same amount of data from both.

### Single commands

Time per call, in microseconds.

| µs per call                        | fakeredis | fakeredis (sync) | Redis | Redis + hiredis |
|------------------------------------|----------:|-----------------:|------:|----------------:|
| `SET`                              |      32.0 |             27.9 |  40.2 |            40.5 |
| `SET ... EX`                       |      37.4 |             33.0 |  42.2 |            42.8 |
| `GET`                              |      25.1 |             21.5 |  37.6 |            36.1 |
| `MGET` (10 keys)                   |      47.7 |             43.3 |  70.6 |            44.8 |
| `EXISTS`                           |      25.4 |             21.7 |  37.3 |            37.2 |
| `EXPIRE`                           |      30.4 |             26.0 |  38.2 |            38.0 |
| `TTL`                              |      24.7 |             21.0 |  36.1 |            35.7 |
| `SET` + `DEL`                      |      59.0 |             51.0 |  76.7 |            77.3 |
| `INCR`                             |      28.5 |             24.5 |  37.2 |            36.5 |
| `HSET`                             |      30.7 |             27.1 |  38.2 |            37.9 |
| `HGET`                             |      26.8 |             23.2 |  38.1 |            37.1 |
| `HGETALL` (10 fields)              |      29.3 |             25.8 |  87.4 |            39.9 |
| `HINCRBY`                          |      31.1 |             27.2 |  37.6 |            37.2 |
| `SADD`                             |      27.7 |             24.0 |  37.1 |            37.2 |
| `SISMEMBER`                        |      26.7 |             23.1 |  37.2 |            37.2 |
| `SMEMBERS` (10 members)            |      28.4 |             24.2 |  64.1 |            38.8 |
| `RPUSH` + `LPOP`                   |      54.3 |             46.8 |  74.2 |            74.1 |
| `LRANGE` (10 items)                |      30.1 |             26.5 |  63.9 |            39.0 |
| `ZADD`                             |      30.7 |             26.9 |  38.2 |            38.0 |
| `ZSCORE`                           |      26.6 |             23.1 |  37.8 |            37.0 |
| `ZRANGE` (10 members, with scores) |      51.0 |             47.0 |   104 |            47.7 |
| `XADD` (`MAXLEN 1000`)             |      43.4 |             39.0 |  41.6 |            40.4 |
| `XRANGE` (10 entries)              |      57.1 |             53.1 |   155 |            47.4 |
| `XREAD` (10 entries)               |      53.4 |             50.0 |   161 |            51.2 |
| `XADD` + `XREADGROUP` + `XACK`     |       113 |              101 |   142 |             127 |
| `PUBLISH` (no subscribers)         |      26.1 |             22.3 |  37.3 |            37.7 |
| `EVAL` (one `redis.call`)          |      59.6 |             54.3 |  39.2 |            38.2 |

For a simple command, more than half of fakeredis' time is spent in redis-py's own client code.

### Pipelines

Time per command, in microseconds, for `SET`s sent in one pipeline.

| µs per command               | fakeredis | fakeredis (sync) | Redis | Redis + hiredis |
|------------------------------|----------:|-----------------:|------:|----------------:|
| 10 `SET`s in one pipeline    |      22.5 |             19.7 |  17.0 |            15.7 |
| 100 `SET`s in one pipeline   |      20.6 |             19.1 |  12.8 |            11.4 |
| 1,000 `SET`s in one pipeline |      20.6 |             19.3 |  11.8 |            10.3 |

A pipeline removes the per-command round trip, which is where a real server loses most of its time. What is left for
fakeredis is parsing and running each command in Python.

### Whole-collection reads

Time per call, in milliseconds, for a reply of 100,000 elements (10,000 for `MGET`).

| ms per call                             | fakeredis | fakeredis (sync) | Redis | Redis + hiredis |
|-----------------------------------------|----------:|-----------------:|------:|----------------:|
| `LRANGE 0 -1`                           |      10.3 |             11.0 |   251 |            5.37 |
| `SMEMBERS`                              |      25.1 |             29.2 |   267 |            13.2 |
| `HGETALL`                               |      38.8 |             41.2 |   522 |            34.6 |
| `ZRANGE 0 -1 WITHSCORES`                |       211 |              216 |   648 |            74.5 |
| `XRANGE - +`                            |       378 |              382 | 1,219 |             112 |
| `KEYS big:key:*`                        |      27.1 |             27.7 |   264 |            10.4 |
| `MGET` (10,000 keys)                    |      29.3 |             28.8 |  34.0 |            9.47 |
| `scan_iter(count=1000)`, whole keyspace |      77.8 |             70.1 |   285 |            32.2 |

Without hiredis, a real server's time here is almost entirely redis-py parsing the reply in Python.

### Small reads from large collections

Time per call, in microseconds, on the same 100,000-element collections. Neither slows down with the size of
the collection for these.

| µs per call                                  | fakeredis | fakeredis (sync) | Redis | Redis + hiredis |
|----------------------------------------------|----------:|-----------------:|------:|----------------:|
| `GET`                                        |      25.4 |             21.8 |  38.2 |            36.1 |
| `HGET`                                       |      27.2 |             23.6 |  38.9 |            37.1 |
| `SISMEMBER`                                  |      27.1 |             23.5 |  37.6 |            37.2 |
| `ZSCORE`                                     |      26.9 |             23.4 |  38.1 |            37.0 |
| `LRANGE 0 9`                                 |      30.4 |             26.7 |  64.8 |            38.0 |
| `ZRANGE 0 9`                                 |      36.4 |             32.2 |  67.2 |            40.0 |
| `ZRANGEBYSCORE` (10 members from the middle) |      36.8 |             32.6 |  67.3 |            40.0 |
| `XRANGE - + COUNT 10`                        |      57.4 |             52.8 |   155 |            46.6 |
| `XREAD COUNT 10` (from the middle)           |      54.5 |             50.5 |   167 |            54.1 |

### New client

Time, in microseconds, to create a client, run one `GET` and close it. This matters for test suites that build a
client per test. For fakeredis the client is new but the data store is reused; for Redis it includes opening the
TCP connection.

| µs per call                              | fakeredis | fakeredis (sync) | Redis | Redis + hiredis |
|------------------------------------------|----------:|-----------------:|------:|----------------:|
| Create a client, run one `GET`, close it |       264 |              252 | 1,251 |           1,095 |

### Running the benchmark

The tables are printed by [
`scripts/benchmark.py`](https://github.com/cunla/fakeredis-py/blob/master/scripts/benchmark.py).
It needs a real server to compare with, and flushes the database the URL points at.

```bash
docker run -d --network host redis:8.10 redis-server --port 6398 --save "" --appendonly no

# redis-py's default parser
uv run python scripts/benchmark.py --redis-url redis://localhost:6398/15

# with hiredis
uv run --with hiredis python scripts/benchmark.py --redis-url redis://localhost:6398/15
```

The server runs on the host network because a published container port adds a proxy hop: about 11 µs per command
on the machine used here.
