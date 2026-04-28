import pytest
import redis
import redis.client
import valkey

from fakeredis import _msgs as msgs
from test import testtools
from test.testtools import raw_command, resp_conversion


def test_ping(r: redis.Redis):
    assert r.ping()
    assert testtools.raw_command(r, "ping", "test") == b"test"
    with pytest.raises(Exception, match=msgs.WRONG_ARGS_MSG6.format("ping")[4:]) as ctx:
        raw_command(r, "ping", "arg1", "arg2")

    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


def test_echo(r: redis.Redis):
    assert r.echo(b"hello") == b"hello"
    assert r.echo("hello") == b"hello"


def test_unknown_command(r: redis.Redis):
    with pytest.raises(Exception) as ctx:
        raw_command(r, "0 3 3")
    assert isinstance(ctx.value, (redis.ResponseError, valkey.ResponseError))


@testtools.fake_only
def test_time(r, mocker):
    fake_time = mocker.patch("time.time")
    fake_time.return_value = 1234567890.1234567
    assert r.time() == (1234567890, 123457)
    fake_time.return_value = 1234567890.000001
    assert r.time() == (1234567890, 1)
    fake_time.return_value = 1234567890.9999999
    assert r.time() == (1234567891, 0)


# @pytest.mark.supported_redis_versions(min_ver="7")
# @pytest.mark.unsupported_server_types("dragonfly")
# def test_hello(r: redis.Redis):
#     client_info = r.client_info()
#     protocol = int(client_info.get("resp"))
#     if protocol == 2:
#         return
#     assert r.hello() == {
#         "server": "fakeredis",
#         "version": "1.0.0",
#         "proto": 2,
#         "id": 1,
#     }


@pytest.mark.unsupported_server_types("dragonfly")
@pytest.mark.supported_redis_versions(min_ver="7")
def test_client_list(r: redis.Redis):
    client_info = r.client_info()
    client_id = client_info["id"]
    client_list = r.client_list()
    assert isinstance(client_list, list)
    assert len(client_list) >= 1
    assert isinstance(client_list[0], dict)
    client_ids = [int(client["id"]) for client in client_list]
    assert client_id in client_ids

    client_list = r.client_list()
    assert isinstance(client_list, list)
    client_ids = [int(client["id"]) for client in client_list]
    non_existing_client_id = max(client_ids) + 1
    client_list = r.client_list(client_id=[str(non_existing_client_id)])
    assert isinstance(client_list, list)
    assert len(client_list) == 0


@pytest.mark.supported_redis_versions(min_ver="7")
@pytest.mark.unsupported_server_types("dragonfly")
@testtools.run_test_if_redispy_ver("gte", "5")
def test_client_info(r: redis.Redis):
    client_info = r.client_info()
    assert client_info.get("lib-name", "redis-py") in {"redis-py", "valkey-py"}
    r.client_setinfo(b"lib-name", b"fakeredis")
    r.client_setinfo(b"lib-ver", b"1.0.0")
    client_info = r.client_info()
    assert client_info["lib-name"] == "fakeredis"
    assert client_info["lib-ver"] == "1.0.0"


@pytest.mark.unsupported_server_types("dragonfly")
def test_client_id(r: redis.Redis):
    client_id = r.client_id()
    client_info = r.client_info()
    assert client_id == client_info["id"]


def test_client_setname(r: redis.Redis):
    assert r.client_setname("test") is True
    assert r.client_getname() == resp_conversion(r, b"test", "test")


@pytest.mark.decode_responses
class TestDecodeResponses:
    def test_decode_str(self, r):
        r.set("foo", "bar")
        assert r.get("foo") == "bar"

    def test_decode_set(self, r):
        r.sadd("foo", "member1")
        assert set(r.smembers("foo")) == {"member1"}

    def test_decode_list(self, r):
        r.rpush("foo", "a", "b")
        assert r.lrange("foo", 0, -1) == ["a", "b"]

    def test_decode_dict(self, r):
        r.hset("foo", "key", "value")
        assert r.hgetall("foo") == {"key": "value"}

    def test_decode_error(self, r):
        r.set("foo", "bar")
        with pytest.raises(Exception) as exc_info:
            r.hset("foo", "bar", "baz")
        assert isinstance(exc_info.value, (redis.ResponseError, valkey.ResponseError))
        assert isinstance(exc_info.value.args[0], str)


