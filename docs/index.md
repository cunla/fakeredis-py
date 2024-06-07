## fakeredis: A python implementation of redis server

FakeRedis is a pure-Python implementation of the Redis key-value store.

It enables running tests requiring redis server without an actual server.

It provides enhanced versions of the redis-py Python bindings for Redis.

That provides the following added functionality: A built-in Redis server that is automatically installed, configured and
managed when the Redis bindings are used.
A single server shared by multiple programs or multiple independent servers.
All the servers provided by FakeRedis support all Redis functionality including advanced features such as RedisJson,
GeoCommands.

For a list of supported/unsupported redis commands, see [Supported commands][6].

## Installation

To install fakeredis-py, simply:

```bash
pip install fakeredis        ## No additional modules support

pip install fakeredis[lua]   ## Support for LUA scripts

pip install fakeredis[json]  ## Support for RedisJSON commands

pip install fakeredis[probabilistic,json]  ## Support for RedisJSON and BloomFilter/CuckooFilter/CountMinSketch commands
```

## How to Use

### Use as a pytest fixture

```python
import pytest


@pytest.fixture
def redis_client(request):
    import fakeredis
    redis_client = fakeredis.FakeRedis()
    return redis_client
```

### General usage

FakeRedis can imitate Redis server version 6.x or 7.x. Version 7 is used by default.

The intent is for fakeredis to act as though you're talking to a real redis server.
It does this by storing the state internally. For example:

```pycon
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

```pycon
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

It is also possible to mock connection errors, so you can effectively test your error handling.
Set the connected attribute of the server to `False` after initialization.

```pycon
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

### async Redis

Async redis client is supported. Instead of using `fakeredis.FakeRedis`, use `fakeredis.aioredis.FakeRedis`.

```pycon
>>> from fakeredis import FakeAsyncRedis
>>> r1 = FakeAsyncRedis()
>>> await r1.set('foo', 'bar')
True
>>> await r1.get('foo')
'bar'
```

### Use to test django cache

Update your cache settings:

```python
from fakeredis import FakeConnection

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': '...',
        'OPTIONS': {
            'connection_class': FakeConnection
        }
    }
}
```

For [django-redis][8] library, use the following `OPTIONS`:

```
'OPTIONS': {
    'CONNECTION_POOL_KWARGS': {'connection_class': FakeConnection},
}
```

You can use
django [`@override_settings` decorator][9]

### Use to test django-rq

There is a need to override `django_rq.queues.get_redis_connection` with a method returning the same connection.

```python
import django_rq


# RQ
# Configuration to pretend there is a Redis service available.
# Set up the connection before RQ Django reads the settings.
# The connection must be the same because in fakeredis connections
# do not share the state. Therefore, we define a singleton object to reuse it.
def get_fake_connection(config: Dict[str, Any], strict: bool):
    from fakeredis import FakeRedis, FakeStrictRedis
    redis_cls = FakeStrictRedis if strict else FakeRedis
    if "URL" in config:
        return redis_cls.from_url(
            config["URL"],
            db=config.get("DB"),
        )
    return redis_cls(
        host=config["HOST"],
        port=config["PORT"],
        db=config.get("DB", 0),
        username=config.get("USERNAME", None),
        password=config.get("PASSWORD"),
    )


django_rq.queues.get_redis_connection = get_fake_connection
```

### Use to test FastAPI

See info on [this issue][7]

If you're using FastAPI dependency injection to provide a Redis connection,
then you can override that dependency for testing.

Your FastAPI application main.py:

```python
from typing import Annotated, Any, AsyncIterator

from redis import asyncio as redis
from fastapi import Depends, FastAPI

app = FastAPI()

async def get_redis() -> AsyncIterator[redis.Redis]:
    # Code to handle creating a redis connection goes here, for example
    async with redis.from_url("redis://localhost:6379") as client:  # type: ignore[no-untyped-call]
        yield client

@app.get("/")
async def root(redis_client: Annotated[redis.Redis, Depends(get_redis)]) -> Any:
    # Code that does something with redis goes here, for example:
    await redis_client.set("foo", "bar")
    return {"redis_keys": await redis_client.keys()}
```

Assuming you use pytest-asyncio, your test file
(or you can put the fixtures in conftest.py as usual):

```python
from typing import AsyncIterator
from unittest import mock

import fakeredis
import httpx
import pytest
import pytest_asyncio
from redis import asyncio as redis

from main import app, get_redis

@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[redis.Redis]:
    async with fakeredis.FakeAsyncRedis() as client:
        yield client

