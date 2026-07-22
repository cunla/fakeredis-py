import pytest

from .base import BaseMachine, commands, keys, run_machine, st, values
from .test_string import string_commands

# TODO: real redis raises an error if there is a save already in progress.
#  Find a better way to test this. commands(st.just('bgsave'))
server_commands = (
    commands(st.just("dbsize"))
    | commands(st.sampled_from(["flushdb", "flushall"]))
    # TODO: result is non-deterministic
    # | commands(st.just('lastsave'))
    | commands(st.just("save"))
)


class ServerMachine(BaseMachine):
    base_commands = server_commands | string_commands
    redis_only_commands = commands(st.sampled_from(["flushdb", "flushall"]), st.sampled_from([[], "async"]))
    create_commands = commands(st.just("set"), keys, values)


@pytest.mark.slow
def test_server(hypothesis_config):
    run_machine(ServerMachine, hypothesis_config)
