"""Benchmark a real Redis server, fakeredis and burner-redis on the same operations.

Prints the Markdown tables shown in docs/performance.md. All three are driven through their asyncio API, the only one
burner-redis has, so the comparison is like for like; fakeredis' sync client is measured next to them as well.

    uv run --with burner-redis python scripts/benchmark.py --redis-url redis://localhost:6390/15

The database the URL points at is flushed. burner-redis is optional: without it, its column reads "n/a".
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import platform
import time
from importlib import metadata
from typing import Any, Awaitable, Callable

import redis
import redis.asyncio

import fakeredis

try:
    from burner_redis import BurnerRedis
except ImportError:  # pragma: no cover
    BurnerRedis = None

ROUNDS = 5
ROUND_SECONDS = 0.15
NA = "n/a"

Op = Callable[[Any], Awaitable[Any]]


async def _maybe_await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


class SyncAdapter:
    """Lets the sync fakeredis client be driven by the same coroutines as the asyncio clients."""

    def __init__(self, client: Any) -> None:
        self._client = client

    def __getattr__(self, name: str) -> Any:
        attr = getattr(self._client, name)
        if name in ("pipeline", "scan_iter") or not callable(attr):
            return attr

        def call(*args: Any, **kwargs: Any) -> Any:
            return _Done(attr(*args, **kwargs))

        return call


class _Done:
    """An already computed value that can be awaited."""

    def __init__(self, value: Any) -> None:
        self._value = value

    def __await__(self) -> Any:
        return self._value
        yield


def new_pipeline(client: Any) -> Any:
    try:
        return client.pipeline(transaction=False)
    except TypeError:  # burner-redis takes no arguments
        return client.pipeline()


async def measure(op: Op, client: Any, fixed_n: int | None = None) -> float:
    """Seconds one call of `op` takes: the best of several rounds of back-to-back calls."""
    await op(client)
    if fixed_n is None:
        start = time.perf_counter()
        await op(client)
        once = max(time.perf_counter() - start, 1e-7)
        n = max(1, min(20000, int(ROUND_SECONDS / once)))
    else:
        n = fixed_n
    best = float("inf")
    for _ in range(ROUNDS):
        start = time.perf_counter()
        for _ in range(n):
            await op(client)
        best = min(best, (time.perf_counter() - start) / n)
    return best


async def run_table(
    backends: dict[str, Callable[[], Awaitable[Any]]],
    rows: list[tuple[str, Op | None, Op]],
    fixed_n: int | None = None,
) -> dict[str, dict[str, float | None]]:
    """Time every row on every backend. A row is (label, setup, op); setup runs once per backend before timing."""
    results: dict[str, dict[str, float | None]] = {label: {} for label, _, _ in rows}
    for name, make in backends.items():
        client = await make()
        for label, setup, op in rows:
            try:
                if setup is not None:
                    await setup(client)
                results[label][name] = await measure(op, client, fixed_n)
            except (NotImplementedError, AttributeError, TypeError) as e:
                results[label][name] = None
                print(f"<!-- {name}: {label}: {type(e).__name__}: {e} -->")
        await close(client)
    return results


def print_table(title: str, unit: str, scale: float, backends: list[str], results: dict[str, dict[str, float | None]]):
    print(f"\n### {title}\n")
    print(f"| {unit} | " + " | ".join(backends) + " |")
    print("|---|" + "---:|" * len(backends))
    for label, row in results.items():
        cells = []
        for name in backends:
            value = row.get(name)
            if value is None:
                cells.append(NA)
            else:
                scaled = value * scale
                cells.append(
                    f"{scaled:,.0f}" if scaled >= 100 else f"{scaled:.1f}" if scaled >= 10 else f"{scaled:.2f}"
                )
        print(f"| {label} | " + " | ".join(cells) + " |")


async def close(client: Any) -> None:
    for name in ("aclose", "close"):
        method = getattr(client, name, None)
        if method is not None:
            await _maybe_await(method())
            return


async def fill(client: Any, n: int) -> None:
    """Load `n` elements into one key of each type, and `n` string keys."""
    step = 1000
    for start in range(0, n, step):
        ids = range(start, min(start + step, n))
        pipe = new_pipeline(client)
        pipe.rpush("big:list", *[f"item-{i}" for i in ids])
        pipe.sadd("big:set", *[f"member-{i}" for i in ids])
        pipe.hset("big:hash", mapping={f"field-{i}": f"value-{i}" for i in ids})
        pipe.zadd("big:zset", {f"member-{i}": i for i in ids})
        for i in ids:
            pipe.set(f"big:key:{i}", f"value-{i}")
            pipe.xadd("big:stream", {"n": str(i)}, id=f"{i + 1}-0")
        await _maybe_await(pipe.execute())


async def scan_all(client: Any) -> int:
    count = 0
    keys = client.scan_iter(match="big:key:*", count=1000)
    if hasattr(keys, "__aiter__"):
        async for _ in keys:
            count += 1
    else:
        for _ in keys:
            count += 1
    return count


async def pipeline_of(client: Any, n: int) -> None:
    pipe = new_pipeline(client)
    for i in range(n):
        pipe.set(f"pipe:{i}", "value")
    await _maybe_await(pipe.execute())


def single_command_rows() -> list[tuple[str, Op | None, Op]]:
    async def setup_keys(r: Any) -> None:
        await r.set("str", "value")
        await r.hset("hash", mapping={f"f{i}": f"v{i}" for i in range(10)})
        await r.sadd("set", *[f"m{i}" for i in range(10)])
        await r.zadd("zset", {f"m{i}": i for i in range(10)})
        await r.rpush("list", *[f"i{i}" for i in range(10)])
        for i in range(10):
            await r.set(f"k{i}", "value")
            await r.xadd("stream", {"f": "v"})

    async def setup_group(r: Any) -> None:
        await r.xgroup_create("gstream", "group", id="0", mkstream=True)

    async def read_group(r: Any) -> None:
        await r.xadd("gstream", {"f": "v"})
        res = await r.xreadgroup("group", "consumer", {"gstream": ">"}, count=1)
        stream = res[0] if isinstance(res, list) else next(iter(res.items()))
        await r.xack("gstream", "group", stream[1][0][0])

    async def push_pop(r: Any) -> None:
        await r.rpush("queue", "job")
        await r.lpop("queue")

    async def set_delete(r: Any) -> None:
        await r.set("temp", "value")
        await r.delete("temp")

    keys = [f"k{i}" for i in range(10)]
    script = "return redis.call('GET', KEYS[1])"
    return [
        ("`SET`", setup_keys, lambda r: r.set("str", "value")),
        ("`SET ... EX`", None, lambda r: r.set("str", "value", ex=100)),
        ("`GET`", None, lambda r: r.get("str")),
        ("`MGET` (10 keys)", None, lambda r: r.mget(*keys)),
        ("`EXISTS`", None, lambda r: r.exists("str")),
        ("`EXPIRE`", None, lambda r: r.expire("str", 100)),
        ("`TTL`", None, lambda r: r.ttl("str")),
        ("`SET` + `DEL`", None, set_delete),
        ("`INCR`", None, lambda r: r.incr("counter")),
        ("`HSET`", None, lambda r: r.hset("hash", "f1", "value")),
        ("`HGET`", None, lambda r: r.hget("hash", "f1")),
        ("`HGETALL` (10 fields)", None, lambda r: r.hgetall("hash")),
        ("`HINCRBY`", None, lambda r: r.hincrby("hash", "n", 1)),
        ("`SADD`", None, lambda r: r.sadd("set", "m1")),
        ("`SISMEMBER`", None, lambda r: r.sismember("set", "m1")),
        ("`SMEMBERS` (10 members)", None, lambda r: r.smembers("set")),
        ("`RPUSH` + `LPOP`", None, push_pop),
        ("`LRANGE` (10 items)", None, lambda r: r.lrange("list", 0, -1)),
        ("`ZADD`", None, lambda r: r.zadd("zset", {"m1": 1})),
        ("`ZSCORE`", None, lambda r: r.zscore("zset", "m1")),
        ("`ZRANGE` (10 members, with scores)", None, lambda r: r.zrange("zset", 0, -1, withscores=True)),
        ("`XADD` (`MAXLEN 1000`)", None, lambda r: r.xadd("capped", {"f": "v"}, maxlen=1000)),
        ("`XRANGE` (10 entries)", None, lambda r: r.xrange("stream", count=10)),
        ("`XREAD` (10 entries)", None, lambda r: r.xread({"stream": "0"}, count=10)),
        ("`XADD` + `XREADGROUP` + `XACK`", setup_group, read_group),
        ("`PUBLISH` (no subscribers)", None, lambda r: r.publish("channel", "message")),
        ("`EVAL` (one `redis.call`)", None, lambda r: r.eval(script, 1, "str")),
    ]


def large_rows(n: int) -> list[tuple[str, Op | None, Op]]:
    keys = [f"big:key:{i}" for i in range(0, n, 10)]
    return [
        ("`LRANGE 0 -1`", lambda r: fill(r, n), lambda r: r.lrange("big:list", 0, -1)),
        ("`SMEMBERS`", None, lambda r: r.smembers("big:set")),
        ("`HGETALL`", None, lambda r: r.hgetall("big:hash")),
        ("`ZRANGE 0 -1 WITHSCORES`", None, lambda r: r.zrange("big:zset", 0, -1, withscores=True)),
        ("`XRANGE - +`", None, lambda r: r.xrange("big:stream")),
        ("`KEYS big:key:*`", None, lambda r: r.keys("big:key:*")),
        (f"`MGET` ({len(keys):,} keys)", None, lambda r: r.mget(*keys)),
        ("`scan_iter(count=1000)`, whole keyspace", None, scan_all),
    ]


def needle_rows(n: int) -> list[tuple[str, Op | None, Op]]:
    mid = n // 2
    return [
        ("`GET`", None, lambda r: r.get(f"big:key:{mid}")),
        ("`HGET`", None, lambda r: r.hget("big:hash", f"field-{mid}")),
        ("`SISMEMBER`", None, lambda r: r.sismember("big:set", f"member-{mid}")),
        ("`ZSCORE`", None, lambda r: r.zscore("big:zset", f"member-{mid}")),
        ("`LRANGE 0 9`", None, lambda r: r.lrange("big:list", 0, 9)),
        ("`ZRANGE 0 9`", None, lambda r: r.zrange("big:zset", 0, 9)),
        ("`ZRANGEBYSCORE` (10 members from the middle)", None, lambda r: r.zrangebyscore("big:zset", mid, mid + 9)),
        ("`XRANGE - + COUNT 10`", None, lambda r: r.xrange("big:stream", count=10)),
        ("`XREAD COUNT 10` (from the middle)", None, lambda r: r.xread({"big:stream": f"{mid}-0"}, count=10)),
    ]


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--redis-url", default="redis://localhost:6379/15", help="real server to compare with")
    parser.add_argument("--size", type=int, default=100_000, help="elements in the large collections")
    args = parser.parse_args()

    async def real() -> Any:
        client = redis.asyncio.Redis.from_url(args.redis_url)
        await client.flushdb()
        return client

    async def fake_async() -> Any:
        return fakeredis.FakeAsyncRedis(server=fakeredis.FakeServer(version=(8,)))

    async def fake_sync() -> Any:
        return SyncAdapter(fakeredis.FakeRedis(server=fakeredis.FakeServer(version=(8,))))

    async def burner() -> Any:
        if BurnerRedis is None:
            raise NotImplementedError("burner-redis is not installed")
        return BurnerRedis()

    backends: dict[str, Callable[[], Awaitable[Any]]] = {
        "Redis": real,
        "fakeredis": fake_async,
        "fakeredis (sync)": fake_sync,
    }
    if BurnerRedis is not None:
        backends["burner-redis"] = burner
    names = list(backends)

    probe = redis.Redis.from_url(args.redis_url)
    server = probe.info("server")
    probe.close()
    print(
        f"<!-- {platform.python_implementation()} {platform.python_version()}, {platform.machine()} {platform.system()}"
    )
    print(f"     redis server {server['redis_version']} at {args.redis_url}, redis-py {metadata.version('redis')}")
    burner_version = metadata.version("burner-redis") if BurnerRedis is not None else "not installed"
    print(f"     fakeredis {metadata.version('fakeredis')}, burner-redis {burner_version} -->")

    print_table("Single commands", "µs per call", 1e6, names, await run_table(backends, single_command_rows()))

    pipeline_rows: list[tuple[str, Op | None, Op]] = [
        (f"{n:,} `SET`s in one pipeline", None, lambda r, n=n: pipeline_of(r, n)) for n in (10, 100, 1000)
    ]
    results = await run_table(backends, pipeline_rows)
    for (label, row), n in zip(results.items(), (10, 100, 1000)):
        results[label] = {name: None if value is None else value / n for name, value in row.items()}
    print_table("Pipelines", "µs per command", 1e6, names, results)

    large = await run_table(backends, large_rows(args.size), fixed_n=3)
    print_table(f"Whole-collection reads, {args.size:,} elements", "ms per call", 1e3, names, large)

    async def filled(make: Callable[[], Awaitable[Any]]) -> Any:
        client = await make()
        await fill(client, args.size)
        return client

    filled_backends = {name: (lambda make=make: filled(make)) for name, make in backends.items()}
    needles = await run_table(filled_backends, needle_rows(args.size))
    print_table(f"Small reads from large collections, {args.size:,} elements", "µs per call", 1e6, names, needles)

    async def connect_and_get(make: Callable[[], Awaitable[Any]]) -> None:
        client = await make()
        await client.get("str")
        await close(client)

    server_for_new_clients = fakeredis.FakeServer(version=(8,))

    async def new_real() -> Any:
        return redis.asyncio.Redis.from_url(args.redis_url)

    async def new_fake_async() -> Any:
        return fakeredis.FakeAsyncRedis(server=server_for_new_clients)

    async def new_fake_sync() -> Any:
        return SyncAdapter(fakeredis.FakeRedis(server=server_for_new_clients))

    makers = {"Redis": new_real, "fakeredis": new_fake_async, "fakeredis (sync)": new_fake_sync}
    if BurnerRedis is not None:
        makers["burner-redis"] = burner
    row: dict[str, float | None] = {}
    for name, make in makers.items():

        async def op(_: Any, make: Callable[[], Awaitable[Any]] = make) -> None:
            await connect_and_get(make)

        row[name] = await measure(op, None)
    print_table("New client", "µs per call", 1e6, names, {"Create a client, run one `GET`, close it": row})


if __name__ == "__main__":
    asyncio.run(main())
