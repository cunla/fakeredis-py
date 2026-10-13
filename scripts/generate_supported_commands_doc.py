"""
This script generates the markdown files for the supported commands documentation.
"""

from __future__ import annotations

import json
import os
import re

import requests
import yaml

from fakeredis._commands import SUPPORTED_COMMANDS

IGNORE_COMMANDS = {
    "QUIT",
    "PUBSUB HELP",
    "FUNCTION HELP",
    "SCRIPT HELP",
    "JSON.DEBUG",
    "BF.DEBUG",
    "CF.DEBUG",
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

COMMANDS_URL = "https://raw.githubusercontent.com/redis/docs/refs/heads/main/data/commands.json"
COMMANDS_LOCAL_FILENAME = ".commands.json"
# Commands missing from commands.json, read from their markdown page instead
MARKDOWN_COMMANDS: list[str] = []


# The `module` field of a command in commands.json (core commands have none) => docs/supported-commands/ sub-directory
MODULE_STACKS = {
    None: "Redis",
    "ReJSON": "RedisJson",
    "timeseries": "RedisTimeSeries",
    "search": "RedisSearch",
    "bf": "RedisBloom",
    "vectorset": "Redis",
}
# Group names in commands.json that are renamed for the docs
GROUP_RENAMES = {"vector_set": "vectorset"}


def is_internal_command(cmd: str) -> bool:
    """Internal commands, e.g., `_FT.DEBUG`, `FT._LIST`"""
    return any(part.startswith("_") for part in re.split(r"[ .]", cmd))


def _download(url: str, filename: str) -> None:
    if os.path.exists(filename):
        return
    response = requests.get(url)
    response.raise_for_status()
    with open(filename, "wb") as f:
        f.write(response.content)


def download_command_markdown(command: str) -> dict:
    url = f"https://raw.githubusercontent.com/redis/docs/refs/heads/main/content/commands/{command.lower()}.md"
    filename = os.path.join(THIS_DIR, f"{command}.md")
    _download(url, filename)
    # Read markdown file and extract metadata from the top of the file, which is in the format:
    # ---
    # summary: "summary of the command"
    # group: "group of the command"
    # ---
    with open(filename) as f:
        lines = f.readlines()
    metadata = {}
    if lines[0].strip() == "---":
        for ind, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                break
        metadata = yaml.load("".join(lines[1:ind]), Loader=yaml.SafeLoader)
    return metadata


def download_commands() -> dict[str, dict]:
    """All commands (core and modules) from redis/docs, keyed by lowercase name, without internal commands"""
    full_filename = os.path.join(THIS_DIR, COMMANDS_LOCAL_FILENAME)
    _download(COMMANDS_URL, full_filename)
    with open(full_filename) as f:
        curr_cmds = json.load(f)
    cmds = {k.lower(): v for k, v in curr_cmds.items() if not is_internal_command(k)}
    for cmd in MARKDOWN_COMMANDS:
        if cmd.lower() not in cmds:
            try:
                cmds[cmd.lower()] = download_command_markdown(cmd)
            except Exception as e:
                print(f"Failed to download markdown for command {cmd}: {e}")
    return cmds


def implemented_commands() -> set:
    res = set(SUPPORTED_COMMANDS.keys())
    if "json.type" not in res:
        raise ValueError("Make sure jsonpath_ng is installed to get accurate documentation")
    if "bf.add" not in res:
        raise ValueError("Make sure pybloom-live is installed to get accurate documentation")
    return res


def _commands_by_stack_and_group(commands: dict) -> dict[str, dict[str, list[str]]]:
    res: dict[str, dict[str, list[str]]] = {}
    for cmd, info in commands.items():
        if "summary" not in info:  # Undocumented commands, e.g., deprecated `FT.ADD`, `SEARCH.CLUSTERSET`
            continue
        group = GROUP_RENAMES.get(info["group"], info["group"])
        res.setdefault(MODULE_STACKS[info.get("module")], {}).setdefault(group, []).append(cmd)
    return res


def generate_redis_commands_markdown_files(
    redis_commands: dict, groups: dict[str, list[str]], fakeredis_commands: set[str], stack: str
) -> None:
    for group, group_commands in groups.items():
        filename = markdown_filename_template.format(f"{stack}/{group.upper()}")
        with open(filename, "w") as f:
            implemented_in_group = set(group_commands).intersection(fakeredis_commands)
            implemented_in_group = sorted(implemented_in_group)
            unimplemented_in_group = set(group_commands) - fakeredis_commands
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
                f.write("> To implement support for a command, see [here](../../../guides/implement-command/) \n\n")
                for cmd in unimplemented_in_group:
                    f.write(
                        f"#### [{cmd.upper()}](https://redis.io/commands/{cmd.replace(' ', '-')}/)"
                        f" <small>(not implemented)</small>\n\n"
                    )
                    f.write(f"{redis_commands[cmd]['summary']}\n\n")
            f.write("\n")


if __name__ == "__main__":
    implemented = implemented_commands()
    cmds = download_commands()
    for stack, groups in _commands_by_stack_and_group(cmds).items():
        generate_redis_commands_markdown_files(cmds, groups, implemented, stack)
    print("Commands not in any redis stack:")
    print(implemented - set(cmds.keys()))
