"""
Tests will run only if module lupa is installed.
"""
import logging

import pytest
import pytest_asyncio
import redis
import redis.client
from packaging.version import Version
from redis.exceptions import ResponseError

import fakeredis
import testtools

lupa = pytest.importorskip("lupa")

fake_only = pytest.mark.parametrize(
    'create_redis',
    [pytest.param('FakeStrictRedis', marks=pytest.mark.fake)],
    indirect=True
)


@pytest_asyncio.fixture
def r(request, create_redis):
    rconn = create_redis(db=0)
    connected = request.node.get_closest_marker('disconnected') is None
    if connected:
        rconn.flushall()
    yield rconn
    if connected:
        rconn.flushall()
    if hasattr(r, 'close'):
        rconn.close()  # Older versions of redis-py don't have this method


@pytest_asyncio.fixture(
    params=[
        pytest.param('StrictRedis', marks=pytest.mark.real),
        pytest.param('FakeStrictRedis', marks=pytest.mark.fake)
    ]
)
def create_redis(request):
    name = request.param
    if not name.startswith('Fake') and not request.getfixturevalue('is_redis_running'):
        pytest.skip('Redis is not running')
    decode_responses = request.node.get_closest_marker('decode_responses') is not None

    def factory(db=0):
        if name.startswith('Fake'):
            fake_server = request.getfixturevalue('fake_server')
            cls = getattr(fakeredis, name)
            return cls(db=db, decode_responses=decode_responses, server=fake_server)
        else:
            cls = getattr(redis, name)
            conn = cls('localhost', port=6379, db=db, decode_responses=decode_responses)
            min_server_marker = request.node.get_closest_marker('min_server')
            if min_server_marker is not None:
                server_version = conn.info()['redis_version']
                min_version = Version(min_server_marker.args[0])
                if Version(server_version) < min_version:
                    pytest.skip(
                        'Redis server {} required but {} found'.format(min_version, server_version)
                    )
            return conn

    return factory


def test_eval_blpop(r):
    r.rpush('foo', 'bar')
    with pytest.raises(redis.ResponseError, match='not allowed from scripts'):
        r.eval('return redis.pcall("BLPOP", KEYS[1], 1)', 1, 'foo')


def test_eval_set_value_to_arg(r):
    r.eval('redis.call("SET", KEYS[1], ARGV[1])', 1, 'foo', 'bar')
    val = r.get('foo')
    assert val == b'bar'


def test_eval_conditional(r):
    lua = """
    local val = redis.call("GET", KEYS[1])
    if val == ARGV[1] then
        redis.call("SET", KEYS[1], ARGV[2])
    else
        redis.call("SET", KEYS[1], ARGV[1])
    end
    """
    r.eval(lua, 1, 'foo', 'bar', 'baz')
    val = r.get('foo')
    assert val == b'bar'
    r.eval(lua, 1, 'foo', 'bar', 'baz')
    val = r.get('foo')
    assert val == b'baz'


def test_eval_table(r):
    lua = """
    local a = {}
    a[1] = "foo"
    a[2] = "bar"
    a[17] = "baz"
    return a
    """
    val = r.eval(lua, 0)
    assert val == [b'foo', b'bar']


def test_eval_table_with_nil(r):
    lua = """
    local a = {}
    a[1] = "foo"
    a[2] = nil
    a[3] = "bar"
    return a
    """
    val = r.eval(lua, 0)
    assert val == [b'foo']


def test_eval_table_with_numbers(r):
    lua = """
    local a = {}
    a[1] = 42
    return a
    """
    val = r.eval(lua, 0)
    assert val == [42]


def test_eval_nested_table(r):
    lua = """
    local a = {}
    a[1] = {}
    a[1][1] = "foo"
    return a
    """
    val = r.eval(lua, 0)
    assert val == [[b'foo']]


