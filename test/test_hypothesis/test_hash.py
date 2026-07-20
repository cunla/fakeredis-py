from .base import (
    BaseTest,
    commands,
    values,
    st,
    keys,
    common_commands,
    zero_or_more,
    expires_seconds,
    expires_ms,
    fields,
    ints,
)


class TestHash(BaseTest):
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
    command_strategy_redis7 = (
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
    create_command_strategy = commands(st.just("hset"), keys, st.lists(st.tuples(fields, values), min_size=1))
    command_strategy = hash_commands | common_commands
