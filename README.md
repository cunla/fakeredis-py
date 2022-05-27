fakeredis: A fake version of a redis-py
=======================================

![badge](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/cunla/b756396efb895f0e34558c980f1ca0c7/raw/fakeredis-py.json)

- [fakeredis: A fake version of a redis-py](#fakeredis--a-fake-version-of-a-redis-py)
- [How to Use](#how-to-use)
- [Other limitations](#other-limitations)
- [Support for redis-py <4.2 with aioredis](#support-for-redis-py--42-with-aioredis)
    + [aioredis 1.x](#aioredis-1x)
    + [aioredis 2.x](#aioredis-2x)
- [Running the Tests](#running-the-tests)
- [Contributing](#contributing)
- [Alternatives](#alternatives)


fakeredis is a pure-Python implementation of the redis-py python client
that simulates talking to a redis server.  This was created for a single
purpose: **to write unittests**.  Setting up redis is not hard, but
many times you want to write unittests that do not talk to an external server
(such as redis).  This module now allows tests to simply use this
module as a reasonable substitute for redis.

Although fakeredis is pure Python, you will need [lupa](https://pypi.org/project/lupa/) if you want to run Lua
scripts (this includes features like ``redis.lock.Lock``, which are implemented
in Lua). If you install fakeredis with ``pip install fakeredis[lua]`` it will
be automatically installed.

For a list of supported/unsupported redis commands, see [REDIS_COMMANDS.md](REDIS_COMMANDS.md)

# How to Use

The intent is for fakeredis to act as though you're talking to a real
redis server. It does this by storing state internally.
For example:

```
>>> import fakeredis
>>> r = fakeredis.FakeStrictRedis()
>>> r.set('foo', 'bar')
True
>>> r.get('foo')
'bar'
>>> r.lpush('bar', 1)
1
>>> r.lpush('bar', 2)
2
>>> r.lrange('bar', 0, -1)
[2, 1]
```

The state is stored in an instance of `FakeServer`. If one is not provided at
construction, a new instance is automatically created for you, but you can
explicitly create one to share state:

```
>>> import fakeredis
>>> server = fakeredis.FakeServer()
>>> r1 = fakeredis.FakeStrictRedis(server=server)
>>> r1.set('foo', 'bar')
True
>>> r2 = fakeredis.FakeStrictRedis(server=server)
>>> r2.get('foo')
'bar'
>>> r2.set('bar', 'baz')
True
>>> r1.get('bar')
'baz'
>>> r2.get('bar')
'baz'
```

It is also possible to mock connection errors so you can effectively test
your error handling. Simply set the connected attribute of the server to
`False` after initialization.


```
>>> import fakeredis
>>> server = fakeredis.FakeServer()
>>> server.connected = False
>>> r = fakeredis.FakeStrictRedis(server=server)
>>> r.set('foo', 'bar')
ConnectionError: FakeRedis is emulating a connection error.
>>> server.connected = True
>>> r.set('foo', 'bar')
True
```

Fakeredis implements the same interface as `redis-py`, the
popular redis client for python, and models the responses
of redis 6.2 (although most new features are not supported).

# Other limitations

Apart from unimplemented commands, there are a number of cases where fakeredis
won't give identical results to real redis. The following are differences that
are unlikely to ever be fixed; there are also differences that are fixable
(such as commands that do not support all features) which should be filed as
bugs in Github.

1. Hyperloglogs are implemented using sets underneath. This means that the
   `type` command will return the wrong answer, you can't use `get` to retrieve
   the encoded value, and counts will be slightly different (they will in fact be
   exact).

2. When a command has multiple error conditions, such as operating on a key of
   the wrong type and an integer argument is not well-formed, the choice of
   error to return may not match redis.

3. The `incrbyfloat` and `hincrbyfloat` commands in redis use the C `long
   double` type, which typically has more precision than Python's `float`
   type.

4. Redis makes guarantees about the order in which clients blocked on blocking
   commands are woken up. Fakeredis does not honour these guarantees.

5. Where redis contains bugs, fakeredis generally does not try to provide exact
   bug-compatibility. It's not practical for fakeredis to try to match the set
   of bugs in your specific version of redis.

6. There are a number of cases where the behaviour of redis is undefined, such
   as the order of elements returned by set and hash commands. Fakeredis will
   generally not produce the same results, and in Python versions before 3.6
   may produce different results each time the process is re-run.

7. SCAN/ZSCAN/HSCAN/SSCAN will not necessarily iterate all items if items are
   deleted or renamed during iteration. They also won't necessarily iterate in
   the same chunk sizes or the same order as redis.

8. DUMP/RESTORE will not return or expect data in the RDB format. Instead the
   `pickle` module is used to mimic an opaque and non-standard format.
   **WARNING**: Do not use RESTORE with untrusted data, as a malicious pickle
   can execute arbitrary code.

# Support for redis-py <4.2 with aioredis

Aioredis is now in redis-py 4.2.0. But support is maintained until fakeredis 2 for older version of redis-py.

You can also use fakeredis to mock out [aioredis](https://aioredis.readthedocs.io/).  This is a much newer
addition to fakeredis (added in 1.4.0) with less testing, so your mileage may
vary. Both version 1 and version 2 (which have very different APIs) are
supported. The API provided by fakeredis depends on the version of aioredis that is
installed.

### aioredis 1.x

Example:

```
>>> import fakeredis.aioredis
>>> r = await fakeredis.aioredis.create_redis_pool()
>>> await r.set('foo', 'bar')
True
>>> await r.get('foo')
b'bar'
```

You can pass a `FakeServer` as the first argument to `create_redis` or
`create_redis_pool` to share state (you can even share state with a
`fakeredis.FakeRedis`). It should even be safe to do this state sharing between
threads (as long as each connection/pool is only used in one thread).

It is highly recommended that you only use the aioredis support with
Python 3.5.3 or higher. Earlier versions will not work correctly with
non-default event loops.

### aioredis 2.x

Example:

```
>>> import fakeredis.aioredis
>>> r = fakeredis.aioredis.FakeRedis()
>>> await r.set('foo', 'bar')
True
>>> await r.get('foo')
b'bar'
```

The support is essentially the same as for redis-py e.g., you can pass a
`server` keyword argument to the `FakeRedis` constructor.


# Running the Tests

To ensure parity with the real redis, there are a set of integration tests
that mirror the unittests.  For every unittest that is written, the same
test is run against a real redis instance using a real redis-py client
instance.  In order to run these tests you must have a redis server running
on localhost, port 6379 (the default settings). **WARNING**: the tests will
completely wipe your database!


First install poetry if you don't have it, and then install all the dependencies:
```   
pip install poetry
poetry install
``` 

To run all the tests:
```
poetry run pytest -v
```

If you only want to run tests against fake redis, without a real redis::
```
poetry run pytest -m fake
```

Because this module is attempting to provide the same interface as `redis-py`,
the python bindings to redis, a reasonable way to test this to to take each
unittest and run it against a real redis server.  fakeredis and the real redis
server should give the same result. To run tests against a real redis instance
instead::
```
poetry run pytest -m real
```

If redis is not running and you try to run tests against a real redis server,
these tests will have a result of 's' for skipped.

There are some tests that test redis blocking operations that are somewhat
slow.  If you want to skip these tests during day to day development,
they have all been tagged as 'slow' so you can skip them by running::
```
poetry run pytest -m "not slow"
```

# Contributing
Contributions are welcome.  Please see the 
[contributing guide](.github/CONTRIBUTING.md) for more details. 
The maintainer generally has very little time to work on fakeredis, so the 
best way to get a bug fixed is to contribute a pull request.

If you'd like to help out, you can start with any of the issues
labeled with `Help wanted`.

# Alternatives

Consider using [redislite](https://redislite.readthedocs.io/en/latest/) instead of fakeredis. 
It runs a real redis server and connects to it over a UNIX domain socket, so it will behave just like a real
server. Another alternative is [birdisle](https://birdisle.readthedocs.io/en/latest/), which 
runs the redis code as a Python extension (no separate process), but which is currently unmaintained.
