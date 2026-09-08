# Support for KiviDB

[KiviDB][1] is a Rust in-memory database that speaks RESP as a drop-in Redis replacement, so it is used through the
regular Redis clients and only the server behaviour differs.

FakeRedis can be used as a KiviDB replacement for testing and development purposes as well.

Since KiviDB does not have its own unique clients, you can use the `FakeRedis` client to connect to it.

```python
from fakeredis import FakeRedis

client = FakeRedis(server_type="kividb")
client.set("key", "value")
print(client.get("key"))
```

Alternatively, you can start a thread with a fake KiviDB server.

```python
from threading import Thread
from fakeredis import TcpFakeServer

server_address = ("127.0.0.1", 6379)
server = TcpFakeServer(server_address, server_type="kividb")
t = Thread(target=server.serve_forever, daemon=True)
t.start()

import redis

r = redis.Redis(host=server_address[0], port=server_address[1])
r.set("foo", "bar")
assert r.get("foo") == b"bar"
```

## Server version

A real KiviDB reports two versions in `INFO`: a `redis_version` — `7.0.15` in KiviDB 1.0.4 — and its own
`kividb_version`. The two are unrelated, since KiviDB's `1.0.x` numbering tracks its own releases rather than the Redis
version it emulates.

The `version` argument is the **Redis** version, as it is for every other server type, so pin it to the `redis_version`
your KiviDB reports rather than to its `kividb_version`:

```python
from fakeredis import FakeRedis

client = FakeRedis(server_type="kividb", version="7.0.15")
```

Left unset it defaults to `8`, the same default the other server types get.

## Differences between KiviDB and Redis

Apart from the command surface below, `server_type="kividb"` currently answers exactly as Redis does.

### Commands a KiviDB server does not serve

Commands that fakeredis restricts to a narrower set of server types are not served on a KiviDB server, and answer with
an `unknown command` error:

| Group             | Commands                                                                          |
|-------------------|-----------------------------------------------------------------------------------|
| String            | `LCS`                                                                             |
| Hash field expiry | `HTTL`, `HPTTL`, `HEXPIRETIME`, `HPEXPIRETIME`, `HGETEX`, `HGETDEL`, `HSETEX`      |
| Streams           | `XDELEX`, `XACKDEL`, `XNACK`, `XIDMPRECORD`                                       |

Dragonfly's own [`SADDEX`][2] and `CL.THROTTLE` are not served either.

!!! note
    KiviDB's own behaviour is not emulated yet. The exclusions above fall out of those commands being marked as
    belonging to Redis (or Dragonfly) rather than from KiviDB's real command surface having been checked against a
    running server, and every other command answers the Redis way. A `server_type="kividb"` server will therefore not
    match a real KiviDB wherever the two diverge — unlike [Dragonfly](dragonfly-support.md), whose differences have
    been catalogued.

[1]: https://www.kividb.io/

[2]: https://www.dragonflydb.io/docs/command-reference/sets/saddex
