import pytest
import redis
from redis import exceptions

from fakeredis._helpers import asbytes
from fakeredis.model import get_categories, get_commands_by_category
from test import testtools
from test.conftest import ServerDetails
from test.testtools import resp_conversion

pytestmark = []
pytestmark.extend([pytest.mark.min_server("7"), testtools.run_test_if_redispy_ver("gte", "5")])

_VALKEY_UNSUPPORTED_COMMANDS = {
    "hexpiretime",
    "hexpireat",
    "hpexpireat",
    "hexpire",
    "hpttl",
    "hpexpire",
    "hpexpiretime",
    "httl",
}


def test_acl_cat(r: redis.Redis, real_server_details: ServerDetails):
    fakeredis_categories = get_categories()
    fakeredis_categories = {asbytes(cat) for cat in fakeredis_categories}
    fakeredis_categories.add(b"search")
    response_categories = r.acl_cat()
    response_categories = {asbytes(cat) for cat in response_categories}
    assert len(set(response_categories) - set(fakeredis_categories)) == 0
    if b"search" in response_categories:
        response_categories.remove(b"search")  # `search` is not supported by fakeredis
    for cat in response_categories:
        commands = get_commands_by_category(cat)
        commands = {cmd.decode() for cmd in commands}
        assert len(commands) >= 0
        commands.discard("hpersist")
        if real_server_details[0] == "valkey":
            commands = commands - _VALKEY_UNSUPPORTED_COMMANDS
        commands = {asbytes(cmd.replace(" ", "|")) for cmd in commands}
        server_commands = r.acl_cat(cat)
        server_commands = {asbytes(cmd) for cmd in server_commands}
        diff = set(commands) - set(server_commands)
        assert len(diff) == 0, f"Commands not found in category {cat}: {diff}"


def test_acl_genpass(r: redis.Redis):
    assert len(r.acl_genpass()) == 64
    assert len(r.acl_genpass(128)) == 32


def test_auth(r: redis.Redis):
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
    username = "fakeredis-authuser"

    assert r.acl_setuser(username, enabled=True, passwords=["+strong_password"], commands=["+acl"])

    assert r.auth(username=username, password="strong_password") is True

    with pytest.raises(redis.AuthenticationError):
        r.auth(username=username, password="wrong_password")

    # test that user can log in even if the default user is disabled
    r.acl_setuser(default_username, enabled=False)
    assert r.auth(username=username, password="strong_password") is True

    r.acl_setuser(default_username, enabled=True)
    r.auth("", "default")


def test_acl_list(r: redis.Redis):
    username = "fakeredis-user"
    r.acl_deluser(username)
    start = r.acl_list()

    assert r.acl_setuser(username, enabled=False, reset=True)
    users = r.acl_list()
    assert len(users) == len(start) + 1
    assert r.acl_setuser(
        username,
        enabled=True,
        reset=True,
        passwords=["+pass1", "+pass2"],
        categories=["+set", "+@hash", "-geo"],
        commands=["+get", "+mget", "-hset"],
        keys=["cache:*", "objects:*"],
        channels=["message:*"],
        selectors=[("+set", "%W~app*"), ("+get", "%RW~app* &x"), ("-hset", "%W~app*")],
    )
    rules = r.acl_list()
    rules = [(rule.decode() if isinstance(rule, bytes) else rule) for rule in rules]
    user_rule = next(filter(lambda x: x.startswith(f"user {username}"), rules), None)
    assert user_rule is not None

    assert "nopass" not in user_rule
    assert "#e6c3da5b206634d7f3f3586d747ffdb36b5c675757b380c6a5fe5c570c714349" in user_rule
    assert "#1ba3d16e9881959f8c9a9762854f72c6e6321cdd44358a10a4e939033117eab9" in user_rule
    assert "on" in user_rule
    assert "~cache:*" in user_rule
    assert "~objects:*" in user_rule
    assert "resetchannels &message:*" in user_rule
    assert "(%W~app* resetchannels -@all +set)" in user_rule
    assert "(~app* resetchannels &x -@all +get)" in user_rule
    assert "(%W~app* resetchannels -@all -hset)" in user_rule


