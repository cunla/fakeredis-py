fakeredis: A fake version of a redis-py
=======================================
[![badge](https://img.shields.io/pypi/v/fakeredis)](https://pypi.org/project/fakeredis/)
[![CI](https://github.com/cunla/fakeredis-py/actions/workflows/test.yml/badge.svg)](https://github.com/cunla/fakeredis-py/actions/workflows/test.yml)
[![badge](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/cunla/b756396efb895f0e34558c980f1ca0c7/raw/fakeredis-py.json)](https://github.com/cunla/fakeredis-py/actions/workflows/test.yml)
[![badge](https://img.shields.io/pypi/dm/fakeredis)](https://pypi.org/project/fakeredis/)
[![badge](https://img.shields.io/pypi/l/fakeredis)](./LICENSE)
--------------------
[Intro](#intro) | [How to Use](#how-to-use) | [Contributing](.github/CONTRIBUTING.md) | [Guides](#guides)
| [Sponsoring](#sponsor)

# Intro

fakeredis is a pure-Python implementation of the redis-py python client
that simulates talking to a redis server. This was created for a single
purpose: **to write tests**. Setting up redis is not hard, but
many times you want to write tests that do not talk to an external server
(such as redis). This module now allows tests to simply use this
module as a reasonable substitute for redis.

For a list of supported/unsupported redis commands, see [REDIS_COMMANDS.md](./REDIS_COMMANDS.md).

# Installation

To install fakeredis-py, simply:

``` bash
$ pip install fakeredis
```

You will need [lupa](https://pypi.org/project/lupa/) if you want to run Lua scripts
(this includes features like ``redis.lock.Lock``, which are implemented in Lua).
If you install fakeredis with ``pip install fakeredis[lua]`` it will be automatically installed.

# How to Use

FakeRedis can imitate Redis server version 6.x or 7.x.
If you do not specify the version, version 7 is used by default.

The intent is for fakeredis to act as though you're talking to a real
redis server. It does this by storing state internally.
For example:

```
>>> import fakeredis
>>> r = fakeredis.FakeStrictRedis(version=6)
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

It is also possible to mock connection errors, so you can effectively test
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

Fakeredis implements the same interface as `redis-py`, the popular
redis client for python, and models the responses of redis 6.x or 7.x.

## Use to test django-rq

There is a need to override `django_rq.queues.get_redis_connection` with
a method returning the same connection.

```python
from fakeredis import FakeRedisConnSingleton

django_rq.queues.get_redis_connection = FakeRedisConnSingleton()
```

### Limitations

Apart from unimplemented commands, there are a number of cases where fakeredis
won't give identical results to real redis. The following are differences that
are unlikely to ever be fixed; there are also differences that are fixable
(such as commands that do not support all features) which should be filed as
bugs in GitHub.

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

8. DUMP/RESTORE will not return or expect data in the RDB format. Instead, the
   `pickle` module is used to mimic an opaque and non-standard format.
   **WARNING**: Do not use RESTORE with untrusted data, as a malicious pickle
   can execute arbitrary code.

### Local development environment

To ensure parity with the real redis, there are a set of integration tests
that mirror the unittests. For every unittest that is written, the same
test is run against a real redis instance using a real redis-py client
instance. In order to run these tests you must have a redis server running
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
the python bindings to redis, a reasonable way to test this to take each
unittest and run it against a real redis server. fakeredis and the real redis
server should give the same result. To run tests against a real redis instance
instead:

```
poetry run pytest -m real
```

If redis is not running, and you try to run tests against a real redis server,
these tests will have a result of 's' for skipped.

There are some tests that test redis blocking operations that are somewhat
slow. If you want to skip these tests during day to day development,
they have all been tagged as 'slow' so you can skip them by running:

```
poetry run pytest -m "not slow"
```

# Contributing

Contributions are welcome. Please see the [contributing guide](.github/CONTRIBUTING.md) for more details.
If you'd like to help out, you can start with any of the issues labeled with `Help wanted`.

# Guides

### Implementing support for a command

Creating a new command support should be done in the `FakeSocket` class (in `_fakesocket.py`) by creating the method
and using `@command` decorator (which should be the command syntax, you can use existing samples on the file).

For example:

```python
class FakeSocket(BaseFakeSocket, FakeLuaSocket):
    # ...
    @command(...)
    def zscore(self, key, member):
        try:
            return self._encodefloat(key.value[member], False)
        except KeyError:
            return None
```

#### Implement a test for it

There are multiple scenarios for test, with different versions of redis server, redis-py, etc.
The tests not only assert the validity of output but runs the same test on a real redis-server and compares the output
to the real server output.

- Create tests in the `test_fakeredis6.py` if the command is supported in redis server 6.x.
- Alternatively, create the test in `test_fakeredis7.py` if the command is supported only on redis server 7.x.
- If support for the command was introduced in a certain version of redis-py (
  see [redis-py release notes](https://github.com/redis/redis-py/releases/tag/v4.3.4)) you can use the
  decorator `@testtools.run_test_if_redispy_ver` on your tests. example:

```python
@testtools.run_test_if_redispy_ver('above', '4.2.0')  # This will run for redis-py 4.2.0 or above.
def test_expire_should_not_expire__when_no_expire_is_set(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    assert r.expire('foo', 1, xx=True) == 0
```

#### Updating `REDIS_COMMANDS.md`

Lastly, run from the root of the project the script to regenerate `REDIS_COMMANDS.md`:

```
python scripts/supported.py > REDIS_COMMANDS.md    
```

# Sponsor

fakeredis-py is developed for free.

You can support this project by becoming a sponsor using [this link](https://github.com/sponsors/cunla).

Alternatively, you can buy me coffee using this
link: [!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/danielmoran)
