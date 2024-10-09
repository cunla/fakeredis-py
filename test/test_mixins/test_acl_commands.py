import redis

from fakeredis._command_info import get_categories, get_commands_by_category


def test_acl_cat(r: redis.Redis):
    categories = get_categories()
    categories = [cat.decode() for cat in categories]
    assert set(r.acl_cat()) == set(categories)
    for cat in categories:
        commands = get_commands_by_category(cat)
        commands = {cmd.decode() for cmd in commands}
        if "hpersist" in commands:
            commands.remove("hpersist")
        assert len(commands) > 0
        diff = set(commands) - set(r.acl_cat(cat))
        assert len(diff) == 0
