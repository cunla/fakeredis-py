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
`dragonflydb/dragonfly` container (`df-v1.40.1`, which reports `redis_version:7.4.0`) and
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
| `SINTERCARD 9 key`             | `Number of keys can't be greater than number of args` | `syntax error`                             |
| `SINTERCARD 0 ...` / `LMPOP 0 ...` / `ZMPOP 0 ...` | `numkeys should be greater than 0`  | `at least 1 input key is needed for this command` |
| `ZINTERCARD 0 ...` / `ZUNION 0 ...` / `ZUNIONSTORE dst 0 ...` | `at least 1 input key is needed for <command>` | `at least 1 input key is needed for this command` |
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

### Sets and sorted sets

`SMOVE` checks the destination's type before it looks at the source, so moving a member out
of a key that does not exist into a string is a `WRONGTYPE` error. Redis answers 0 there,
and only complains about the destination once the source key exists.

`ZDIFF` and `ZDIFFSTORE` accept sorted sets only. Redis — and Dragonfly's own `ZUNION*`,
`ZINTER*` and `ZINTERCARD` — read a plain set as a sorted set scoring every member 1.

### Streams

`XINFO GROUPS` uses -1 as its "lag unknown" sentinel and reports that as nil. Any other
lag, negative ones included, is reported as the number it worked out.

`XPENDING` looks the key up before the group, so a missing stream is `ERR no such key`
rather than Redis' `NOGROUP No such key '<key>' or consumer group '<group>'`. Once the key
exists, a missing group is `NOGROUP No such consumer group '<group>' for key name '<key>'`.

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

Replies that Redis sends as a null, an empty map or a member/score pair are sent by
Dragonfly in the RESP2 shape it would have used anyway. Under RESP2 both servers encode
identically and clients see no difference.

| Reply                                       | Redis (RESP3)      | Dragonfly (RESP3)   |
|---------------------------------------------|--------------------|---------------------|
| `BLPOP` / `BRPOP` / `BZPOPMIN` timeout      | nil                | `[]`                |
| `XREAD` / `XREADGROUP` matching nothing     | `{}`               | `[]`                |
| `XREAD BLOCK` woken by a new entry          | `{name: entries}`  | `[[name, entries]]` |
| `XINFO STREAM` on an empty stream, `first-entry` / `last-entry` | nil | `[]`     |
| `ZPOPMIN` / `ZPOPMAX` without a count       | `[member, score]`  | `[[member, score]]` |

A blocking `XREAD` that is served straight away — the entry was already there — answers
with the map, like Redis. Only the reply built when the read actually waited comes back in
the RESP2 array shape. `XREADGROUP` sends the map on both paths.

!!! warning
    redis-py's RESP3 `XREAD` parser assumes the map and raises
    `AttributeError: 'list' object has no attribute 'items'` on Dragonfly's reply. Use
    `execute_command` with the response callbacks disabled if you need to read it.

### JSON

Dragonfly ships its own JSON implementation rather than RedisJSON, and it differs in three
ways that a client will notice.

**A legacy path answers like a JSONPath under RESP3.** `JSON.STRLEN j .a` is `[5]` on
Dragonfly and `5` on RedisJSON; the same goes for `ARRLEN`, `OBJLEN`, `OBJKEYS`,
`STRAPPEND`, `ARRAPPEND`, `ARRINSERT`, `ARRINDEX`, `ARRTRIM`, `ARRPOP` and `TOGGLE`, and
for an omitted path. A path that matched nothing still answers with a plain null, and under
RESP2 nothing is wrapped at all.

**The exceptions run the other way.** `JSON.NUMINCRBY` and `JSON.NUMMULTBY` are never
wrapped — `[2]` on RedisJSON under RESP3 is `2` on Dragonfly — and under RESP2 they answer
with the JSON text of the new value rather than the number. `JSON.TOGGLE` likewise answers
with JSON text (`true`/`false`) for a legacy path and with `0`/`1` for a JSONPath, where
RedisJSON answers with booleans throughout. `JSON.TYPE` wraps *each* match of a JSONPath in
an array of its own — `[[t1], [t2]]` against RedisJSON's `[[t1, t2]]`.

**JSONPath has no filter expressions.** Anything containing `[?(...)]` is rejected with
`ERR syntax error`, whatever the command; wildcards and recursive descent parse as usual.

