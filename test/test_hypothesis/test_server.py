from test.test_hypothesis.base import BaseTest, commands, st, common_commands
from test.test_hypothesis.test_string import TestString


class TestServer(BaseTest):
    # TODO: real redis raises an error if there is a save already in progress.
    #  Find a better way to test this. commands(st.just('bgsave'))
    server_commands = (
        commands(st.just("dbsize"))
        | commands(st.sampled_from(["flushdb", "flushall"]), st.sampled_from([[], "async"]))
        # TODO: result is non-deterministic
        # | commands(st.just('lastsave'))
        | commands(st.just("save"))
    )
    create_command_strategy = TestString.create_command_strategy
    command_strategy = server_commands | TestString.string_commands | common_commands
