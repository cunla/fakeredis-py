# Support for Dragonfly

[Dragonfly DB][1] is a drop-in Redis replacement that cuts costs and boosts performance. Designed to fully utilize the
power of modern cloud hardware and deliver on the data demands of modern applications, Dragonfly frees developers from
the limits of traditional in-memory data stores.

FakeRedis can be used as a Dragonfly replacement for testing and development purposes as well.

Since Dragonfly does not have its own unique clients, you can use the `Fakeredis` client to connect to a Dragonfly.

```python
from fakeredis import FakeRedis

client = FakeRedis(server_type="dragonfly")
client.set("key", "value")
print(client.get("key"))
```

Alternatively, you can start a thread with a Fake Valkey server.

```python
from threading import Thread
from fakeredis import TcpFakeServer

server_address = ("127.0.0.1", 6379)
server = TcpFakeServer(server_address, server_type="dragonfly")
t = Thread(target=server.serve_forever, daemon=True)
t.start()

import redis

r = redis.Redis(host=server_address[0], port=server_address[1])
r.set("foo", "bar")
assert r.get("foo") == b"bar"
```

To call Dragonfly specific commands, which are not implemented in the redis-py client, you can use the
`execute_command`, like in this example calling the [`SADDEX`][2] command:

```python
from fakeredis import FakeRedis

client = FakeRedis(server_type="dragonfly")
client.sadd("key", "value")
# The SADDEX command is not implemented in redis-py
client.execute_command("SADDEX", 10, "key", "value")
```

## Differences between Dragonfly and Redis

Dragonfly is a drop-in replacement, but it is not bug-for-bug identical to Redis. The
differences below were established by running the fakeredis test suite against a real
`dragonflydb/dragonfly` container (`df-v1.39.0`, which reports `redis_version:7.4.0`) and
comparing every reply with the one Redis gives.

Unless a note says otherwise, `FakeRedis(server_type="dragonfly")` reproduces the
Dragonfly behaviour described here rather than the Redis one.

### Commands Dragonfly does not have

| Command                              | On Dragonfly                                           |
|--------------------------------------|--------------------------------------------------------|
| `LCS`                                | ``ERR unknown command `LCS` ``                         |
| `COPY ... DB <index>`                | `ERR syntax error` — there is no `DB` option at all     |
| `PUBSUB SHARDCHANNELS` / `SHARDNUMSUB` | `ERR PUBSUB <sub> is not supported in non cluster mode` |

`SSUBSCRIBE` and `SPUBLISH` themselves work; only the sharded *introspection*
subcommands are refused.

Of the hash-field expiry family, Dragonfly implements only `HEXPIRE`, `HTTL` and
`HSETEX`. `HPEXPIRE`, `HEXPIREAT`, `HPEXPIREAT`, `HPTTL`, `HPERSIST`, `HEXPIRETIME`,
`HPEXPIRETIME`, `HGETEX` and `HGETDEL` are all unknown commands.

!!! note
    fakeredis currently marks `HTTL` and `HSETEX` as Redis-only, so they are rejected on a
    Dragonfly server even though the real one accepts them.

### Error messages

Dragonfly names an unknown command in backticks, upper-cases it, and does not echo the
arguments back:

```
Redis:      ERR unknown command 'lcs', with args beginning with: 'k1'
Dragonfly:  ERR unknown command `LCS`
```

Most numeric options are validated while being decoded, so Dragonfly reports the generic
`ERR value is not an integer or out of range` where Redis names the offending option:

| Command                        | Redis                                            | Dragonfly                                       |
|--------------------------------|--------------------------------------------------|-------------------------------------------------|
| `SINTERCARD ... LIMIT -1`      | `LIMIT can't be negative`                        | `limit can't be negative`                       |
| `ZINTERCARD ... LIMIT -1`      | `LIMIT can't be negative`                        | `limit value is not a positive integer`         |
| `SINTERCARD 0 key`             | `numkeys should be greater than 0`               | `syntax error`                                  |
| `SINTERCARD 9 key`             | `Number of keys can't be greater than number of args` | `syntax error`                             |
| `LMPOP 0 ...` / `ZMPOP 0 ...`  | `numkeys should be greater than 0`               | `at least 1 input key is needed for this command` |
| `SPOP key -1`                  | `value is out of range, must be positive`        | `value is not an integer or out of range`       |
| `LPOS key e COUNT -1`          | `COUNT can't be negative`                        | `value is not an integer or out of range`       |
| `LPOS key e MAXLEN -1`         | `MAXLEN can't be negative`                        | `value is not an integer or out of range`      |
| `LPOS key e RANK 0`            | `RANK can't be zero`                             | `value is not an integer or out of range`       |
| `EXPIRE key 1 BOGUS`           | `Unsupported option BOGUS`                       | `Unsupported option: BOGUS`                     |

A `numkeys` or `COUNT` argument is read as **unsigned**, so a negative value fails to
decode before any other check runs.