@pytest_asyncio.fixture
async def app_client(redis_client: redis.Redis) -> AsyncIterator[httpx.AsyncClient]:
    async def get_redis_override() -> redis.Redis:
        return redis_client
    transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type] # https://github.com/encode/httpx/issues/3111
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as app_client:
        with mock.patch.dict(app.dependency_overrides, {get_redis: get_redis_override}):
            yield app_client

@pytest.mark.asyncio
async def test_app(app_client: httpx.AsyncClient) -> None:
    response = await app_client.get("/")
    assert response.json()["redis_keys"] == ["foo"]
```

## Known Limitations

Apart from unimplemented commands, there are a number of cases where fakeredis won't give identical results to real
redis.
The following are differences that are unlikely to ever be fixed; there are also differences that are fixable (such as
commands that do not support all features) which should be filed as bugs in GitHub.

- Hyperloglogs are implemented using sets underneath. This means that the `type` command will return the wrong answer,
  you can't use `get` to retrieve the encoded value, and counts will be slightly different (they will in fact be exact).

- When a command has multiple error conditions, such as operating on a key of the wrong type and an integer argument is
  not well-formed, the choice of error to return may not match redis.

- The `incrbyfloat` and `hincrbyfloat` commands in redis use the C `long double` type, which typically has more
  precision than Python's `float` type.

- Redis makes guarantees about the order in which clients blocked on blocking commands are woken up. Fakeredis does not
  honor these guarantees.

- Where redis contains bugs, fakeredis generally does not try to provide exact bug compatibility. It's not practical for
  fakeredis to try to match the set of bugs in your specific version of redis.

- There are a number of cases where the behavior of redis is undefined, such as the order of elements returned by set
  and hash commands. Fakeredis will generally not produce the same results, and in Python versions before 3.6 may
  produce different results each time the process is re-run.

- SCAN/ZSCAN/HSCAN/SSCAN will not necessarily iterate all items if items are deleted or renamed during iteration. They
  also won't necessarily iterate in the same chunk sizes or the same order as redis. This is aligned with redis behavior
  as can be seen in tests `test_scan_delete_key_while_scanning_should_not_returns_it_in_scan`.

- DUMP/RESTORE will not return or expect data in the RDB format. Instead, the `pickle` module is used to mimic an opaque
  and non-standard format. **WARNING**: Do not use RESTORE with untrusted data, as a malicious pickle can execute
  arbitrary code.

## Local development environment

To ensure parity with the real redis, there are a set of integration tests that mirror the unittests. For every unittest
that is written, the same test is run against a real redis instance using a real redis-py client instance. To run these
tests, you must have a redis server running on localhost, port 6379 (the default settings). **WARNING**: the tests will
completely wipe your database!

First install poetry if you don't have it, and then install all the dependencies:

```bash
pip install poetry
poetry install
```

To run all the tests:

```bash
poetry run pytest -v
```

If you only want to run tests against fake redis, without a real redis::

```bash
poetry run pytest -m fake
```

Because this module is attempting to provide the same interface as `redis-py`, the python bindings to redis, a
reasonable way to test this to take each unittest and run it against a real redis server.
Fakeredis and the real redis server should give the same result.
To run tests against a real redis instance instead:

```bash
poetry run pytest -m real
```

If redis is not running, and you try to run tests against a real redis server, these tests will have a result of 's' for
skipped.

There are some tests that test redis blocking operations that are somewhat slow.
If you want to skip these tests during day-to-day development, they have all been tagged as 'slow' so you can skip them
by running:

```bash
poetry run pytest -m "not slow"
```

## Contributing

Contributions are welcome. You can contribute in many ways:

- Report bugs you found.
- Check out issues with [`Help wanted`][5] label.
- Implement commands which are not yet implemented. Follow the [guide how to implement a new command][1].
- Write additional test cases. Follow the [guide how to write a test-case][4].

Please follow coding standards listed in the [contributing guide][3].

## Sponsor

fakeredis-py is developed for free.

You can support this project by becoming a sponsor using [this link][2].


[1]:./guides/implement-command/

[2]:https://github.com/sponsors/cunla

[3]:./about/contributing.md

[4]:./guides/test-case/

[5]:https://github.com/cunla/fakeredis-py/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22

[6]:./redis-commands/

[7]:https://github.com/cunla/fakeredis-py/issues/292

[8]:https://github.com/jazzband/django-redis

[9]:https://docs.djangoproject.com/en/4.1/topics/testing/tools/#django.test.override_settings