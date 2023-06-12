"""
Script to create issue for every unsupported command.
To run this:
- Install pygithub: pip install pygithub
- Set environment variable `GITHUB_TOKEN` to a github token with permissions to create issues.
  - Another option is to create `.env` file with `GITHUB_TOKEN`.
"""
import os

from dotenv import load_dotenv
from github import Github

from supported import download_redis_commands, implemented_commands

load_dotenv()  # take environment variables from .env.

IGNORE_GROUPS = {
    'suggestion', 'tdigest', 'scripting', 'cf', 'topk',
    'hyperloglog', 'graph', 'timeseries', 'connection',
    'server', 'generic', 'cms', 'bf', 'cluster',
    'search', 'bitmap',
}
IGNORE_COMMANDS = {
    'PUBSUB HELP', 'OBJECT HELP', 'FUNCTION HELP',
    'SCRIPT HELP',
    'JSON.DEBUG', 'JSON.DEBUG HELP', 'JSON.DEBUG MEMORY',
    'JSON.RESP',
    'XINFO', 'XINFO HELP', 'XGROUP', 'XGROUP HELP', 'XSETID',
    'ACL HELP', 'COMMAND HELP', 'CONFIG HELP', 'DEBUG',
    'MEMORY HELP', 'MODULE HELP', 'CLIENT HELP',
}


def commands_groups(
        all_commands: dict, implemented_set: set
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    implemented, unimplemented = dict(), dict()
    for cmd in all_commands:
        if cmd.upper() in IGNORE_COMMANDS:
            continue
        group = all_commands[cmd]['group']
        unimplemented.setdefault(group, [])
        implemented.setdefault(group, [])
        if cmd in implemented_set:
            implemented[group].append(cmd)
        else:
            unimplemented[group].append(cmd)
    return implemented, unimplemented


def get_unimplemented_and_implemented_commands() -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Returns 2 dictionaries, one of unimplemented commands and another of implemented commands

    """
    commands = download_redis_commands()
    implemented_commands_set = implemented_commands()
    implemented_dict, unimplemented_dict = commands_groups(commands, implemented_commands_set)
    groups = sorted(implemented_dict.keys(), key=lambda x: len(unimplemented_dict[x]))
    for group in groups:
        unimplemented_count = len(unimplemented_dict[group])
        total_count = len(implemented_dict.get(group)) + unimplemented_count
        print(f'{group} has {unimplemented_count}/{total_count} unimplemented commands')
    return unimplemented_dict, implemented_dict


class GithubData:
    def __init__(self, dry=False):
        token = os.getenv('GITHUB_TOKEN', None)
        g = Github(token)
        self.dry = dry or (token is None)
        self.gh_repo = g.get_repo('cunla/fakeredis')
        open_issues = self.gh_repo.get_issues(state='open')
        self.issues = {i.title: i.number for i in open_issues}
        gh_labels = self.gh_repo.get_labels()
        self.labels = {label.name for label in gh_labels}

    def create_label(self, name):
        if self.dry:
            print(f'Creating label "{name}"')
        else:
            self.gh_repo.create_label(name, "f29513")
        self.labels.add(name)

    def create_issue(self, group: str, cmd: str, summary: str):
        link = f"https://redis.io/commands/{cmd.replace(' ', '-')}/"
        title = f"Implement support for `{cmd.upper()}` ({group} command)"
        filename = f'{group}_mixin.py'
        body = f"""Implement support for command `{cmd.upper()}` in {filename}.

{summary}.

Here is the [Official documentation]({link})"""
        labels = [f'{group}-commands', 'enhancement', 'help wanted']
        for label in labels:
            if label not in self.labels:
                self.create_label(label)
        if title in self.issues:
            return
        if self.dry:
            print(f'Creating issue with title "{title}" and labels {labels}')
        else:
            self.gh_repo.create_issue(title, body, labels=labels)


def print_gh_commands(commands: dict, unimplemented: dict):
    gh = GithubData()
    for group in unimplemented:
        if group in IGNORE_GROUPS:
            continue
        print(f'### Creating issues for {group} commands')
        for cmd in unimplemented[group]:
            if cmd.upper() in IGNORE_COMMANDS:
                continue
            summary = commands[cmd]['summary']
            gh.create_issue(group, cmd, summary)


if __name__ == '__main__':
    commands = download_redis_commands()
    unimplemented_dict, _ = get_unimplemented_and_implemented_commands()
    print_gh_commands(commands, unimplemented_dict)
