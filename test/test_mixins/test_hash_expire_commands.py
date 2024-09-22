from typing import Optional, Dict

import pytest
import redis.client

from test import testtools

testtools.run_test_if_redispy_ver("gte", "5")


@pytest.mark.min_server("7.4")
@pytest.mark.parametrize(
    "expiration_seconds,preset_expiration,flags,expected_result",
    [
        # No flags
        (100, None, dict(), 1),
        (100, 50, dict(), 1),
        # NX
        (100, None, dict(nx=True), 1),
        (100, 50, dict(nx=True), 0),
        # XX
        (100, None, dict(xx=True), 0),
        (100, 50, dict(xx=True), 1),
        # GT
        (100, None, dict(gt=True), 0),
        (100, 50, dict(gt=True), 1),
        (100, 100, dict(gt=True), 0),
        (100, 200, dict(gt=True), 0),
        # LT
        (100, None, dict(lt=True), 1),
        (100, 50, dict(lt=True), 0),
        (100, 100, dict(lt=True), 0),
        (100, 200, dict(lt=True), 1),
    ],
)
def test_hexpire(
    r: redis.Redis,
    expiration_seconds: int,
    preset_expiration: Optional[int],
    flags: Dict[str, bool],
    expected_result: int,
) -> None:
    key, field = "redis-key", "hash-key"
    r.hset(key, field, "value")
    if preset_expiration is not None:
        assert r.hexpire(key, preset_expiration, field) == [1]
    result = r.hexpire(key, expiration_seconds, field, **flags)
    assert result == [expected_result]