def test_acl_getuser_setuser(r: redis.Redis):
    username = "fakeredis-user"

    # test enabled=False
    assert r.acl_setuser(username, enabled=False, reset=True)
    acl = r.acl_getuser(username)
    assert acl["categories"] == ["-@all"]
    assert acl["commands"] == []
    assert acl["keys"] == []
    assert acl["passwords"] == []
    assert "off" in acl["flags"]
    assert acl["enabled"] is False

    # test nopass=True
    assert r.acl_setuser(username, enabled=True, reset=True, nopass=True)
    acl = r.acl_getuser(username)
    assert acl["categories"] == ["-@all"]
    assert acl["commands"] == []
    assert acl["keys"] == []
    assert acl["passwords"] == []
    assert "on" in acl["flags"]
    assert "nopass" in acl["flags"]
    assert acl["enabled"] is True

    # test all args
    assert r.acl_setuser(
        username,
        enabled=True,
        reset=True,
        passwords=["+pass1", "+pass2"],
        categories=["+set", "+@hash", "-@geo"],
        commands=["+get", "+mget", "-hset"],
        keys=["cache:*", "objects:*"],
    )
    acl = r.acl_getuser(username)
    assert set(acl["categories"]) == {"+@hash", "+@set", "-@all", "-@geo"}
    assert set(acl["commands"]) == {"+get", "+mget", "-hset"}
    assert acl["enabled"] is True
    assert "on" in acl["flags"]
    assert set(acl["keys"]) == {"~cache:*", "~objects:*"}
    assert len(acl["passwords"]) == 2

    # # test reset=False keeps existing ACL and applies new ACL on top
    assert r.acl_setuser(
        username,
        enabled=True,
        reset=True,
        passwords=["+pass1"],
        categories=["+@set"],
        commands=["+get"],
        keys=["cache:*"],
    )
    assert r.acl_setuser(
        username,
        enabled=True,
        passwords=["+pass2"],
        categories=["+@hash"],
        commands=["+mget"],
        keys=["objects:*"],
    )
    acl = r.acl_getuser(username)
    assert set(acl["commands"]) == {"+get", "+mget"}
    assert acl["enabled"] is True
    assert "on" in acl["flags"]
    assert set(acl["keys"]) == {"~cache:*", "~objects:*"}
    assert len(acl["passwords"]) == 2

    # # test removal of passwords
    assert r.acl_setuser(username, enabled=True, reset=True, passwords=["+pass1", "+pass2"])
    assert len(r.acl_getuser(username)["passwords"]) == 2
    assert r.acl_setuser(username, enabled=True, passwords=["-pass2"])
    assert len(r.acl_getuser(username)["passwords"]) == 1

    # # Resets and tests that hashed passwords are set properly.
    hashed_password = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    assert r.acl_setuser(username, enabled=True, reset=True, hashed_passwords=["+" + hashed_password])
    acl = r.acl_getuser(username)
    assert acl["passwords"] == [hashed_password]

    # test removal of hashed passwords
    assert r.acl_setuser(
        username,
        enabled=True,
        reset=True,
        hashed_passwords=["+" + hashed_password],
        passwords=["+pass1"],
    )
    assert len(r.acl_getuser(username)["passwords"]) == 2
    assert r.acl_setuser(username, enabled=True, hashed_passwords=["-" + hashed_password])
    assert len(r.acl_getuser(username)["passwords"]) == 1

    # # test selectors
    assert r.acl_setuser(
        username,
        enabled=True,
        reset=True,
        passwords=["+pass1", "+pass2"],
        categories=["+set", "+@hash", "-geo"],
        commands=["+get", "+mget", "-hset"],
        keys=["cache:*", "objects:*"],
        channels=["message:*"],
        selectors=[("+set", "%W~app*")],
    )
    acl = r.acl_getuser(username)
    assert set(acl["categories"]) == {"+@hash", "+@set", "-@all", "-@geo"}
    assert set(acl["commands"]) == {"+get", "+mget", "-hset"}
    assert acl["enabled"] is True
    assert "on" in acl["flags"]
    assert set(acl["keys"]) == {"~cache:*", "~objects:*"}
    assert len(acl["passwords"]) == 2
    assert set(acl["channels"]) == {"&message:*"}
    r.acl_deluser(username)
    assert acl["selectors"] == resp_conversion(
        r,
        [{"channels": "", "commands": "-@all +set", "keys": "%W~app*"}],
        [["commands", "-@all +set", "keys", "%W~app*", "channels", ""]],
    )

    assert r.acl_setuser(
        username,
        enabled=True,
        reset=True,
        passwords=["+pass1", "+pass2"],
        categories=["+set", "+@hash", "-geo"],
        commands=["+get", "+mget", "-hset"],
        keys=["cache:*", "objects:*"],
        channels=["message:*"],
        selectors=[("+set", "%W~app*"), ("+get", "%RW~app* &x"), ("-hset", "%W~app*")],
    )
    acl = r.acl_getuser(username)
    assert acl["selectors"] == resp_conversion(
        r,
        [
            {"channels": "", "commands": "-@all +set", "keys": "%W~app*"},
            {"channels": "&x", "commands": "-@all +get", "keys": "~app*"},
            {"channels": "", "commands": "-@all -hset", "keys": "%W~app*"},
        ],
        [
            ["commands", "-@all +set", "keys", "%W~app*", "channels", ""],
            ["commands", "-@all +get", "keys", "~app*", "channels", "&x"],
            ["commands", "-@all -hset", "keys", "%W~app*", "channels", ""],
        ],
    )


