import pytest as pytest
import redis

from testtools import raw_command, zadd


@pytest.mark.min_server('7')
def test_script_exists(r):
    # test response for no arguments by bypassing the py-redis command
    # as it requires at least one argument
    with pytest.raises(redis.ResponseError):
        raw_command(r, "SCRIPT EXISTS")

    # use single character characters for non-existing scripts, as those
    # will never be equal to an actual sha1 hash digest
    assert r.script_exists("a") == [0]
    assert r.script_exists("a", "b", "c", "d", "e", "f") == [0, 0, 0, 0, 0, 0]

    sha1_one = r.script_load("return 'a'")
    assert r.script_exists(sha1_one) == [1]
    assert r.script_exists(sha1_one, "a") == [1, 0]
    assert r.script_exists("a", "b", "c", sha1_one, "e") == [0, 0, 0, 1, 0]

    sha1_two = r.script_load("return 'b'")
    assert r.script_exists(sha1_one, sha1_two) == [1, 1]
    assert r.script_exists("a", sha1_one, "c", sha1_two, "e", "f") == [0, 1, 0, 1, 0, 0]


@pytest.mark.min_server('7')
def test_set_get_nx(r):
    # Note: this will most likely fail on a 7.0 server, based on the docs for SET
    assert raw_command(r, 'set', 'foo', 'bar', 'NX', 'GET') is None


@pytest.mark.min_server('7.0')
def test_zadd_minus_zero(r):
    zadd(r, 'foo', {'a': -0.0})
    zadd(r, 'foo', {'a': 0.0})
    assert raw_command(r, 'zscore', 'foo', 'a') == b'0'
