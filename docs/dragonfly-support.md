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

[1]: https://www.dragonflydb.io/

[2]: https://www.dragonflydb.io/docs/command-reference/sets/saddex