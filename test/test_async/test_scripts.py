import pytest
import redis
import redis.asyncio
import valkey

from fakeredis._typing import AsyncClientType
from test import testtools

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.asyncio,
    ]
)


@testtools.run_test_if_lupa
class TestScripts:
    async def test_no_script_error(self, async_redis: AsyncClientType):
        with pytest.raises(Exception) as exc_info:
            await async_redis.evalsha("0123456789abcdef0123456789abcdef", 0)
        assert isinstance(exc_info.value, (redis.exceptions.NoScriptError, valkey.exceptions.NoScriptError))

    @pytest.mark.supported_server_versions(max_redis_ver="6.2.7")
    @pytest.mark.unsupported_server_types("valkey")
    async def test_failed_script_error6(self, async_redis):
        await async_redis.set("foo", "bar")
        with pytest.raises(Exception, match="^Error running script") as ctx:
            await async_redis.eval('return redis.call("ZCOUNT", KEYS[1])', 1, "foo")

        assert isinstance(ctx.value, (redis.asyncio.ResponseError, valkey.asyncio.ResponseError))

    @pytest.mark.supported_server_versions(min_redis_ver="7")
    async def test_failed_script_error7(self, async_redis):
        await async_redis.set("foo", "bar")
        with pytest.raises(Exception) as exc_info:
            await async_redis.eval('return redis.call("ZCOUNT", KEYS[1])', 1, "foo")
        assert isinstance(exc_info.value, (redis.asyncio.ResponseError, valkey.asyncio.ResponseError))
