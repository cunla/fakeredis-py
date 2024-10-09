import pytest
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


def test_acl_genpass(r: redis.Redis):
    assert len(r.acl_genpass()) == 64
    assert len(r.acl_genpass(128)) == 32


def test_auth(r: redis.Redis):
    # sending an AUTH command before setting a user/password on the
    # server should return an AuthenticationError
    with pytest.raises(redis.AuthenticationError):
        r.auth("some_password")

    with pytest.raises(redis.AuthenticationError):
        r.auth("some_password", "some_user")

    # first, test for default user (`username` is supposed to be optional)
    default_username = "default"
    temp_pass = "temp_pass"
    r.config_set("requirepass", temp_pass)

    assert r.auth(temp_pass, default_username) is True
    assert r.auth(temp_pass) is True
    r.config_set("requirepass", "")

    # test for other users
    username = "redis-py-auth"

    assert r.acl_setuser(username, enabled=True, passwords=["+strong_password"], commands=["+acl"])

    assert r.auth(username=username, password="strong_password") is True

    with pytest.raises(redis.AuthenticationError):
        r.auth(username=username, password="wrong_password")
