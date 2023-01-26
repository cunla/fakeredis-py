import json
import os
import requests

from fakeredis._commands import SUPPORTED_COMMANDS

THIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
COMMAND_FILES = [
    ('.commands.json', 'https://raw.githubusercontent.com/redis/redis-doc/master/commands.json'),
    ('.json.commands.json', 'https://raw.githubusercontent.com/RedisJSON/RedisJSON/master/commands.json'),
    ('.graph.commands.json', 'https://raw.githubusercontent.com/RedisGraph/RedisGraph/master/commands.json'),
    ('.ts.commands.json', 'https://raw.githubusercontent.com/RedisTimeSeries/RedisTimeSeries/master/commands.json'),
    ('.ft.commands.json', 'https://raw.githubusercontent.com/RediSearch/RediSearch/master/commands.json'),
    ('.bloom.commands.json', 'https://raw.githubusercontent.com/RedisBloom/RedisBloom/master/commands.json'),
]

TARGET_FILES = {
    'unimplemented': 'docs/redis-commands/unimplemented_commands.md',
    'implemented': 'docs/redis-commands/implemented_commands.md',
}


def download_redis_commands() -> dict:
    cmds = {}
    for filename, url in COMMAND_FILES:
        full_filename = os.path.join(THIS_DIR, filename)
        if not os.path.exists(full_filename):
            contents = requests.get(url).content
            open(full_filename, 'wb').write(contents)
        curr_cmds = json.load(open(full_filename))
        cmds = cmds | {k.lower(): v for k, v in curr_cmds.items()}
    return cmds


def implemented_commands() -> set:
    res = set(SUPPORTED_COMMANDS.keys())
    if 'json.get' not in res:
        raise ValueError('Make sure jsonpath_ng is installed to get accurate documenentation')
    return res


def commands_groups(
        all_commands: dict, implemented_set: set
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    implemented, unimplemented = dict(), dict()
    for cmd in all_commands:
        group = all_commands[cmd]['group']
        if cmd in implemented_set:
            implemented.setdefault(group, []).append(cmd)
        else:
            unimplemented.setdefault(group, []).append(cmd)
    return implemented, unimplemented


def generate_markdown_files(
        all_commands: dict,
        unimplemented: dict,
        implemented: dict) -> None:
    def print_groups(dictionary: dict, f):
        for group in dictionary:
            f.write(f'## {group} commands\n\n')
            for cmd in dictionary[group]:
                f.write(f"### [{cmd.upper()}](https://redis.io/commands/{cmd.replace(' ', '-')}/)\n\n")
                f.write(f"{all_commands[cmd]['summary']}\n\n")
            f.write("\n")

    supported_commands_file = open(TARGET_FILES['implemented'], 'w')
    supported_commands_file.write("""# Supported commands

Here is a list of all redis [implemented commands](#implemented-commands) and a
list of [unimplemented commands](#unimplemented-commands).

------\n\n
""")
    print_groups(implemented, supported_commands_file)

    unimplemented_cmds_file = open(TARGET_FILES['unimplemented'], 'w')
    unimplemented_cmds_file.write("""# Unimplemented Commands
All the redis commands are implemented in fakeredis with these exceptions:\n\n""")
    print_groups(unimplemented, unimplemented_cmds_file)


def get_unimplemented_and_implemented_commands() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Returns 2 dictionaries, one of unimplemented commands and another of implemented commands

    """
    commands = download_redis_commands()
    implemented_commands_set = implemented_commands()
    implemented_dict, unimplemented_dict = commands_groups(commands, implemented_commands_set)
    return unimplemented_dict, implemented_dict


if __name__ == '__main__':
    commands = download_redis_commands()
    unimplemented_dict, implemented_dict = get_unimplemented_and_implemented_commands()
    generate_markdown_files(commands, unimplemented_dict, implemented_dict)
