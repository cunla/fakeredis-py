import pytest

from .base import BaseMachine, commands, dbnums, run_machine, st, values

connection_commands = (
    commands(st.just("echo"), values)
    | commands(st.just("ping"), st.lists(values, max_size=2))
    | commands(st.just("select"), dbnums)
)


class ConnectionMachine(BaseMachine):
    base_commands = connection_commands
    redis_only_commands = commands(st.just("swapdb"), dbnums, dbnums)


@pytest.mark.slow
def test_connection(hypothesis_config):
    run_machine(ConnectionMachine, hypothesis_config)
