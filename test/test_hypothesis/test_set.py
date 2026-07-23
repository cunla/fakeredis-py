import pytest

from .base import BaseMachine, commands, fields, keys, run_machine, st

set_commands = (
    commands(st.just("sadd"), keys, st.lists(fields))
    | commands(st.just("scard"), keys)
    | commands(st.sampled_from(["sdiff", "sinter", "sunion"]), st.lists(keys))
    | commands(st.sampled_from(["sdiffstore", "sinterstore", "sunionstore"]), keys, st.lists(keys))
    | commands(st.just("sismember"), keys, fields)
    | commands(st.just("smembers"), keys)
    | commands(st.just("smove"), keys, keys, fields)
    | commands(st.just("srem"), keys, st.lists(fields))
)


class SetMachine(BaseMachine):
    # TODO:
    # - find a way to test srandmember, spop which are random
    # - sscan
    base_commands = set_commands
    create_commands = commands(st.just("sadd"), keys, st.lists(fields, min_size=1))


@pytest.mark.slow
def test_set(hypothesis_config):
    run_machine(SetMachine, hypothesis_config)