A missing key is reported as `no such key` rather than RedisJSON's `could not perform this
operation on a key that doesn't exist`.

### Lua scripting

Dragonfly's interpreter is Lua 5.4, where Redis' is Lua 5.1, and it treats numbers as
numbers throughout instead of routing them through strings:

| Expression                                  | Redis      | Dragonfly |
|---------------------------------------------|------------|-----------|
| `return 3.2`                                | `3`        | `3.2`     |
| `type(redis.call("INCRBYFLOAT", k, 2.0))`   | `"string"` | `"number"` |
| `type(redis.call("ZSCORE", k, m))`          | `"string"` | `"number"` |

The same goes for the replies themselves: `INCRBYFLOAT` and `HINCRBYFLOAT` answer with a
double rather than a bulk string, which a RESP3 client sees as a float. Dragonfly renders a
double under RESP2 as the shortest string that round-trips, where Redis pads it out to 17
significant digits — a `ZSCORE` of `3.2` reads back as `3.2`, not `3.2000000000000002`.

`FLUSHDB` and `FLUSHALL` join the set of commands a script may not call, alongside `SAVE`,
`BGSAVE`, `SHUTDOWN`, `DEBUG`, `CONFIG`, `CLIENT`, `SCRIPT`, `EVAL`, `MULTI`/`EXEC`, the
`(P)SUBSCRIBE` family and the blocking pops:

```
Error running script (call to <sha>): @user_script:2: -ERR This Redis command is not allowed from script
```

`redis.log` accepts any level and silently drops a message logged at one it does not know,
where Redis answers `ERR Invalid debug level.`. It still requires two arguments or more.

Bad arguments to `redis.call` keep the pre-7 wording, `Lua redis() command arguments must
be strings or integers` rather than `Lua redis lib command arguments ...`, and every script
error is wrapped in the Redis 6 style `Error running script (call to <sha>): ...` even
though Dragonfly reports `redis_version` 7.

`SCRIPT FLUSH` has no `ASYNC`/`SYNC` mode and ignores whatever follows it instead of
rejecting it, and `SCRIPT HELP` prints Dragonfly's own text.

### Known differences that are not emulated yet

fakeredis still answers these the way Redis does, so a `server_type="dragonfly"` server
will not match a real one here:

- **Whole Lua numbers.** Dragonfly's Lua 5.4 tells `return 3` (an integer reply) from
  `return 3.0` and `return 1e300` (doubles). The Lua 5.1 runtime fakeredis uses has no
  integer subtype, so any Lua number without a fractional part comes back as an integer.
- **Script error detail.** The wrapper carries `@user_script:?:` rather than the real line
  number, and the error it wraps is not prefixed with `-` the way Dragonfly's is.
- **JSON error reporting.** Where RedisJSON names what went wrong — `Path '.a' does not
  exist or not a string` — Dragonfly answers most type and path mismatches with the single
  `WRONGTYPE wrong JSON type of path value`, and `JSON.TYPE key $.a` on a missing key with a
  null instead of an error. The reply *shapes* are emulated (see [JSON](#json) above); only
  these errors are not.
- **JSON numbers.** `JSON.NUMINCRBY` keeps a whole result whole — `1` incremented by `1` is
  `2`, where fakeredis renders `2.0`. Both parse to the same number.
- **Keyspace notifications.** Dragonfly implements only the `Ex` event class — `expired`
  events on the `__keyevent@<db>__:` channel. The `__keyspace@<db>__:` channel does not
  exist, and no other event is ever published. It is enabled at startup with
  `--notify_keyspace_events=Ex`, and that value must be exactly `Ex`: `E`, `x`, `KEx`,
  `Ax` and `KEA` all abort the server on boot with `Only Ex is currently supported`.
  `CONFIG SET notify-keyspace-events` always fails with `argument can not be set`, and
  `CONFIG GET` reports the setting under the underscored name `notify_keyspace_events`.

    !!! warning
        A failed `CONFIG SET` still changes what `CONFIG GET` reports, while the effective
        setting stays as it was at startup. Reading the value back is therefore no way to
        tell whether notifications are on.

[1]: https://www.dragonflydb.io/

[2]: https://www.dragonflydb.io/docs/command-reference/sets/saddex
