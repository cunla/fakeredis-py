"""
Script to create issue for every unsupported command.
"""

from supported import get_unimplemented_and_implemented_commands, download_redis_commands


def print_gh_commands(commands: dict, unimplemented: dict):
    for group in unimplemented:
        print(f'### Creating issues for {group} commands')
        for item in unimplemented[group]:
            cmd = item.upper()
            link = f"https://redis.io/commands/{item.replace(' ', '-')}/"
            summary = commands[item]['summary']
            title = f"Implement support for \`{cmd}\` ({group} command)"
            body = f"Implement support for command \`{cmd}\` ([documentation]({link})). {summary}"
            print(f'gh issue create --title "{title}" --body "{body}" --label "enhancement,help wanted"')


if __name__ == '__main__':
    commands = download_redis_commands()
    unimplemented_dict, _ = get_unimplemented_and_implemented_commands()
    print_gh_commands(commands, unimplemented_dict)