def test_eval_iterate_over_argv(r):
    lua = """
    for i, v in ipairs(ARGV) do
    end
    return ARGV
    """
    val = r.eval(lua, 0, "a", "b", "c")
    assert val == [b"a", b"b", b"c"]


def test_eval_iterate_over_keys(r):
    lua = """
    for i, v in ipairs(KEYS) do
    end
    return KEYS
    """
    val = r.eval(lua, 2, "a", "b", "c")
    assert val == [b"a", b"b"]


def test_eval_mget(r):
    r.set('foo1', 'bar1')
    r.set('foo2', 'bar2')
    val = r.eval('return redis.call("mget", "foo1", "foo2")', 2, 'foo1', 'foo2')
    assert val == [b'bar1', b'bar2']


@testtools.run_test_if_redis_ver('below', '3')
def test_eval_mget_none(r):
    r.set('foo1', None)
    r.set('foo2', None)
    val = r.eval('return redis.call("mget", "foo1", "foo2")', 2, 'foo1', 'foo2')
    assert val == [b'None', b'None']


def test_eval_mget_not_set(r):
    val = r.eval('return redis.call("mget", "foo1", "foo2")', 2, 'foo1', 'foo2')
    assert val == [None, None]


def test_eval_hgetall(r):
    r.hset('foo', 'k1', 'bar')
    r.hset('foo', 'k2', 'baz')
    val = r.eval('return redis.call("hgetall", "foo")', 1, 'foo')
    sorted_val = sorted([val[:2], val[2:]])
    assert sorted_val == [[b'k1', b'bar'], [b'k2', b'baz']]


def test_eval_hgetall_iterate(r):
    r.hset('foo', 'k1', 'bar')
    r.hset('foo', 'k2', 'baz')
    lua = """
    local result = redis.call("hgetall", "foo")
    for i, v in ipairs(result) do
    end
    return result
    """
    val = r.eval(lua, 1, 'foo')
    sorted_val = sorted([val[:2], val[2:]])
    assert sorted_val == [[b'k1', b'bar'], [b'k2', b'baz']]


@testtools.run_test_if_redis_ver('below', '3')
def test_eval_list_with_nil(r):
    r.lpush('foo', 'bar')
    r.lpush('foo', None)
    r.lpush('foo', 'baz')
    val = r.eval('return redis.call("lrange", KEYS[1], 0, 2)', 1, 'foo')
    assert val == [b'baz', b'None', b'bar']


def test_eval_invalid_command(r):
    with pytest.raises(ResponseError):
        r.eval(
            'return redis.call("FOO")',
            0
        )


def test_eval_syntax_error(r):
    with pytest.raises(ResponseError):
        r.eval('return "', 0)


def test_eval_runtime_error(r):
    with pytest.raises(ResponseError):
        r.eval('error("CRASH")', 0)


def test_eval_more_keys_than_args(r):
    with pytest.raises(ResponseError):
        r.eval('return 1', 42)


def test_eval_numkeys_float_string(r):
    with pytest.raises(ResponseError):
        r.eval('return KEYS[1]', '0.7', 'foo')


def test_eval_numkeys_integer_string(r):
    val = r.eval('return KEYS[1]', "1", "foo")
    assert val == b'foo'


def test_eval_numkeys_negative(r):
    with pytest.raises(ResponseError):
        r.eval('return KEYS[1]', -1, "foo")


def test_eval_numkeys_float(r):
    with pytest.raises(ResponseError):
        r.eval('return KEYS[1]', 0.7, "foo")


def test_eval_global_variable(r):
    # Redis doesn't allow script to define global variables
    with pytest.raises(ResponseError):
        r.eval('a=10', 0)


def test_eval_global_and_return_ok(r):
    # Redis doesn't allow script to define global variables
    with pytest.raises(ResponseError):
        r.eval(
            '''
            a=10
            return redis.status_reply("Everything is awesome")
            ''',
            0
        )


