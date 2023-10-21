import json
import os
from collections import namedtuple
from typing import Any, List, Dict

import requests

from fakeredis._commands import SUPPORTED_COMMANDS

THIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
CommandsMeta = namedtuple('CommandsMeta', ['local_filename', 'stack', 'title', 'url', ])
METADATA = [
    CommandsMeta('.commands.json', 'Redis', 'Redis',
                 'https://raw.githubusercontent.com/redis/redis-doc/master/commands.json', ),
    CommandsMeta('.json.commands.json', 'RedisJson', 'JSON',
                 'https://raw.githubusercontent.com/RedisJSON/RedisJSON/master/commands.json', ),
    CommandsMeta('.graph.commands.json', 'RedisGraph', 'Graph',
                 'https://raw.githubusercontent.com/RedisGraph/RedisGraph/master/commands.json', ),
    CommandsMeta('.ts.commands.json', 'RedisTimeSeries', 'Time Series',
                 'https://raw.githubusercontent.com/RedisTimeSeries/RedisTimeSeries/master/commands.json', ),
    CommandsMeta('.ft.commands.json', 'RedisSearch', 'Search',
                 'https://raw.githubusercontent.com/RediSearch/RediSearch/master/commands.json', ),
    CommandsMeta('.bloom.commands.json', 'RedisBloom', 'Probabilistic',
                 'https://raw.githubusercontent.com/RedisBloom/RedisBloom/master/commands.json', ),
]


def download_single_stack_commands(filename, url) -> dict:
    full_filename = os.path.join(THIS_DIR, filename)
    if not os.path.exists(full_filename):
        contents = requests.get(url).content
        open(full_filename, 'wb').write(contents)
    curr_cmds = json.load(open(full_filename))
    cmds = {k.lower(): v for k, v in curr_cmds.items()}
    return cmds


def implemented_commands() -> set:
    res = set(SUPPORTED_COMMANDS.keys())
    if 'json.type' not in res:
        raise ValueError('Make sure jsonpath_ng is installed to get accurate documentation')
    return res


def dict_deep_get(d: Dict[Any, Any], *keys, default_value: Any = None) -> Any:
    res = d
    for key in keys:
        if isinstance(res, list) and isinstance(key, int):
            res = res[key]
        else:
            res = res.get(key, None)
        if res is None:
            return default_value
    return default_value if res is None else res


def key_specs_array(cmd_info: Dict[str, Any]) -> List[Any]:
    return []


def get_command_info(cmd_name: str, cmd_info: Dict[str, Any]) -> List[Any]:
    """Returns a list
     1 Name //
     2 Arity //
     3 Flags //
     4 First key //
     5 Last key //
     6 Step //
     7 ACL categories (as of Redis 6.0) //
     8 Tips (as of Redis 7.0) //
     9 Key specifications (as of Redis 7.0)
    10 Subcommands (as of Redis 7.0)
    """
    first_key = dict_deep_get(cmd_info, 'key_specs', 0, 'begin_search', 'spec', 'index', default_value=0)
    last_key = dict_deep_get(cmd_info, 'key_specs', -1, 'begin_search', 'spec', 'index', default_value=0)
    step = dict_deep_get(cmd_info, 'key_specs', 0, 'find_keys', 'spec', 'keystep', default_value=0)
    tips = []  # todo
    subcommands = []  # todo
    res = [
        cmd_name.lower(),
        cmd_info.get("arity", -1),
        cmd_info.get("command_flags", []),
        first_key,
        last_key,
        step,
        cmd_info.get("acl_categories", []),
        tips,
        key_specs_array(cmd_info),
        subcommands,
    ]
    return res


if __name__ == '__main__':
    implemented = implemented_commands()
    command_info_dict: Dict[str, List[Any]] = dict()
    for cmd_meta in METADATA:
        cmds = download_single_stack_commands(cmd_meta.local_filename, cmd_meta.url)
        for cmd in cmds:
            if cmd not in implemented:
                continue
            command_info_dict[cmd] = get_command_info(cmd, cmds[cmd])
            print(command_info_dict[cmd])
    with open(os.path.join(os.path.dirname(__file__), '..', 'fakeredis', 'commands.json'), 'w') as f:
        json.dump(command_info_dict, f)
