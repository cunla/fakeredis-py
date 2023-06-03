from __future__ import annotations

import pytest
import redis
import redis.client

from test.testtools import raw_command


@pytest.mark.min_server('7')
def test_script_exists_redis7(r: redis.Redis):
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


@pytest.mark.max_server('6.2.7')
def test_script_exists_redis6(r: redis.Redis):
    # test response for no arguments by bypassing the py-redis command
    # as it requires at least one argument
    assert raw_command(r, "SCRIPT EXISTS") == []

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


@pytest.mark.parametrize("args", [("a",), tuple("abcdefghijklmn")])
def test_script_flush_errors_with_args(r, args):
    with pytest.raises(redis.ResponseError):
        raw_command(r, "SCRIPT FLUSH %s" % " ".join(args))


def test_script_flush(r: redis.Redis):
    # generate/load six unique scripts and store their sha1 hash values
    sha1_values = [r.script_load("return '%s'" % char) for char in "abcdef"]

    # assert the scripts all exist prior to flushing
    assert r.script_exists(*sha1_values) == [1] * len(sha1_values)

    # flush and assert OK response
    assert r.script_flush() is True

    # assert none of the scripts exists after flushing
    assert r.script_exists(*sha1_values) == [0] * len(sha1_values)


def test_script_no_subcommands(r: redis.Redis):
    with pytest.raises(redis.ResponseError):
        raw_command(r, "SCRIPT")


@pytest.mark.max_server('7')
def test_script_help(r: redis.Redis):
    assert raw_command(r, "SCRIPT HELP") == [
        b'SCRIPT <subcommand> [<arg> [value] [opt] ...]. Subcommands are:',
        b'DEBUG (YES|SYNC|NO)',
        b'    Set the debug mode for subsequent scripts executed.',
        b'EXISTS <sha1> [<sha1> ...]',
        b'    Return information about the existence of the scripts in the script cach'
        b'e.',
        b'FLUSH [ASYNC|SYNC]',
        b'    Flush the Lua scripts cache. Very dangerous on replicas.',
        b'    When called without the optional mode argument, the behavior is determin'
        b'ed by the',
        b'    lazyfree-lazy-user-flush configuration directive. Valid modes are:',
        b'    * ASYNC: Asynchronously flush the scripts cache.',
        b'    * SYNC: Synchronously flush the scripts cache.',
        b'KILL',
        b'    Kill the currently executing Lua script.',
        b'LOAD <script>',
        b'    Load a script into the scripts cache without executing it.',
        b'HELP',
        b'    Prints this help.'
    ]


@pytest.mark.min_server('7.1')
def test_script_help71(r: redis.Redis):
    assert raw_command(r, "SCRIPT HELP") == [
        b'SCRIPT <subcommand> [<arg> [value] [opt] ...]. Subcommands are:',
        b'DEBUG (YES|SYNC|NO)',
        b'    Set the debug mode for subsequent scripts executed.',
        b'EXISTS <sha1> [<sha1> ...]',
        b'    Return information about the existence of the scripts in the script cach'
        b'e.',
        b'FLUSH [ASYNC|SYNC]',
        b'    Flush the Lua scripts cache. Very dangerous on replicas.',
        b'    When called without the optional mode argument, the behavior is determin'
        b'ed by the',
        b'    lazyfree-lazy-user-flush configuration directive. Valid modes are:',
        b'    * ASYNC: Asynchronously flush the scripts cache.',
        b'    * SYNC: Synchronously flush the scripts cache.',
        b'KILL',
        b'    Kill the currently executing Lua script.',
        b'LOAD <script>',
        b'    Load a script into the scripts cache without executing it.',
        b'HELP',
        b'    Print this help.'
    ]
