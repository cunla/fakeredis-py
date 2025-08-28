"""
Generates a JSON file with the following structure:
{
    "command_name": [
      1. Name
      2. Arity
      3. Flags
      4. First key
      5. Last key
      6. Step
      7. ACL categories (as of Redis 6.0)
      8. Tips (as of Redis 7.0)
      9. Key specifications (as of Redis 7.0)
      10. Subcommands (as of Redis 7.0)
    ]
}
that is used for the `COMMAND` redis command.
"""

import json
import os
from typing import Any, List, Dict

from fakeredis._commands import SUPPORTED_COMMANDS
from scripts.generate_supported_commands_doc import METADATA, download_single_stack_commands

THIS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))

CATEGORIES = {
    "BF.": "@bloom",
    "CF.": "@cuckoo",
    "CMS.": "@cms",
    "TOPK.": "@topk",
    "TS.": "@timeseries",
    "JSON.": "@json",
    "FT.": "@search",
    "TDIGEST.": "@tdigest",
}


def implemented_commands() -> set:
    res = set(SUPPORTED_COMMANDS.keys())
    if "json.type" not in res:
        raise ValueError("Make sure jsonpath_ng is installed to get accurate documentation")
    if "eval" not in res:
        raise ValueError("Make sure lupa is installed to get accurate documentation")
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


def get_command_info(cmd_name: str, all_commands: Dict[str, Any]) -> List[Any]:
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
    print(f"Command {cmd_name}")
    cmd_info = all_commands[cmd_name]
    first_key = dict_deep_get(cmd_info, "key_specs", 0, "begin_search", "spec", "index", default_value=0)
    last_key = dict_deep_get(cmd_info, "key_specs", -1, "begin_search", "spec", "index", default_value=0)
    step = dict_deep_get(cmd_info, "key_specs", 0, "find_keys", "spec", "keystep", default_value=0)
    tips = []  # todo
    subcommands = [
        get_command_info(cmd, all_commands) for cmd in all_commands if cmd_name != cmd and cmd.startswith(cmd_name)
    ]  # todo
    categories = set(cmd_info.get("acl_categories", []))
    for prefix, category in CATEGORIES.items():
        if cmd_name.startswith(prefix.lower()):
            categories.add(category)
    res = [
        cmd_name.lower().replace(" ", "|"),
        cmd_info.get("arity", -1),
        cmd_info.get("command_flags", []),
        first_key,
        last_key,
        step,
        sorted(list(categories)),
        tips,
        key_specs_array(cmd_info),
        subcommands,
    ]
    return res


if __name__ == "__main__":
    implemented = implemented_commands()
    command_info_dict: Dict[str, List[Any]] = dict()
    for cmd_meta in METADATA:
        cmds = download_single_stack_commands(cmd_meta.local_filename, cmd_meta.url)
        for cmd in cmds:
            if cmd not in implemented:
                continue
            command_info_dict[cmd] = get_command_info(cmd, cmds)
            subcommand = cmd.split(" ")
            if len(subcommand) > 1:
                command_info_dict.setdefault(
                    subcommand[0],
                    [subcommand[0], -1, [], 0, 0, 0, [], [], [], []],
                )[9].append(command_info_dict[cmd])
            print(command_info_dict[cmd])
    with open(os.path.join(os.path.dirname(__file__), "..", "fakeredis", "commands.json"), "w") as f:
        json.dump(command_info_dict, f)
