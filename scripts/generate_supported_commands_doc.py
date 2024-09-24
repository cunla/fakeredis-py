"""
This script generates the markdown files for the supported commands documentation.
"""

import json
import os
from dataclasses import dataclass

import requests

from fakeredis._commands import SUPPORTED_COMMANDS

IGNORE_COMMANDS = {
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


@dataclass
class CommandsMeta:
    local_filename: str
    stack: str
    title: str
    url: str


METADATA = [
    CommandsMeta(
        ".commands.json",
        "Redis",
        "Redis",
        "https://raw.githubusercontent.com/redis/docs/refs/heads/main/data/commands.json",
    ),
    CommandsMeta(
        ".json.commands.json",
        "RedisJson",
        "JSON",
        "https://raw.githubusercontent.com/RedisJSON/RedisJSON/master/commands.json",
    ),
    CommandsMeta(
        ".ts.commands.json",
        "RedisTimeSeries",
        "Time Series",
        "https://raw.githubusercontent.com/RedisTimeSeries/RedisTimeSeries/master/commands.json",
    ),
    CommandsMeta(
        ".ft.commands.json",
        "RedisSearch",
        "Search",
        "https://raw.githubusercontent.com/RediSearch/RediSearch/master/commands.json",
    ),
    CommandsMeta(
        ".bloom.commands.json",
        "RedisBloom",
        "Probabilistic",
        "https://raw.githubusercontent.com/RedisBloom/RedisBloom/master/commands.json",
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
    groups = dict()
    for cmd in commands:
        group = commands[cmd]["group"]
        groups.setdefault(group, []).append(cmd)
    return groups


markdown_filename_template = "docs/redis-commands/{}.md"


def generate_markdown_files(commands: dict, implemented_commands: set[str], stack: str) -> None:
    groups = _commands_groups(commands)
    for group in groups:
        filename = markdown_filename_template.format(f"{stack}/{group.upper()}")
        f = open(filename, "w")
        implemented_in_group = list(filter(lambda cmd: cmd in implemented_commands, groups[group]))
        unimplemented_in_group = list(
            filter(lambda cmd: cmd not in implemented_commands and cmd.upper() not in IGNORE_COMMANDS, groups[group])
        )
        if len(implemented_in_group) > 0:
            f.write(
                f"# `{group}` commands "
                f"({len(implemented_in_group)}/{len(unimplemented_in_group) + len(implemented_in_group)} "
                f"implemented)\n\n"
            )
        for cmd in implemented_in_group:
            f.write(f"## [{cmd.upper()}](https://redis.io/commands/{cmd.replace(' ', '-')}/)\n\n")
            f.write(f"{commands[cmd]['summary']}\n\n")
        f.write("\n")

        if len(unimplemented_in_group) > 0:
            f.write(f"## Unsupported {group} commands \n")
            f.write("> To implement support for a command, see [here](/guides/implement-command/) \n\n")
            for cmd in unimplemented_in_group:
                f.write(
                    f"#### [{cmd.upper()}](https://redis.io/commands/{cmd.replace(' ', '-')}/)"
                    f" <small>(not implemented)</small>\n\n"
                )
                f.write(f"{commands[cmd]['summary']}\n\n")
        f.write("\n")


if __name__ == "__main__":
    implemented = implemented_commands()
    for cmd_meta in METADATA:
        cmds = download_single_stack_commands(cmd_meta.local_filename, cmd_meta.url)
        markdown_filename = f"docs/redis-commands/{cmd_meta.stack}.md"
        generate_markdown_files(cmds, implemented, cmd_meta.title)