def test_eval_convert_number(r):
    # Redis forces all Lua numbers to integer
    val = r.eval('return 3.2', 0)
    assert val == 3
    val = r.eval('return 3.8', 0)
    assert val == 3
    val = r.eval('return -3.8', 0)
    assert val == -3


def test_eval_convert_bool(r):
    # Redis converts true to 1 and false to nil (which redis-py converts to None)
    assert r.eval('return false', 0) is None
    val = r.eval('return true', 0)
    assert val == 1
    assert not isinstance(val, bool)


def test_eval_call_bool(r):
    # Redis doesn't allow Lua bools to be passed to [p]call
    with pytest.raises(redis.ResponseError,
                       match=r'Lua redis\(\) command arguments must be strings or integers'):
        r.eval('return redis.call("SET", KEYS[1], true)', 1, "testkey")


@testtools.run_test_if_redis_ver('below', '3')
def test_eval_none_arg(r):
    val = r.eval('return ARGV[1] == "None"', 0, None)
    assert val


def test_eval_return_error(r):
    with pytest.raises(redis.ResponseError, match='Testing') as exc_info:
        r.eval('return {err="Testing"}', 0)
    assert isinstance(exc_info.value.args[0], str)
    with pytest.raises(redis.ResponseError, match='Testing') as exc_info:
        r.eval('return redis.error_reply("Testing")', 0)
    assert isinstance(exc_info.value.args[0], str)


def test_eval_return_redis_error(r):
    with pytest.raises(redis.ResponseError) as exc_info:
        r.eval('return redis.pcall("BADCOMMAND")', 0)
    assert isinstance(exc_info.value.args[0], str)


def test_eval_return_ok(r):
    val = r.eval('return {ok="Testing"}', 0)
    assert val == b'Testing'
    val = r.eval('return redis.status_reply("Testing")', 0)
    assert val == b'Testing'


def test_eval_return_ok_nested(r):
    val = r.eval(
        '''
        local a = {}
        a[1] = {ok="Testing"}
        return a
        ''',
        0
    )
    assert val == [b'Testing']


def test_eval_return_ok_wrong_type(r):
    with pytest.raises(redis.ResponseError):
        r.eval('return redis.status_reply(123)', 0)


def test_eval_pcall(r):
    val = r.eval(
        '''
        local a = {}
        a[1] = redis.pcall("foo")
        return a
        ''',
        0
    )
    assert isinstance(val, list)
    assert len(val) == 1
    assert isinstance(val[0], ResponseError)


def test_eval_pcall_return_value(r):
    with pytest.raises(ResponseError):
        r.eval('return redis.pcall("foo")', 0)


def test_eval_delete(r):
    r.set('foo', 'bar')
    val = r.get('foo')
    assert val == b'bar'
    val = r.eval('redis.call("DEL", KEYS[1])', 1, 'foo')
    assert val is None


def test_eval_exists(r):
    val = r.eval('return redis.call("exists", KEYS[1]) == 0', 1, 'foo')
    assert val == 1


def test_eval_flushdb(r):
    r.set('foo', 'bar')
    val = r.eval(
        '''
        local value = redis.call("FLUSHDB");
        return type(value) == "table" and value.ok == "OK";
        ''', 0
    )
    assert val == 1


def test_eval_flushall(r, create_redis):
    r1 = create_redis(db=0)
    r2 = create_redis(db=1)

    r1['r1'] = 'r1'
    r2['r2'] = 'r2'

    val = r.eval(
        '''
        local value = redis.call("FLUSHALL");
        return type(value) == "table" and value.ok == "OK";
        ''', 0
    )

    assert val == 1
    assert 'r1' not in r1
    assert 'r2' not in r2


def test_eval_incrbyfloat(r):
    r.set('foo', 0.5)
    val = r.eval(
        '''
        local value = redis.call("INCRBYFLOAT", KEYS[1], 2.0);
        return type(value) == "string" and tonumber(value) == 2.5;
        ''', 1, 'foo'
    )
    assert val == 1


