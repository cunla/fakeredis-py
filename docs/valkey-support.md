# Support for valkey

[Valkey][1] is an open source (BSD) high-performance key/value datastore that supports a variety of workloads such as
caching, message queues, and can act as a primary database.
The project was forked from the open source Redis project right before the transition to their new source available
licenses.

FakeRedis can be used as a valkey replacement for testing and development purposes as well.

To make the process more straightforward, we have added a `FakeValkey` module to fakeredis that provides the same API as
`FakeRedis` but with the valkey-specific commands/exceptions.

[1]: https://github.com/valkey-io/valkey