def test_acl_users(r: redis.Redis):
    username = "fakeredis-user"
    r.acl_deluser(username)
    start = r.acl_users()

    assert r.acl_setuser(username, enabled=False, reset=True)
    users = r.acl_users()
    assert len(users) == len(start) + 1
    assert (username.encode() in users) or (username in users)


def test_acl_whoami(r: redis.Redis):
    # first, test for default user (`username` is supposed to be optional)
    default_username = "default"
    temp_pass = "temp_pass"
    r.config_set("requirepass", temp_pass)

    assert r.auth(temp_pass, default_username) is True
    assert r.auth(temp_pass) is True
    assert asbytes(r.acl_whoami()) == asbytes(default_username)

    username = "fakeredis-authuser"
    r.acl_deluser(username)
    r.acl_setuser(username, enabled=True, passwords=["+strong_password"], commands=["+acl"])
    r.auth(username=username, password="strong_password")
    assert asbytes(r.acl_whoami()) == asbytes(username)
    assert r.auth(temp_pass, default_username) is True
    r.config_set("requirepass", "")


def test_acl_log_auth_exist(r: redis.Redis, request):
    username = "fredis-py-user"

    def teardown():
        r.auth("", username="default")
        r.acl_deluser(username)

    request.addfinalizer(teardown)
    r.acl_setuser(
        username,
        enabled=True,
        reset=True,
        commands=["+get", "+set", "+select"],
        keys=["cache:*"],
        passwords=["+pass1"],
    )
    r.acl_log_reset()

    with pytest.raises(exceptions.AuthenticationError):
        r.auth("xxx", username=username)
    r.auth("pass1", username=username)

    # Valid operation and key
    assert r.set("cache:0", 1)
    assert r.get("cache:0") == b"1"

    r.auth("", "default")
    log = r.acl_log()
    assert isinstance(log, list)
    assert len(log) == 1
    assert len(r.acl_log(count=1)) == 1
    assert isinstance(log[0], dict)

    auth_record = log[0]
    assert auth_record["username"] == username
    assert auth_record["reason"] == "auth"
    assert auth_record["object"] == "AUTH"


def test_acl_log_invalid_key(r: redis.Redis, request):
    username = "fredis-py-user"

    def teardown():
        r.auth("", username="default")
        r.acl_deluser(username)

    request.addfinalizer(teardown)
    r.acl_setuser(
        username,
        enabled=True,
        reset=True,
        commands=["+get", "+set", "+select"],
        keys=["cache:*"],
        nopass=True,
    )
    r.acl_log_reset()

    r.auth("", username=username)

    # Valid operation and key
    assert r.set("cache:0", 1)
    assert r.get("cache:0") == b"1"

    # Invalid operation
    with pytest.raises(exceptions.NoPermissionError) as ctx:
        r.hset("cache:0", "hkey", "hval")

    assert str(ctx.value) == "User fredis-py-user has no permissions to run the 'hset' command"

    # Invalid key
    with pytest.raises(exceptions.NoPermissionError) as ctx:
        r.get("violated_cache:0")

    assert str(ctx.value) == "No permissions to access a key"

    r.auth("", "default")
    log = r.acl_log()
    assert isinstance(log, list)
    assert len(log) == 2
    assert len(r.acl_log(count=1)) == 1
    assert isinstance(log[0], dict)

    bad_key_record = log[0]
    assert bad_key_record["username"] == username
    assert bad_key_record["reason"] == "key"
    assert bad_key_record["object"] == "violated_cache:0"

    bad_command_record = log[1]
    assert bad_command_record["username"] == username
    assert bad_command_record["reason"] == "command"
    assert bad_command_record["object"].lower() == "hset"


def test_acl_log_invalid_channel(r: redis.Redis, request):
    username = "fredis-py-user"

    def teardown():
        r.auth("", username="default")
        r.acl_deluser(username)

    request.addfinalizer(teardown)
    r.acl_setuser(
        username,
        enabled=True,
        reset=True,
        commands=["+get", "+set", "+select", "+publish"],
        channels=["message:*"],
        keys=["cache:*"],
        nopass=True,
    )
    r.acl_log_reset()

    r.auth("", username=username)

    # Valid operation and key
    assert r.set("cache:0", 1)
    assert r.get("cache:0") == b"1"

    with pytest.raises(exceptions.NoPermissionError) as ctx:
        r.publish("invalid-channel", "message")

    assert str(ctx.value) == "No permissions to access a channel"

    r.auth("", "default")
    log = r.acl_log()
    assert isinstance(log, list)
    assert len(log) == 1
    assert len(r.acl_log(count=1)) == 1
    assert isinstance(log[0], dict)

    log_record = r.acl_log(count=1)[0]
    assert log_record["username"] == username
    assert log_record["reason"] == "channel"
    assert log_record["object"].lower() == "invalid-channel"
