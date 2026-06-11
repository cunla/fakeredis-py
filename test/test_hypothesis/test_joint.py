import hypothesis.strategies as st

from .test_connection import TestConnection as _TestConnection
from .test_server import TestServer as _TestServer
from .test_zset import TestZSet as _TestZSet
from .test_set import TestSet as _TestSet
from .test_list import TestList as _TestList
from .test_hash import TestHash as _TestHash
from .base import BaseTest, common_commands, commands
from .test_string import TestString as _TestString, string_commands

bad_commands = (
    # redis-py splits the command on spaces, and hangs if that ends up being an empty list
    commands(st.text().filter(lambda x: bool(x.split())), st.lists(st.binary() | st.text()))
)


class TestJoint(BaseTest):
    create_command_strategy = (
        _TestString.create_command_strategy
        | _TestHash.create_command_strategy
        | _TestList.create_command_strategy
        | _TestSet.create_command_strategy
        | _TestZSet.create_command_strategy
    )
    command_strategy = (
        _TestServer.server_commands
        | _TestConnection.connection_commands
        | string_commands
        | _TestHash.hash_commands
        | _TestList.list_commands
        | _TestSet.set_commands
        | _TestZSet.zset_commands
        | common_commands
        | bad_commands
    )
