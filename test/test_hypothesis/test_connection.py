from .base import (
    BaseTest,
    commands,
    values,
    st,
    dbnums,
    keys,
    common_commands,
    counts,
    zero_or_more,
    expires_seconds,
    expires_ms,
)


class TestConnection(BaseTest):
    # TODO: tests for select
    connection_commands = (
        commands(st.just("echo"), values)
        | commands(st.just("ping"), st.lists(values, max_size=2))
        | commands(st.just("swapdb"), dbnums, dbnums)
    )
    command_strategy = connection_commands | common_commands
