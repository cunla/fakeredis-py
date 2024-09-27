# Support for valkey

[Valkey][1] is an open source (BSD) high-performance key/value datastore that supports a variety of workloads such as
caching, message queues, and can act as a primary database.
The project was forked from the open source Redis project right before the transition to their new source available
licenses.

FakeRedis can be used as a valkey replacement for testing and development purposes as well.

To make the process more straightforward, the `FakeValkey` class sets all relevant arguments in `FakeRedis` to the
valkey values.

```python
from fakeredis import FakeValkey

valkey = FakeValkey()
valkey.set("key", "value")
print(valkey.get("key"))
```

[1]: https://github.com/valkey-io/valkey
