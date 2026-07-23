import pytest

from .base import BaseMachine, commands, counts, ints, keys, run_machine, st, values

# TODO: blocking commands
list_commands = (
    commands(st.just("lindex"), keys, counts)
    | commands(
        st.just("linsert"),
        keys,
        st.sampled_from(["before", "after", "BEFORE", "AFTER"]) | st.binary(),
        values,
        values,
    )
    | commands(st.just("llen"), keys)
    | commands(st.sampled_from(["lpop", "rpop"]), keys, st.just(None) | st.just([]) | ints)
    | commands(st.sampled_from(["lpush", "lpushx", "rpush", "rpushx"]), keys, st.lists(values))
    | commands(st.just("lrange"), keys, counts, counts)
    | commands(st.just("lrem"), keys, counts, values)
    | commands(st.just("lset"), keys, counts, values)
    | commands(st.just("ltrim"), keys, counts, counts)
    | commands(st.just("rpoplpush"), keys, keys)
)


class ListMachine(BaseMachine):
    base_commands = list_commands
    create_commands = commands(st.just("rpush"), keys, st.lists(values, min_size=1))


@pytest.mark.slow
def test_list(hypothesis_config):
    run_machine(ListMachine, hypothesis_config)