### Key and field expiry

Dragonfly will not store an expiry deadline more than `2**28 - 1` seconds (~8.5 years)
away. Which way it fails depends on how the deadline was expressed:

- **Relative** (`EXPIRE`, `PEXPIRE`) — silently clamped to the horizon.
- **Absolute** (`EXPIREAT`, `PEXPIREAT`) — rejected with `ERR expiry is out of range`.

```python
client.expire("key", 2**28 + 10_000)  # accepted, TTL clamped to 2**28 - 1
client.expireat("key", 33_177_117_420)  # ERR expiry is out of range
```

A hash field's TTL is capped more tightly still: `HEXPIRE` rejects anything above
`2**26` seconds with `ERR value is not an integer or out of range`.

`EXPIRE` option pairs are also checked differently. Dragonfly refuses only the two
directly contradictory pairs and accepts `NX` alongside `GT` or `LT`:

| Options   | Redis                                                     | Dragonfly                                      |
|-----------|-----------------------------------------------------------|------------------------------------------------|
| `NX XX`   | `NX and XX, GT or LT options at the same time are not compatible` | `NX and XX options at the same time are not compatible` |
| `GT LT`   | error                                                     | `GT and LT options at the same time are not compatible` |
| `NX GT`   | error                                                     | accepted                                       |
| `NX LT`   | error                                                     | accepted                                       |

### SORT

Dragonfly's `SORT` diverges in four ways:

- A `BY` pattern with no `*` disables sorting, as on Redis, but `DESC` is then **ignored**
  rather than reversing the natural order.
- There is no `->` hash-field syntax. `BY record_*->age` is taken as a literal key name
  (`record_<element>->age`), so it usually resolves to nothing.
- A `GET` pattern does not need a `*`; without one it is a literal key lookup, where Redis
  returns nil.
- A `GET` that resolves to nothing yields an empty string rather than nil.
- Equal weights keep their existing order; Redis breaks such ties on the element itself.

### GEOSEARCH

`COUNT` alone does not imply an ascending sort. Results come back in geohash (sorted-set
score) order unless `ASC` or `DESC` is given explicitly.

### Pub/Sub

Outside cluster mode Dragonfly keeps a **single channel namespace**. A sharded
subscription lands in the same place as a plain one, so `SPUBLISH` reaches plain
subscribers and `PUBLISH` reaches sharded ones. Only the message type differs, and it is
decided by the publishing command.

`SUNSUBSCRIBE` is confirmed with a plain `unsubscribe` message rather than `sunsubscribe`.

!!! warning
    redis-py tracks sharded subscriptions in a separate `shard_channels` set that it only
    clears on a `sunsubscribe` confirmation. Against Dragonfly that set is never cleared,
    so `PubSub.subscribed` stays `True` after `sunsubscribe()`.

### Transactions

Any `SETBIT` dirties the key, so a `SETBIT` that writes back the value already stored
still invalidates a `WATCH`. Redis only invalidates when the stored value actually
changes.

### RESP3 reply shapes

Two replies that Redis sends as a null or empty map are sent by Dragonfly as an empty
array. Under RESP2 both encode identically and clients see no difference.

| Reply                                       | Redis (RESP3) | Dragonfly (RESP3) |
|---------------------------------------------|---------------|-------------------|
| `BLPOP` / `BRPOP` / `BZPOPMIN` timeout      | nil           | `[]`              |
| `XREAD` / `XREADGROUP` matching nothing     | `{}`          | `[]`              |

!!! warning
    redis-py's RESP3 `XREAD` parser assumes the map and raises
    `AttributeError: 'list' object has no attribute 'items'` on Dragonfly's reply. Use
    `execute_command` with the response callbacks disabled if you need to read it.

### Known differences that are not emulated yet

fakeredis still answers these the way Redis does, so a `server_type="dragonfly"` server
will not match a real one here:

- **Scripting.** `FLUSHALL` and `FLUSHDB` are rejected from inside a script. Lua numbers
  are not truncated to integers (`return 3.2` yields `3.2`, not `3`). `redis.log` accepts
  any log level. `SCRIPT FLUSH` accepts any argument instead of rejecting it. `SCRIPT
  HELP` prints its own text.
- **JSON.** Dragonfly returns single-element arrays where RedisJSON returns scalars — for
  example `JSON.STRLEN j $.a` gives `[5]` rather than `5` — and reports a missing key as
  `no such key`.
- **Streams.** The `XINFO STREAM` and `XGROUP SETID` replies differ.
- **Keyspace notifications.** `notify-keyspace-events` cannot be set: `CONFIG SET` fails
  with `argument can not be set`. `CONFIG GET` reports it under the underscored name
  `notify_keyspace_events`.

[1]: https://www.dragonflydb.io/

[2]: https://www.dragonflydb.io/docs/command-reference/sets/saddex