@pytest.mark.disconnected
@testtools.fake_only
class TestFakeStrictRedisConnectionErrors:
    def test_flushdb(self, r):
        with pytest.raises(Exception):
            r.flushdb()

    def test_flushall(self, r):
        with pytest.raises(Exception):
            r.flushall()

    def test_append(self, r):
        with pytest.raises(Exception):
            r.append("key", "value")

    def test_bitcount(self, r):
        with pytest.raises(Exception):
            r.bitcount("key", 0, 20)

    def test_decr(self, r):
        with pytest.raises(Exception):
            r.decr("key", 2)

    def test_exists(self, r):
        with pytest.raises(Exception):
            r.exists("key")

    def test_expire(self, r):
        with pytest.raises(Exception):
            r.expire("key", 20)

    def test_pexpire(self, r):
        with pytest.raises(Exception):
            r.pexpire("key", 20)

    def test_echo(self, r):
        with pytest.raises(Exception):
            r.echo("value")

    def test_get(self, r):
        with pytest.raises(Exception):
            r.get("key")

    def test_getbit(self, r):
        with pytest.raises(Exception):
            r.getbit("key", 2)

    def test_getset(self, r):
        with pytest.raises(Exception):
            r.getset("key", "value")

    def test_incr(self, r):
        with pytest.raises(Exception):
            r.incr("key")

    def test_incrby(self, r):
        with pytest.raises(Exception):
            r.incrby("key")

    def test_ncrbyfloat(self, r):
        with pytest.raises(Exception):
            r.incrbyfloat("key")

    def test_keys(self, r):
        with pytest.raises(Exception):
            r.keys()

    def test_mget(self, r):
        with pytest.raises(Exception):
            r.mget(["key1", "key2"])

    def test_mset(self, r):
        with pytest.raises(Exception):
            r.mset({"key": "value"})

    def test_msetnx(self, r):
        with pytest.raises(Exception):
            r.msetnx({"key": "value"})

    def test_persist(self, r):
        with pytest.raises(Exception):
            r.persist("key")

    def test_rename(self, r):
        server = r.connection_pool.connection_kwargs["server"]
        server.connected = True
        r.set("key1", "value")
        server.connected = False
        with pytest.raises(Exception) as ctx:
            r.rename("key1", "key2")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))
        server.connected = True
        assert r.exists("key1")

    def test_eval(self, r):
        with pytest.raises(Exception) as ctx:
            r.eval("", 0)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lpush(self, r):
        with pytest.raises(Exception) as ctx:
            r.lpush("name", 1, 2)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lrange(self, r):
        with pytest.raises(Exception) as ctx:
            r.lrange("name", 1, 5)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_llen(self, r):
        with pytest.raises(Exception) as ctx:
            r.llen("name")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lrem(self, r):
        with pytest.raises(Exception) as ctx:
            r.lrem("name", 2, 2)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_rpush(self, r):
        with pytest.raises(Exception) as ctx:
            r.rpush("name", 1)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lpop(self, r):
        with pytest.raises(Exception) as ctx:
            r.lpop("name")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lset(self, r):
        with pytest.raises(Exception) as ctx:
            r.lset("name", 1, 4)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_rpushx(self, r):
        with pytest.raises(Exception) as ctx:
            r.rpushx("name", 1)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_ltrim(self, r):
        with pytest.raises(Exception):
            r.ltrim("name", 1, 4)

    def test_lindex(self, r):
        with pytest.raises(Exception) as ctx:
            r.lindex("name", 1)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_lpushx(self, r):
        with pytest.raises(Exception) as ctx:
            r.lpushx("name", 1)
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_rpop(self, r):
        with pytest.raises(Exception) as ctx:
            r.rpop("name")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_linsert(self, r):
        with pytest.raises(Exception) as ctx:
            r.linsert("name", "where", "refvalue", "value")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_rpoplpush(self, r):
        with pytest.raises(Exception) as ctx:
            r.rpoplpush("src", "dst")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_blpop(self, r):
        with pytest.raises(Exception) as ctx:
            r.blpop("keys")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_brpop(self, r):
        with pytest.raises(Exception) as ctx:
            r.brpop("keys")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_brpoplpush(self, r):
        with pytest.raises(Exception) as ctx:
            r.brpoplpush("src", "dst")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hdel(self, r):
        with pytest.raises(Exception) as ctx:
            r.hdel("name")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hexists(self, r):
        with pytest.raises(Exception) as ctx:
            r.hexists("name", "key")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hget(self, r):
        with pytest.raises(Exception) as ctx:
            r.hget("name", "key")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hgetall(self, r):
        with pytest.raises(Exception) as ctx:
            r.hgetall("name")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hincrby(self, r):
        with pytest.raises(Exception) as ctx:
            r.hincrby("name", "key")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_hincrbyfloat(self, r):
        with pytest.raises(Exception):
            r.hincrbyfloat("name", "key")

    def test_hkeys(self, r):
        with pytest.raises(Exception):
            r.hkeys("name")

    def test_hlen(self, r):
        with pytest.raises(Exception):
            r.hlen("name")

    def test_hset(self, r):
        with pytest.raises(Exception):
            r.hset("name", "key", 1)

    def test_hsetnx(self, r):
        with pytest.raises(Exception):
            r.hsetnx("name", "key", 2)

    def test_hmset(self, r):
        with pytest.raises(Exception):
            r.hmset("name", {"key": 1})

    def test_hmget(self, r):
        with pytest.raises(Exception):
            r.hmget("name", ["a", "b"])

    def test_hvals(self, r):
        with pytest.raises(Exception):
            r.hvals("name")

    def test_sadd(self, r):
        with pytest.raises(Exception):
            r.sadd("name", 1, 2)

    def test_scard(self, r):
        with pytest.raises(Exception):
            r.scard("name")

    def test_sdiff(self, r):
        with pytest.raises(Exception):
            r.sdiff(["a", "b"])

    def test_sdiffstore(self, r):
        with pytest.raises(Exception):
            r.sdiffstore("dest", ["a", "b"])

    def test_sinter(self, r):
        with pytest.raises(Exception):
            r.sinter(["a", "b"])

    def test_sinterstore(self, r):
        with pytest.raises(Exception):
            r.sinterstore("dest", ["a", "b"])

    def test_sismember(self, r):
        with pytest.raises(Exception):
            r.sismember("name", 20)

    def test_smembers(self, r):
        with pytest.raises(Exception):
            r.smembers("name")

    def test_smove(self, r):
        with pytest.raises(Exception):
            r.smove("src", "dest", 20)

    def test_spop(self, r):
        with pytest.raises(Exception):
            r.spop("name")

    def test_srandmember(self, r):
        with pytest.raises(Exception):
            r.srandmember("name")

    def test_srem(self, r):
        with pytest.raises(Exception):
            r.srem("name")

    def test_sunion(self, r):
        with pytest.raises(Exception):
            r.sunion(["a", "b"])

    def test_sunionstore(self, r):
        with pytest.raises(Exception):
            r.sunionstore("dest", ["a", "b"])

    def test_zadd(self, r):
        with pytest.raises(Exception):
            r.zadd("name", {"key": "value"})

    def test_zcard(self, r):
        with pytest.raises(Exception):
            r.zcard("name")

    def test_zcount(self, r):
        with pytest.raises(Exception):
            r.zcount("name", 1, 5)

    def test_zincrby(self, r):
        with pytest.raises(Exception):
            r.zincrby("name", 1, 1)

    def test_zinterstore(self, r):
        with pytest.raises(Exception):
            r.zinterstore("dest", ["a", "b"])

    def test_zrange(self, r):
        with pytest.raises(Exception):
            r.zrange("name", 1, 5)

    def test_zrangebyscore(self, r):
        with pytest.raises(Exception):
            r.zrangebyscore("name", 1, 5)

    def test_rangebylex(self, r):
        with pytest.raises(Exception):
            r.zrangebylex("name", 1, 4)

    def test_zrem(self, r):
        with pytest.raises(Exception):
            r.zrem("name", "value")

    def test_zremrangebyrank(self, r):
        with pytest.raises(Exception):
            r.zremrangebyrank("name", 1, 5)

    def test_zremrangebyscore(self, r):
        with pytest.raises(Exception):
            r.zremrangebyscore("name", 1, 5)

    def test_zremrangebylex(self, r):
        with pytest.raises(Exception):
            r.zremrangebylex("name", 1, 5)

    def test_zlexcount(self, r):
        with pytest.raises(Exception):
            r.zlexcount("name", 1, 5)

    def test_zrevrange(self, r):
        with pytest.raises(Exception):
            r.zrevrange("name", 1, 5, 1)

    def test_zrevrangebyscore(self, r):
        with pytest.raises(Exception):
            r.zrevrangebyscore("name", 5, 1)

    def test_zrevrangebylex(self, r):
        with pytest.raises(Exception):
            r.zrevrangebylex("name", 5, 1)

    def test_zrevran(self, r):
        with pytest.raises(Exception):
            r.zrevrank("name", 2)

    def test_zscore(self, r):
        with pytest.raises(Exception):
            r.zscore("name", 2)

    def test_zunionstor(self, r):
        with pytest.raises(Exception):
            r.zunionstore("dest", ["1", "2"])

    def test_pipeline(self, r):
        with pytest.raises(Exception):
            r.pipeline().watch("key")

    def test_transaction(self, r):
        with pytest.raises(Exception):

            def func(a):
                return a * a

            r.transaction(func, 3)

    def test_lock(self, r):
        with pytest.raises(Exception):
            with r.lock("name"):
                pass

    def test_pubsub(self, r):
        with pytest.raises(Exception):
            r.pubsub().subscribe("channel")

    def test_pfadd(self, r):
        with pytest.raises(Exception):
            r.pfadd("name", 1)

    def test_pfmerge(self, r):
        with pytest.raises(Exception):
            r.pfmerge("dest", "a", "b")

    def test_scan(self, r):
        with pytest.raises(Exception):
            list(r.scan())

    def test_sscan(self, r):
        with pytest.raises(Exception):
            r.sscan("name")

    def test_hscan(self, r):
        with pytest.raises(Exception):
            r.hscan("name")

    def test_scan_iter(self, r):
        with pytest.raises(Exception):
            list(r.scan_iter())

    def test_sscan_iter(self, r):
        with pytest.raises(Exception):
            list(r.sscan_iter("name"))

    def test_hscan_iter(self, r):
        with pytest.raises(Exception):
            list(r.hscan_iter("name"))


@pytest.mark.disconnected
@testtools.fake_only
class TestPubSubConnected:
    @pytest.fixture
    def pubsub(self, r):
        return r.pubsub()

    def test_basic_subscribe(self, pubsub):
        with pytest.raises(Exception) as ctx:
            pubsub.subscribe("logs")
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))

    def test_subscription_conn_lost(self, fake_server, pubsub):
        fake_server.connected = True
        pubsub.subscribe("logs")
        fake_server.connected = False
        # The initial message is already in the pipe
        msg = pubsub.get_message()
        check = {"type": "subscribe", "pattern": None, "channel": b"logs", "data": 1}
        assert msg == check, "Message was not published to channel"
        with pytest.raises(Exception) as ctx:
            pubsub.get_message()
        assert isinstance(ctx.value, (redis.ConnectionError, valkey.ConnectionError))
