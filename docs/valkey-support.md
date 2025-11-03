# Support for valkey

[Valkey][valkey] is an open source (BSD) high-performance key/value datastore that supports a variety of workloads such as
caching, message queues, and can act as a primary database.
The project was forked from the open source Redis project right before the transition to their new source available
licenses.

FakeRedis can be used as a valkey replacement for testing and development purposes as well.

To install FakeRedis with Valkey support, you can use the following command:

```bash
pip install fakeredis[valkey]
```

To make the process more straightforward, the `FakeValkey` class sets all relevant arguments in `FakeRedis` to the
valkey values.

```python
from fakeredis import FakeValkey

valkey = FakeValkey()
valkey.set("key", "value")
print(valkey.get("key"))
```

Alternatively, you can start a thread with a Fake Valkey server.

```python
from threading import Thread
from fakeredis import TcpFakeServer

server_address = ("127.0.0.1", 6379)
server = TcpFakeServer(server_address, server_type="valkey")
t = Thread(target=server.serve_forever, daemon=True)
t.start()

import valkey

r = valkey.Valkey(host=server_address[0], port=server_address[1])
r.set("foo", "bar")
assert r.get("foo") == b"bar"

```

[valkey]: https://github.com/valkey-io/valkey
