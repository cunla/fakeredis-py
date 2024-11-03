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

    with open(acl_filename, "rb") as f:
        lines = f.readlines()
        assert len(lines) == 1
