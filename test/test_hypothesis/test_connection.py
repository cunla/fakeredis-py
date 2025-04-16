from .base import (
    BaseTest,
    commands,
    values,
    st,
    dbnums,
    common_commands,
)


class TestConnection(BaseTest):
    # TODO: tests for select
    connection_commands = commands(st.just("echo"), values) | commands(st.just("ping"), st.lists(values, max_size=2))
    command_strategy_redis_only = commands(st.just("swapdb"), dbnums, dbnums)
    command_strategy = connection_commands | common_commands
