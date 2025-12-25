"""
This script generates the markdown files for the supported commands documentation.
"""

import json
import os
from dataclasses import dataclass

import requests

from fakeredis._commands import SUPPORTED_COMMANDS

IGNORE_COMMANDS = {
    "QUIT",
    "PUBSUB HELP",
    "FUNCTION HELP",
    "SCRIPT HELP",
    "JSON.DEBUG",
    "JSON.DEBUG HELP",
    "JSON.DEBUG MEMORY",
    "JSON.RESP",
    "XINFO",
    "XINFO HELP",
    "XGROUP",
    "XGROUP HELP",
    "XSETID",
    "ACL HELP",
    "COMMAND HELP",
    "CONFIG HELP",
    "DEBUG",
    "MEMORY HELP",
    "MODULE HELP",
    "CLIENT HELP",
    "PFDEBUG",
    "PFSELFTEST",
    "BITFIELD_RO",
    "OBJECT",
    "OBJECT HELP",
    "OBJECT IDLETIME",
    "OBJECT REFCOUNT",
    "OBJECT FREQ",
    "OBJECT ENCODING",
    "MIGRATE",
    "TOUCH",
}

THIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
markdown_filename_template = "docs/supported-commands/{}.md"


@dataclass
class CommandsMeta:
    local_filename: str
    stack: str
    url: str


METADATA = [
    CommandsMeta(
        ".commands.json",
        "Redis",
        "https://raw.githubusercontent.com/redis/docs/refs/heads/main/data/commands.json",
    ),
    CommandsMeta(
        ".json.commands.json",
        "RedisJson",
        "https://raw.githubusercontent.com/redis/docs/refs/heads/main/data/commands_redisjson.json",
    ),
    CommandsMeta(
        ".ts.commands.json",
        "RedisTimeSeries",
        "https://raw.githubusercontent.com/redis/docs/refs/heads/main/data/commands_redistimeseries.json",
    ),
    CommandsMeta(
        ".ft.commands.json",
        "RedisSearch",
        "https://raw.githubusercontent.com/redis/docs/refs/heads/main/data/commands_redisearch.json",
    ),
    CommandsMeta(
        ".bloom.commands.json",
        "RedisBloom",
        "https://raw.githubusercontent.com/redis/docs/refs/heads/main/data/commands_redisbloom.json",
    ),
]


def download_single_stack_commands(filename, url) -> dict:
    full_filename = os.path.join(THIS_DIR, filename)
    if not os.path.exists(full_filename):
        contents = requests.get(url).content
        open(full_filename, "wb").write(contents)
    curr_cmds = json.load(open(full_filename))
    cmds = {k.lower(): v for k, v in curr_cmds.items()}
    return cmds


def implemented_commands() -> set:
    res = set(SUPPORTED_COMMANDS.keys())
    if "json.type" not in res:
        raise ValueError("Make sure jsonpath_ng is installed to get accurate documentation")
    if "bf.add" not in res:
        raise ValueError("Make sure pybloom-live is installed to get accurate documentation")
    return res


def _commands_groups(commands: dict) -> dict[str, list[str]]:
    groups = {}
    for cmd in commands:
        group = commands[cmd]["group"]
        groups.setdefault(group, []).append(cmd)
    return groups


def generate_redis_commands_markdown_files(redis_commands: dict, fakeredis_commands: set[str], stack: str) -> None:
    groups = _commands_groups(redis_commands)
    for group in groups:
        filename = markdown_filename_template.format(f"{stack}/{group.upper()}")
        with open(filename, "w") as f:
            implemented_in_group = set(groups[group]).intersection(fakeredis_commands)
            implemented_in_group = sorted(implemented_in_group)
            unimplemented_in_group = set(groups[group]) - fakeredis_commands
            unimplemented_in_group = sorted(
                {cmd for cmd in unimplemented_in_group if cmd.upper() not in IGNORE_COMMANDS}
            )
            if len(implemented_in_group) > 0:
                f.write(
                    f"# {stack} `{group}` commands "
                    f"({len(implemented_in_group)}/{len(unimplemented_in_group) + len(implemented_in_group)} "
                    f"implemented)\n\n"
                )
            for cmd in implemented_in_group:
                f.write(f"## [{cmd.upper()}](https://redis.io/commands/{cmd.replace(' ', '-')}/)\n\n")
                f.write(f"{redis_commands[cmd]['summary']}\n\n")
            f.write("\n")

            if len(unimplemented_in_group) > 0:
                f.write(f"## Unsupported {group} commands \n")
                f.write("> To implement support for a command, see [here](/guides/implement-command/) \n\n")
                for cmd in unimplemented_in_group:
                    f.write(
                        f"#### [{cmd.upper()}](https://redis.io/commands/{cmd.replace(' ', '-')}/)"
                        f" <small>(not implemented)</small>\n\n"
                    )
                    f.write(f"{redis_commands[cmd]['summary']}\n\n")
            f.write("\n")


if __name__ == "__main__":
    implemented = implemented_commands()
    non_redis_commands = implemented
    for cmd_meta in METADATA:
        cmds = download_single_stack_commands(cmd_meta.local_filename, cmd_meta.url)
        generate_redis_commands_markdown_files(cmds, implemented, cmd_meta.stack)
        non_redis_commands = non_redis_commands - set(cmds.keys())
    print("Commands not in any redis stack:")
    print(non_redis_commands)
