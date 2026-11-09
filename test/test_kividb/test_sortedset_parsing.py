"""How KiviDB reads the arguments of its sorted set commands.

Since KiviDB 1.2.0 these follow redis, which the tests in `test/test_mixins` check on KiviDB too. The one
divergence left is how a short WEIGHTS list is reported.
"""

from __future__ import annotations

import pytest

from fakeredis._typing import ClientType
from test.testtools import raw_command

pytestmark = [pytest.mark.unsupported_server_types("redis", "valkey", "dragonfly")]


@pytest.fixture
def two_sets(r: ClientType) -> ClientType:
    r.zadd("x", {"m": 1})
    r.zadd("y", {"m": 2})
    return r


@pytest.mark.parametrize(
    "command,args",
    [
        ("zinterstore", ("dest", 2, "x", "y")),
        ("zunionstore", ("dest", 2, "x", "y")),
        ("zinter", (2, "x", "y")),
        ("zunion", (2, "x", "y")),
    ],
)
@pytest.mark.parametrize("weights", [("weights",), ("weights", 1), ("WeIgHtS", 1)])
def test_weights_that_run_out_of_arguments(two_sets: ClientType, command: str, args: tuple, weights: tuple):
    """Redis answers a syntax error; KiviDB complains about the weight."""
    with pytest.raises(Exception, match="weight value is not a float"):
        raw_command(two_sets, command, *args, *weights)


def test_weights_errors_shared_with_redis(two_sets: ClientType):
    # A weight that is there but not a float, and one weight too many, are reported as on redis.
    with pytest.raises(Exception, match="weight value is not a float"):
        raw_command(two_sets, "zinterstore", "dest", 2, "x", "y", "weights", "x", 1)
    with pytest.raises(Exception, match="syntax error"):
        raw_command(two_sets, "zinterstore", "dest", 2, "x", "y", "weights", 1, 2, 3)
    # ZDIFFSTORE takes no WEIGHTS at all, so even a short one is a syntax error there.
    with pytest.raises(Exception, match="syntax error"):
        raw_command(two_sets, "zdiffstore", "dest", 2, "x", "y", "weights", 1)