def test_eval_lrange(r):
    r.rpush('foo', 'a', 'b')
    val = r.eval(
        '''
        local value = redis.call("LRANGE", KEYS[1], 0, -1);
        return type(value) == "table" and value[1] == "a" and value[2] == "b";
        ''', 1, 'foo'
    )
    assert val == 1


def test_eval_ltrim(r):
    r.rpush('foo', 'a', 'b', 'c', 'd')
    val = r.eval(
        '''
        local value = redis.call("LTRIM", KEYS[1], 1, 2);
        return type(value) == "table" and value.ok == "OK";
        ''', 1, 'foo'
    )
    assert val == 1
    assert r.lrange('foo', 0, -1) == [b'b', b'c']


def test_eval_lset(r):
    r.rpush('foo', 'a', 'b')
    val = r.eval(
        '''
        local value = redis.call("LSET", KEYS[1], 0, "z");
        return type(value) == "table" and value.ok == "OK";
        ''', 1, 'foo'
    )
    assert val == 1
    assert r.lrange('foo', 0, -1) == [b'z', b'b']


def test_eval_sdiff(r):
    r.sadd('foo', 'a', 'b', 'c', 'f', 'e', 'd')
    r.sadd('bar', 'b')
    val = r.eval(
        '''
        local value = redis.call("SDIFF", KEYS[1], KEYS[2]);
        if type(value) ~= "table" then
            return redis.error_reply(type(value) .. ", should be table");
        else
            return value;
        end
        ''', 2, 'foo', 'bar')
    # Note: while fakeredis sorts the result when using Lua, this isn't
    # actually part of the redis contract (see
    # https://github.com/antirez/redis/issues/5538), and for Redis 5 we
    # need to sort val to pass the test.
    assert sorted(val) == [b'a', b'c', b'd', b'e', b'f']


def test_script(r):
    script = r.register_script('return ARGV[1]')
    result = script(args=[42])
    assert result == b'42'


@fake_only
def test_lua_log(r, caplog):
    logger = fakeredis._server.LOGGER
    script = """
        redis.log(redis.LOG_DEBUG, "debug")
        redis.log(redis.LOG_VERBOSE, "verbose")
        redis.log(redis.LOG_NOTICE, "notice")
        redis.log(redis.LOG_WARNING, "warning")
    """
    script = r.register_script(script)
    with caplog.at_level('DEBUG'):
        script()
    assert caplog.record_tuples == [
        (logger.name, logging.DEBUG, 'debug'),
        (logger.name, logging.INFO, 'verbose'),
        (logger.name, logging.INFO, 'notice'),
        (logger.name, logging.WARNING, 'warning')
    ]


def test_lua_log_no_message(r):
    script = "redis.log(redis.LOG_DEBUG)"
    script = r.register_script(script)
    with pytest.raises(redis.ResponseError):
        script()


@fake_only
def test_lua_log_different_types(r, caplog):
    logger = fakeredis._server.LOGGER
    script = "redis.log(redis.LOG_DEBUG, 'string', 1, true, 3.14, 'string')"
    script = r.register_script(script)
    with caplog.at_level('DEBUG'):
        script()
    assert caplog.record_tuples == [
        (logger.name, logging.DEBUG, 'string 1 3.14 string')
    ]


def test_lua_log_wrong_level(r):
    script = "redis.log(10, 'string')"
    script = r.register_script(script)
    with pytest.raises(redis.ResponseError):
        script()


@fake_only
def test_lua_log_defined_vars(r, caplog):
    logger = fakeredis._server.LOGGER
    script = """
        local var='string'
        redis.log(redis.LOG_DEBUG, var)
    """
    script = r.register_script(script)
    with caplog.at_level('DEBUG'):
        script()
    assert caplog.record_tuples == [(logger.name, logging.DEBUG, 'string')]
