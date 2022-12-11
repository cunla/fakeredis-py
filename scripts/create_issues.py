"""
Script to create issue for every unsupported command.
"""
import os

from dotenv import load_dotenv
from github import Github

from supported import get_unimplemented_and_implemented_commands, download_redis_commands

load_dotenv()  # take environment variables from .env.

IGNORE_GROUPS = {
    'server', 'cf', 'cms', 'topk', 'tdigest', 'bf', 'search', 'suggestion', 'timeseries',
    'graph', 'server', 'cluster', 'connection',
    'server', 'cluster', 'list', 'connection', 'bitmap', 'sorted-set', 'generic', 'scripting', 'geo', 'string', 'hash',
    'hyperloglog', 'pubsub', 'stream', 'graph', 'timeseries', 'search', 'suggestion', 'bf', 'cf', 'cms', 'topk',
    'tdigest', 'json',
}
IGNORE_COMMANDS = {
    'PUBSUB HELP',
    'OBJECT HELP',
    'FUNCTION HELP',
    'SCRIPT HELP',
    'XGROUP HELP',
    'XINFO HELP',
    'JSON.DEBUG HELP',
    'JSON.DEBUG MEMORY',
    'JSON.DEBUG',
    'JSON.TYPE',
    'JSON.OBJKEYS',
    'JSON.OBJLEN',
    'JSON.ARRTRIM',
    'JSON.ARRAPPEND',
    'JSON.ARRINDEX',
    'JSON.ARRINSERT',
    'JSON.ARRLEN',
    'JSON.ARRPOP',
    'JSON.NUMINCRBY',
    'JSON.NUMMULTBY',
    'JSON.RESP',
}


class GithubData:
    def __init__(self, dry=True):
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
