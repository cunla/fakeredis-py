import os

from fakeredis import FakeServer, FakeStrictRedis


def test_acl_save_load():
    acl_filename = b"./users.acl"
    server = FakeServer(config={b"aclfile": acl_filename})
    r = FakeStrictRedis(server=server)
    username = "fakeredis-user"
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
    r.acl_save()

    # assert acl file contains all data
    with open(acl_filename, "r") as f:
        lines = f.readlines()
        assert len(lines) == 2
        user_rule = lines[1]
        assert user_rule.startswith("user fakeredis-user")
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

    # assert acl file is loaded correctly
    server2 = FakeServer(config={b"aclfile": acl_filename})
    r2 = FakeStrictRedis(server=server2)
    r2.acl_load()
    rules = r2.acl_list()
    user_rule = next(filter(lambda x: x.startswith(f"user {username}"), rules), None)
    assert user_rule.startswith("user fakeredis-user")
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

    os.remove(acl_filename)
