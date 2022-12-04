"""
Script to create issue for every unsupported command.
"""

from supported import get_unimplemented_and_implemented_commands, download_redis_commands

IGNORE_GROUPS = {
    'server', 'cf', 'cms', 'topk', 'tdigest', 'bf', 'search', 'suggestion', 'timeseries',
    'graph', 'server', 'cluster', 'connection',
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
}


def print_gh_commands(commands: dict, unimplemented: dict):
    for group in unimplemented:
        if group in IGNORE_GROUPS:
            continue
        print(f'### Creating issues for {group} commands')
        for item in unimplemented[group]:
            cmd = item.upper()
            if cmd in IGNORE_COMMANDS:
                continue
            link = f"https://redis.io/commands/{item.replace(' ', '-')}/"
            summary = commands[item]['summary']
            title = f"Implement support for \`{cmd}\` ({group} command)"
            body = f"Implement support for command \`{cmd}\` ([documentation]({link})). {summary}"
            print(f'gh issue create --title "{title}" --body "{body}" --label "enhancement,help wanted"')


if __name__ == '__main__':
    commands = download_redis_commands()
    unimplemented_dict, _ = get_unimplemented_and_implemented_commands()
    print_gh_commands(commands, unimplemented_dict)
