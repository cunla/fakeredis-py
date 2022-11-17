"""Tests for `fakeredis-py`'s emulation of Redis's JSON command subset."""

# Future Imports
from __future__ import annotations

# Standard Library Imports
import json
from contextlib import contextmanager
from itertools import (
    chain,
    count,
    takewhile,
)
from random import (
    choices,
    shuffle,
)
from typing import (
    Any,
    Generator,
    List,
    TypeVar,
)

# Third-Party Imports
import fakeredis  # noqa: F401
import pytest
import redis
import testtools

# <editor-fold desc="Constants ...">

cache_key: str = "roundtrip-json"
RoundTripValue = TypeVar("RoundTripValue")

# </editor-fold desc="Constants ...">

# <editor-fold desc="Utility Functions ...">


def frange(
    start: float,
    stop: float,
    step: float = 1.0,
) -> Generator[float, None, None]:
    """A range of float values."""
    yield from takewhile(
        lambda value: value <= stop,
        count(start, step),
    )


def populate_cache(
    redis_client: redis.Redis,
    value: Any,
) -> bool:
    """Insert the supplied value into the emulated cache as a `sorted set`."""
    if not isinstance(value, bytes):
        value = json.dumps(value)

    if isinstance(value, str):
        value = value.encode()

    testtools.raw_command(
        redis_client,
        "JSON.SET",
        cache_key,
        "$",
        value,
    )

    key_type = redis_client.type(cache_key)

    return key_type != b"none"


def wipe_cache(redis_client: redis.Redis) -> bool:
    """Wipe the values inserted into the emulated cache by the previous test
    before proceeding with the next one."""
    redis_client.delete(cache_key)
    return redis_client.type(cache_key) == b"none"


@contextmanager
def scoped_redis_client(
    redis_client: redis.Redis,
) -> Generator[redis.Redis, None, None]:
    """Automatically wipe the cache in between tests."""
    assert wipe_cache(redis_client)

    yield redis_client

    assert wipe_cache(redis_client)


def round_trip(r: redis.Redis, value: RoundTripValue) -> RoundTripValue:
    """Call `JSON.SET` with the supplied value and return the unaltered value
    from calling `JSON.GET`."""

    redis_client: redis.Redis

    with scoped_redis_client(r) as redis_client:
        if not populate_cache(redis_client, value):
            return ValueError

        cached_value = redis_client.json().get(cache_key)

    return cached_value


def scalar_round_trip(
    r: redis.Redis,
    values: List[RoundTripValue],
) -> List[RoundTripValue]:
    """Call `JSON.SET` with the supplied values and return the unaltered values
    from calling `JSON.GET`."""
    return [round_trip(r, value) for value in values]


# </editor-fold desc="Utility Functions ...">


