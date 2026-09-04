import pytest

from .base import (
    BaseMachine,
    commands,
    expires_ms,
    expires_seconds,
    fields,
    ints,
    keys,
    run_machine,
    st,
    values,
    zero_or_more,
)

hash_commands = (
    commands(st.just("hset"), keys, st.lists(st.tuples(fields, values)))
    | commands(st.just("hdel"), keys, st.lists(fields))
    | commands(st.just("hexists"), keys, fields)
    | commands(st.just("hget"), keys, fields)
    | commands(st.sampled_from(["hgetall", "hkeys", "hvals"]), keys)
    | commands(st.just("hincrby"), keys, fields, ints)
    | commands(st.just("hlen"), keys)
    | commands(st.just("hmget"), keys, st.lists(fields))
    | commands(st.just("hset"), keys, st.lists(st.tuples(fields, values)))
    | commands(st.just("hsetnx"), keys, fields, values)
    | commands(st.just("hstrlen"), keys, fields)
    | commands(
        st.just("hpersist"),
        st.just("fields"),
        st.just(2),
        st.lists(fields, min_size=2, max_size=2),
    )
    | commands(
        st.just("hexpire"),
        keys,
        expires_seconds,
        st.just("fields"),
        st.just(2),
        st.lists(fields, min_size=2, max_size=2, unique=True),
    )
)

hash_commands_redis7 = (
    commands(st.just("hpersist"), st.just("fields"), st.just(2), st.lists(fields, min_size=2, max_size=2))
    | commands(st.just("hexpiretime"), st.just("fields"), st.just(2), st.lists(fields, min_size=2, max_size=2))
    | commands(st.just("hpexpiretime"), st.just("fields"), st.just(2), st.lists(fields, min_size=2, max_size=2))
    | commands(
        st.just("hexpire"),
        keys,
        expires_seconds,
        *zero_or_more("nx", "xx", "gt", "lt"),
        st.just("fields"),
        st.just(2),
        st.lists(fields, min_size=2, max_size=2, unique=True),
    )
    | commands(
        st.just("hpexpire"),
        keys,
        expires_ms,
        *zero_or_more("nx", "xx", "gt", "lt"),
        st.just("fields"),
        st.just(2),
        st.lists(fields, min_size=2, max_size=2, unique=True),
    )
)


class HashMachine(BaseMachine):
    base_commands = hash_commands
    redis7_commands = hash_commands_redis7
    create_commands = commands(st.just("hset"), keys, st.lists(st.tuples(fields, values), min_size=1))


@pytest.mark.slow
def test_hash(hypothesis_config):
    run_machine(HashMachine, hypothesis_config)
