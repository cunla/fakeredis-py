import pytest

from .base import BaseMachine, commands, keys, run_machine, server_type, st, values
from .test_string import string_commands

# Dragonfly's SAVE returns before the snapshot is finished, so a SAVE that follows one too
# closely is refused with "SAVING - can not save database" -- which nothing on the machine's
# side can predict. Redis saves synchronously and has no such window.
save_commands = st.deferred(lambda: st.nothing() if server_type() == "dragonfly" else commands(st.just("save")))

# TODO: real redis raises an error if there is a save already in progress.
#  Find a better way to test this. commands(st.just('bgsave'))
server_commands = (
    commands(st.just("dbsize"))
    | commands(st.sampled_from(["flushdb", "flushall"]))
    # TODO: result is non-deterministic
    # | commands(st.just('lastsave'))
    | save_commands
)


class ServerMachine(BaseMachine):
    base_commands = server_commands | string_commands
    redis_only_commands = commands(st.sampled_from(["flushdb", "flushall"]), st.sampled_from([[], "async"]))
    create_commands = commands(st.just("set"), keys, values)


@pytest.mark.slow
def test_server(hypothesis_config):
    run_machine(ServerMachine, hypothesis_config)