@pytest.mark.descriptor
def describe_roundtrip() -> None:
    """Test that `fakeredis-py` maintains `redis-py`'s basic contract(s) for
    round-trip value storage and retrieval."""

    float_values = [round(val, 5) for val in frange(-10, 11, 1.1)]
    string_values = ["one", "two", "three", "four", "five", "six", "seven"]
    integer_values = list(map(int, float_values))

    scalar_pool = list(chain(float_values, string_values, integer_values))
    shuffle(scalar_pool)

    @pytest.mark.description
    def with_integer_values(r: redis.Redis) -> None:
        """Test that simple integers are reliably stored and retrieved."""
        assert scalar_round_trip(r, integer_values) == integer_values

    @pytest.mark.description
    def with_float_values(r: redis.Redis) -> None:
        """Test that floating point values are reliably stored and
        retrieved."""
        assert scalar_round_trip(r, float_values) == float_values

    @pytest.mark.description
    def with_string_values(r: redis.Redis) -> None:
        """Test that simple strings are reliably stored and retrieved."""
        assert scalar_round_trip(r, string_values) == string_values

    @pytest.mark.description
    def with_list_of_scalar_values(r: redis.Redis) -> None:
        """Test that lists of scalar values are reliably stored and
        retrieved."""
        list_values = choices(
            scalar_pool,
            k=len(scalar_pool) // 3,
        )
        assert round_trip(r, list_values) == list_values

    @pytest.mark.description
    def with_nested_lists(r: redis.Redis) -> None:
        """Test that lists of lists of scalar values are reliably stored and
        retrieved."""
        value_lists = [
            choices(
                scalar_pool,
                k=len(scalar_pool) // 3,
            )
            for _ in range(3)
        ]
        assert round_trip(r, value_lists) == value_lists

    @pytest.mark.description
    def with_mapping_of_scalar_values(r: redis.Redis) -> None:
        """Test that key-value mappings whose keys and values are all scalar
        values are reliably stored and retrieved."""
        value = dict(
            zip(
                string_values,
                choices(integer_values, k=len(string_values)),
            )
        )
        assert round_trip(r, value) == value

    @pytest.mark.description
    def with_mapping_of_scalar_lists(r: redis.Redis) -> None:
        """Test that key-value mappings whose keys are all scalar values and
        whose values are all lists of scalar values are reliably stored and
        retrieved."""
        value = {
            key: choices(
                scalar_pool,
                k=len(scalar_pool) // 3,
            )
            for key in string_values
        }
        assert round_trip(r, value) == value

    @pytest.mark.description
    def with_nested_mappings(r: redis.Redis) -> None:
        """Test that complex key-value mappings are reliably stored and
        retrieved."""
        value = {
            key: {
                key: choices(
                    scalar_pool,
                    k=len(scalar_pool) // 3,
                )
                for key in string_values
            }
            for key in string_values
        }
        assert round_trip(r, value) == value


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_del() -> None:
    """Test that the `json_del` method of `fakeredis-py`'s `JSONCommandsMixin`
    class exhibits behavioral parity with a real Redis server."""

    @pytest.mark.description
    def with_no_sub_path(r: redis.Redis) -> None:
        """When no explicit sub-path is specified, the specified key should be
        deleted entirely."""
        raise NotImplementedError

    @pytest.mark.description
    def with_sub_path(r: redis.Redis) -> None:
        """When a path is specified, the value of specified key should be
        altered to remove the value at the supplied sub-path and written back
        to the cache."""
        raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_get() -> None:
    """Test that the `json_get` method of `fakeredis-py`'s `JSONCommandsMixin`
    class exhibits behavioral parity with a real Redis server."""

    @pytest.mark.description
    def with_bad_key(r: redis.Redis) -> None:
        """When a key is specified but does not exist in the cache, a `nil`
        value should be returned (identical to the Redis default `GET`
        behavior)."""
        raise NotImplementedError

    @pytest.mark.description
    def with_no_sub_path(r: redis.Redis) -> None:
        """When no explicit sub-path is specified, the value of the specified
        key should be retrieved in its entirety."""
        raise NotImplementedError

    @pytest.mark.description
    def with_bad_sub_path(r: redis.Redis) -> None:
        """When a sub-path is specified that doesn't exist, a `nil` value
        should be returned."""
        raise NotImplementedError

    @pytest.mark.description
    def with_good_sub_path(r: redis.Redis) -> None:
        """When a sub-path is specified that exists within the cached JSON
        object, only the sub-value of should be returned."""
        raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_set() -> None:
    """Test that the `json_set` method of `fakeredis-py`'s `JSONCommandsMixin`
    class exhibits behavioral parity with a real Redis server."""

    @pytest.mark.description
    def with_no_sub_path(r: redis.Redis) -> None:
        """..."""
        raise NotImplementedError

    @pytest.mark.description
    def with_bad_sub_path(r: redis.Redis) -> None:
        """..."""
        raise NotImplementedError

    @pytest.mark.description
    def with_good_sub_path(r: redis.Redis) -> None:
        """..."""
        raise NotImplementedError

    @pytest.mark.description
    def with_both_xx_and_nx_flags(r: redis.Redis) -> None:
        """..."""
        raise NotImplementedError

    @pytest.mark.description
    def with_nx_flag_and_cached_value(r: redis.Redis) -> None:
        """..."""
        raise NotImplementedError

    @pytest.mark.description
    def with_nx_flag_and_missing_value(r: redis.Redis) -> None:
        """..."""
        raise NotImplementedError

    @pytest.mark.description
    def with_xx_flag_and_cached_value(r: redis.Redis) -> None:
        """..."""
        raise NotImplementedError

    @pytest.mark.description
    def with_xx_flag_and_missing_value(r: redis.Redis) -> None:
        """..."""
        raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_mget() -> None:
    """Test that the `json_mget` method of `fakeredis-py`'s `JSONCommandsMixin`
    class exhibits behavioral parity with a real Redis server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_resp() -> None:
    """Test that the `json_resp` method of `fakeredis-py`'s `JSONCommandsMixin`
    class exhibits behavioral parity with a real Redis server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_type() -> None:
    """Test that the `json_type` method of `fakeredis-py`'s `JSONCommandsMixin`
    class exhibits behavioral parity with a real Redis server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_clear() -> None:
    """Test that the `json_clear` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_debug() -> None:
    """Test that the `json_debug` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_arrlen() -> None:
    """Test that the `json_arrlen` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_arrpop() -> None:
    """Test that the `json_arrpop` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_forget() -> None:
    """Test that the `json_forget` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_objlen() -> None:
    """Test that the `json_objlen` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_strlen() -> None:
    """Test that the `json_strlen` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_toggle() -> None:
    """Test that the `json_toggle` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_arrtrim() -> None:
    """Test that the `json_arrtrim` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_objkeys() -> None:
    """Test that the `json_objkeys` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_arrindex() -> None:
    """Test that the `json_arrindex` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_arrappend() -> None:
    """Test that the `json_arrappend` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_arrinsert() -> None:
    """Test that the `json_arrinsert` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_numincrby() -> None:
    """Test that the `json_numincrby` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_nummultby() -> None:
    """Test that the `json_nummultby` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError


@pytest.mark.xfail
@pytest.mark.descriptor
def describe_json_strappend() -> None:
    """Test that the `json_strappend` method of `fakeredis-py`'s
    `JSONCommandsMixin` class exhibits behavioral parity with a real Redis
    server."""
    raise NotImplementedError
