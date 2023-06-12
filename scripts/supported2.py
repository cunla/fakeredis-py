import json
import os
from collections import namedtuple

import requests

from create_issues import IGNORE_COMMANDS
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


def _commands_groups(commands: dict) -> dict[str, list[str]]:
    groups = dict()
    for cmd in commands:
        group = commands[cmd]['group']
        groups.setdefault(group, []).append(cmd)
    return groups


def generate_markdown_files(commands: dict, implemented_commands: set[str], stack: str, filename: str) -> None:
    groups = _commands_groups(commands)
    f = open(filename, 'w')
    f.write(f'# {stack} commands\n\n')
    implemeted_count = 0
    for group in groups:
        implemeted_count = list(map(lambda cmd: cmd in implemented_commands, groups[group])).count(True)
        if implemeted_count > 0:
            break
    if implemeted_count == 0:
        f.write('Module currently not implemented in fakeredis.\n\n')
    for group in groups:
        implemented_in_group = list(filter(lambda cmd: cmd in implemented_commands, groups[group]))
        if len(implemented_in_group) > 0:
            f.write(f'## {group} commands\n\n')
        for cmd in implemented_in_group:
            f.write(f"### [{cmd.upper()}](https://redis.io/commands/{cmd.replace(' ', '-')}/)\n\n")
            f.write(f"{commands[cmd]['summary']}\n\n")
        f.write("\n")
        unimplemented_in_group = list(filter(
            lambda cmd: cmd not in implemented_commands and cmd.upper() not in IGNORE_COMMANDS, groups[group]))
        if len(unimplemented_in_group) > 0:
            f.write(f'### Unsupported {group} commands \n')
            f.write('> To implement support for a command, see [here](../../guides/implement-command/) \n\n')
            for cmd in unimplemented_in_group:
                f.write(f"#### [{cmd.upper()}](https://redis.io/commands/{cmd.replace(' ', '-')}/)"
                        f" <small>(not implemented)</small>\n\n")
                f.write(f"{commands[cmd]['summary']}\n\n")
        f.write("\n")


if __name__ == '__main__':
    implemented = implemented_commands()
    for cmd_meta in METADATA:
        cmds = download_single_stack_commands(cmd_meta.local_filename, cmd_meta.url)
        markdown_filename = f'docs/redis-commands/{cmd_meta.stack}.md'
        generate_markdown_files(cmds, implemented, cmd_meta.title, markdown_filename)
