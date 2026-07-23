import pytest

from .base import (
    BaseMachine,
    Command,
    commands,
    counts,
    fields,
    float_as_bytes,
    keys,
    optional,
    run_machine,
    scores,
    st,
    string_tests,
    zero_or_more,
)

# A negative LIMIT offset is undefined behaviour in Redis (it reads out of
# bounds, so the result depends on leftover internal state), so keep the offset
# non-negative. A negative count is well-defined and means "unlimited".
limit_offsets = st.integers(min_value=0, max_value=3) | st.integers(min_value=0, max_value=2_147_483_647)
limits = st.just(()) | st.tuples(st.just("limit"), limit_offsets, counts)
score_tests = scores | st.builds(lambda x: b"(" + repr(x).encode(), scores)
zset_no_score_create_commands = commands(st.just("zadd"), keys, st.lists(st.tuples(st.just(0), fields), min_size=1))
zset_no_score_commands = (  # TODO: test incr
    commands(
        st.just("zadd"),
        keys,
        *zero_or_more("nx", "xx", "ch", "incr"),
        st.lists(st.tuples(st.just(0), fields)),
    )
    | commands(st.just("zlexcount"), keys, string_tests, string_tests)
    | commands(st.sampled_from(["zrangebylex", "zrevrangebylex"]), keys, string_tests, string_tests, limits)
    | commands(st.just("zremrangebylex"), keys, string_tests, string_tests)
)


def build_zstore(command, dest, sources, weights, aggregate) -> Command:
    args = [command, dest, len(sources)]
    args += [source[0] for source in sources]
    if weights:
        args.append("weights")
        args += [source[1] for source in sources]
    if aggregate:
        args += ["aggregate", aggregate]
    return Command(args)


zset_commands = (
    commands(
        st.just("zadd"),
        keys,
        *zero_or_more("nx", "xx", "ch", "incr"),
        st.lists(st.tuples(scores, fields)),
    )
    | commands(st.just("zcard"), keys)
    | commands(st.just("zcount"), keys, score_tests, score_tests)
    | commands(st.just("zincrby"), keys, scores, fields)
    | commands(st.sampled_from(["zrange", "zrevrange"]), keys, counts, counts, optional("withscores"))
    | commands(
        st.sampled_from(["zrangebyscore", "zrevrangebyscore"]),
        keys,
        score_tests,
        score_tests,
        limits,
        optional("withscores"),
    )
    | commands(st.sampled_from(["zrank", "zrevrank"]), keys, fields)
    | commands(st.just("zrem"), keys, st.lists(fields))
    | commands(st.just("zremrangebyrank"), keys, counts, counts)
    | commands(st.just("zremrangebyscore"), keys, score_tests, score_tests)
    | commands(st.just("zscore"), keys, fields)
    | commands(st.sampled_from(["zpopmin", "zpopmax"]), keys, st.none() | counts)
    | st.builds(
        build_zstore,
        command=st.sampled_from(["zunionstore", "zinterstore"]),
        dest=keys,
        sources=st.lists(st.tuples(keys, float_as_bytes)),
        weights=st.booleans(),
        aggregate=st.sampled_from([None, "sum", "min", "max"]),
    )
)


class ZSetMachine(BaseMachine):
    # TODO: zscan, bzpopmin/bzpopmax, probably more
    base_commands = zset_commands
    create_commands = commands(st.just("zadd"), keys, st.lists(st.tuples(scores, fields), min_size=1))


class ZSetNoScoresMachine(BaseMachine):
    base_commands = zset_no_score_commands
    create_commands = zset_no_score_create_commands


@pytest.mark.slow
def test_zset(hypothesis_config):
    run_machine(ZSetMachine, hypothesis_config)


@pytest.mark.slow
def test_zset_no_scores(hypothesis_config):
    run_machine(ZSetNoScoresMachine, hypothesis_config)
