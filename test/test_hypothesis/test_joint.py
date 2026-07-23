import pytest

from .base import BaseMachine, commands, run_machine, st
from .test_connection import connection_commands
from .test_hash import HashMachine, hash_commands
from .test_list import ListMachine, list_commands
from .test_server import server_commands
from .test_set import SetMachine, set_commands
from .test_string import StringMachine, string_commands
from .test_zset import ZSetMachine, zset_commands

bad_commands = (
    # redis-py splits the command on spaces, and hangs if that ends up being an empty list
    commands(st.text().filter(lambda x: bool(x.split())), st.lists(st.binary() | st.text()))
)


class JointMachine(BaseMachine):
    base_commands = (
        server_commands
        | connection_commands
        | string_commands
        | hash_commands
        | list_commands
        | set_commands
        | zset_commands
        | bad_commands
    )
    create_commands = (
        StringMachine.create_commands
        | HashMachine.create_commands
        | ListMachine.create_commands
        | SetMachine.create_commands
        | ZSetMachine.create_commands
    )


@pytest.mark.slow
def test_joint(hypothesis_config):
    run_machine(JointMachine, hypothesis_config)
