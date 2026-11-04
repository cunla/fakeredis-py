import pytest
import redis

import fakeredis
from fakeredis.model._acl import UserAccessControlList

pytestmark = [pytest.mark.fake]


@pytest.fixture
def r():
    return fakeredis.FakeRedis(server=fakeredis.FakeServer(version=(8,)))


def _user(*rules: bytes, keys: bytes = b"*", channels: bytes = b"*") -> UserAccessControlList:
    user = UserAccessControlList()
    for rule in rules:
        user.add_command_or_category(rule)
    if keys:
        user.add_key_pattern(keys)
    if channels:
        user.add_channel_pattern(channels)
    return user


def test_unrestricted():
    assert _user(b"+@all").unrestricted()
    assert not _user().unrestricted()
    assert not _user(b"+get").unrestricted()
    assert not _user(b"+@all", b"-get").unrestricted()
    assert not _user(b"+@all", b"-@dangerous").unrestricted()
    assert not _user(b"+@all", keys=b"cache:*").unrestricted()
    assert not _user(b"+@all", channels=b"news:*").unrestricted()
    assert not _user(b"+@all", keys=b"").unrestricted()


def test_restricting_the_default_user_takes_effect(r: redis.Redis):
    assert r.set("cache:0", 1)
    assert r.set("other:0", 1)

    r.acl_setuser("default", enabled=True, reset=True, nopass=True, commands=["+@all"], keys=["cache:*"])
    assert r.get("cache:0") == b"1"
    with pytest.raises(redis.exceptions.NoPermissionError):
        r.get("other:0")

    r.acl_setuser("default", enabled=True, reset=True, nopass=True, commands=["+@all"], keys=["*"], channels=["*"])
    assert r.get("other:0") == b"1"


def test_denied_command_is_logged_with_the_client_info(r: redis.Redis):
    r.acl_setuser("limited", enabled=True, reset=True, nopass=True, commands=["+get", "+auth"], keys=["cache:*"])
    limited = fakeredis.FakeRedis(server=r.connection_pool.connection_kwargs["server"])
    limited.auth("", username="limited")
    with pytest.raises(redis.exceptions.NoPermissionError):
        limited.set("cache:0", 1)
    with pytest.raises(redis.exceptions.NoPermissionError):
        limited.get("other:0")

    log = r.acl_log()
    assert [record["reason"] for record in log] == ["key", "command"]
    for record in log:
        assert record["username"] == "limited"
        assert record["client-info"]["user"] == "limited"
        assert "resp" in record["client-info"]
