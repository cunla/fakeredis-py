from __future__ import annotations

import functools
import math
import operator
import string
import sys
from dataclasses import dataclass
from typing import Any

import hypothesis.strategies as st
import pytest
import redis
import valkey
from hypothesis import settings
from hypothesis.stateful import RuleBasedStateMachine, initialize, precondition, rule, run_state_machine_as_test
from hypothesis.strategies import SearchStrategy

import fakeredis

# ---------------------------------------------------------------------------
# Runtime configuration
#
# Hypothesis state machines and strategies cannot receive pytest fixtures, so
# the ``hypothesis_config`` fixture (see conftest.py) hands the server details
# to ``run_machine``, which publishes them here for the duration of a single
# machine run. Strategies read this lazily (at draw time), so importing this
# module never touches the network.
# ---------------------------------------------------------------------------

_REAL_CLIENT_CLASSES = {
    "redis": redis.StrictRedis,
    "dragonfly": redis.StrictRedis,
    "valkey": valkey.StrictValkey,
}
_FAKE_CLIENT_CLASSES = {
    "redis": fakeredis.FakeStrictRedis,
    "dragonfly": fakeredis.FakeStrictRedis,
    "valkey": fakeredis.FakeValkey,
}


@dataclass
class MachineConfig:
    """Everything a state machine needs to talk to both servers."""

    server_type: str
    version: tuple[int, ...]
    host: str = "localhost"
    port: int = 6390
    db: int = 2

    def make_real_client(self) -> redis.Redis:
        cls = _REAL_CLIENT_CLASSES.get(self.server_type, redis.StrictRedis)
        return cls(self.host, port=self.port, db=self.db)

    def make_fake_client(self) -> redis.Redis:
        cls = _FAKE_CLIENT_CLASSES.get(self.server_type, fakeredis.FakeStrictRedis)
        server = fakeredis.FakeServer(server_type=self.server_type, version=self.version)
        return cls(server=server, db=self.db)


_active_config: MachineConfig | None = None


def _server_version() -> tuple[int, ...]:
    return _active_config.version if _active_config is not None else (7,)


def _floats_kwargs() -> dict:
    # Dragonfly rejects the float edge cases that Redis accepts.
    if _active_config is not None and _active_config.server_type == "dragonfly":
        return {"allow_nan": False, "allow_subnormal": False, "allow_infinity": False}
    return {}


self_strategy = st.runner()


@st.composite
def sample_attr(draw, name):
    """Strategy for sampling a specific attribute from a state machine"""
    machine = draw(self_strategy)
    values = getattr(machine, name)
    position = draw(st.integers(min_value=0, max_value=len(values) - 1))
    return values[position]


keys = sample_attr("keys")
fields = sample_attr("fields")
values = sample_attr("values")
scores = sample_attr("scores")

eng_text = st.builds(lambda x: x.encode(), st.text(alphabet=string.ascii_letters, min_size=1))
ints = st.integers(min_value=-2_147_483_648, max_value=2_147_483_647)
int_as_bytes = st.builds(lambda x: str(default_normalize(x)).encode(), ints)
# ``floats`` is deferred so the dragonfly-specific exclusions resolve at draw
# time from the active config rather than at import time.
floats = st.deferred(lambda: st.floats(width=32, **_floats_kwargs()))
float_as_bytes = st.builds(lambda x: repr(default_normalize(x)).encode(), floats)
counts = st.integers(min_value=-3, max_value=3) | ints
# Redis has an integer overflow bug in swapdb, so we confine the numbers to
# a limited range (https://github.com/antirez/redis/issues/5737).
dbnums = st.integers(min_value=0, max_value=3) | st.integers(min_value=-1000, max_value=1000)
# The filter is to work around https://github.com/antirez/redis/issues/5632
patterns = st.text(alphabet=st.sampled_from("[]^$*.?-azAZ\\\r\n\t")) | st.binary().filter(lambda x: b"\0" not in x)
string_tests = st.sampled_from([b"+", b"-"]) | st.builds(operator.add, st.sampled_from([b"(", b"["]), fields)
# Redis has integer overflow bugs in time computations, which is why we set a maximum.
expires_seconds = st.integers(min_value=5, max_value=1_000)
expires_ms = st.integers(min_value=5_000, max_value=50_000)


class WrappedException:
    """Wraps an exception for comparison."""

    def __init__(self, exc):
        self.wrapped = exc

    def __str__(self):
        return str(self.wrapped)

    def __repr__(self):
        return f"WrappedException({self.wrapped!r})"

    def __eq__(self, other):
        if not isinstance(other, WrappedException):
            return NotImplemented
        return type(self.wrapped) is type(other.wrapped)


def wrap_exceptions(obj):
    if isinstance(obj, list):
        return [wrap_exceptions(item) for item in obj]
    elif isinstance(obj, Exception):
        return WrappedException(obj)
    else:
        return obj


def sort_list(lst):
    if isinstance(lst, list):
        return sorted(lst)
    else:
        return lst


def normalize_if_number(x):
    if isinstance(x, list):
        return [normalize_if_number(item) for item in x]
    try:
        res = float(x)
        return x if math.isnan(res) else res
    except ValueError:
        return x


def flatten(args):
    if isinstance(args, (list, tuple)):
        for arg in args:
            yield from flatten(arg)
    elif args is not None:
        yield args


def default_normalize(x: Any) -> Any:
    if _server_version() >= (7,) and isinstance(x, (int, float)):
        return 0 + x
    return x


def optional(arg: Any) -> st.SearchStrategy:
    return st.none() | st.just(arg)


def zero_or_more(*args: Any):
    return [optional(arg) for arg in args]


class Command:
    def __init__(self, *args):
        args = list(flatten(args))
        args = [default_normalize(x) for x in args]
        self.args = tuple(args)

    def __repr__(self):
        parts = [repr(arg) for arg in self.args]
        return "Command({})".format(", ".join(parts))

    @staticmethod
    def encode(arg):
        encoder = redis.connection.Encoder("utf-8", "replace", False)
        return encoder.encode(arg)

    @property
    def normalize(self):
        command = self.encode(self.args[0]).lower() if self.args else None
        # Functions that return a list in arbitrary order
        unordered = {
            b"keys",
            b"sort",
            b"hgetall",
            b"hkeys",
            b"hvals",
            b"sdiff",
            b"sinter",
            b"sunion",
            b"smembers",
            b"hexpire",
        }
        if command in unordered:
            return sort_list
        else:
            return normalize_if_number

    @property
    def testable(self):
        """Whether this command is suitable for a test.

        The fuzzer can create commands with behavior that is non-deterministic, not supported, or which hits redis bugs.
        """
        N = len(self.args)
        if N == 0:
            return False
        command = self.encode(self.args[0]).lower()
        if not command.split():
            return False
        if command == b"keys" and N == 2 and self.args[1] != b"*":
            return False
        # Redis will ignore a NULL character in some commands but not others,
        # e.g., it recognizes EXEC\0 but not MULTI\00.
        # Rather than try to reproduce this quirky behavior, just skip these tests.
        return b"\x00" not in command


def commands(*args, **kwargs):
    return st.builds(functools.partial(Command, **kwargs), *args)


# # TODO: all expiry-related commands
common_commands = (
    commands(st.sampled_from(["del", "persist", "type", "unlink"]), keys)
    | commands(st.just("exists"), st.lists(keys))
    | commands(st.just("keys"), st.just("*"))
    # Disabled for now due to redis giving wrong answers
    # (https://github.com/antirez/redis/issues/5632)
    # | commands(st.just('keys'), patterns)
    | commands(st.just("move"), keys, dbnums)
    | commands(st.sampled_from(["rename", "renamenx"]), keys, keys)
    # TODO: find a better solution to sort instability than throwing
    #  away the sort entirely with normalize. This also prevents us
    #  using LIMIT.
    | commands(st.just("sort"), keys, *zero_or_more("asc", "desc", "alpha"))
)


class BaseMachine(RuleBasedStateMachine):
    """Fuzzes command sequences, asserting fake and real servers agree.

    Subclasses provide the strategy building blocks below; ``run_machine``
    binds a :class:`MachineConfig` and executes the machine as a test.
    """

    #: Commands exercised against every server.
    base_commands: SearchStrategy = st.nothing()
    #: Commands used to populate initial data before the main rules run.
    create_commands: SearchStrategy = st.nothing()
    #: Commands only real Redis (not valkey/dragonfly) supports.
    redis_only_commands: SearchStrategy = st.nothing()
    #: Commands only Redis 7+ supports.
    redis7_commands: SearchStrategy = st.nothing()

    def __init__(self):
        super().__init__()
        config = _active_config
        assert config is not None, "BaseMachine must be run via run_machine()"
        self.real = config.make_real_client()
        self.fake = config.make_fake_client()
        # Disable the response parsing so that we can check the raw values returned
        self.fake.response_callbacks.clear()
        self.real.response_callbacks.clear()
        self.transaction_normalize = []
        self.keys = []
        self.fields = []
        self.values = []
        self.scores = []
        self.initialized_data = False
        try:
            self.real.execute_command("discard")
        except redis.ResponseError:
            pass
        self.real.flushall()

        # Resolve the command strategies for this server once, up front. The
        # rules below read these instance attributes at draw time.
        self.create_command_strategy = self.create_commands
        self.command_strategy = self.base_commands | common_commands
        if config.server_type == "redis":
            self.command_strategy |= self.redis_only_commands
            if config.version >= (7,):
                self.command_strategy |= self.redis7_commands

    def teardown(self):
        self.real.connection_pool.disconnect()
        self.fake.connection_pool.disconnect()
        super().teardown()

    @staticmethod
    def _evaluate(client, command):
        try:
            result = client.execute_command(*command.args)
            if result != "QUEUED":
                result = command.normalize(result)
            exc = None
        except Exception as e:
            result = exc = e
        return wrap_exceptions(result), exc

    def _compare(self, command):
        fake_result, fake_exc = self._evaluate(self.fake, command)
        real_result, real_exc = self._evaluate(self.real, command)

        if fake_exc is not None and real_exc is None:
            print(f"{fake_exc} raised on only on fake when running {command}", file=sys.stderr)
            raise fake_exc
        elif real_exc is not None and fake_exc is None:
            assert real_exc == fake_exc, f"Expected exception `{real_exc}` not raised when running {command}"
        elif real_exc is None and isinstance(real_result, list) and command.args and command.args[0].lower() == "exec":
            assert fake_result is not None
            # Transactions need to use the normalize functions of the
            # component commands.
            assert len(self.transaction_normalize) == len(real_result)
            assert len(self.transaction_normalize) == len(fake_result)
            for n, r, f in zip(self.transaction_normalize, real_result, fake_result):
                assert n(f) == n(r)
            self.transaction_normalize = []
        elif isinstance(fake_result, list):
            assert len(fake_result) == len(real_result), (
                f"Discrepancy when running command {command}, fake({fake_result}) != real({real_result})",
            )
            for i in range(len(fake_result)):
                assert fake_result[i] == real_result[i] or (
                    type(fake_result[i]) is float and fake_result[i] == pytest.approx(real_result[i])
                ), f"Discrepancy when running command {command}, fake({fake_result}) != real({real_result})"

        else:
            assert fake_result == real_result or (
                type(fake_result) is float and fake_result == pytest.approx(real_result)
            ), f"Discrepancy when running command {command}, fake({fake_result}) != real({real_result})"
            if real_result == b"QUEUED":
                # Since redis removes the distinction between simple strings and
                # bulk strings, this might not actually indicate that we're in a
                # transaction. But it is extremely unlikely that hypothesis will
                # find such examples.
                self.transaction_normalize.append(command.normalize)
        if len(command.args) == 1 and Command.encode(command.args[0]).lower() in (b"discard", b"exec"):
            self.transaction_normalize = []

    @initialize(
        attrs=st.fixed_dictionaries(
            {
                "keys": st.lists(eng_text, min_size=2, max_size=5, unique=True),
                "fields": st.lists(eng_text, min_size=2, max_size=5, unique=True),
                "values": st.lists(eng_text | int_as_bytes | float_as_bytes, min_size=2, max_size=5, unique=True),
                "scores": st.lists(floats, min_size=2, max_size=5, unique=True),
            }
        )
    )
    def init_attrs(self, attrs):
        for key, value in attrs.items():
            setattr(self, key, value)

    # hypothesis doesn't allow ordering of @initialize, so we have to put
    # preconditions on rules to ensure we call init_data exactly once and
    # after init_attrs.
    @precondition(lambda self: not self.initialized_data)
    @rule(commands=self_strategy.flatmap(lambda self: st.lists(self.create_command_strategy)))
    def init_data(self, commands):
        for command in commands:
            self._compare(command)
        self.initialized_data = True

    @precondition(lambda self: self.initialized_data)
    @rule(command=self_strategy.flatmap(lambda self: self.command_strategy))
    def one_command(self, command):
        self._compare(command)


def run_machine(machine_cls: type[BaseMachine], config: MachineConfig) -> None:
    """Run ``machine_cls`` as a Hypothesis test against ``config``'s servers."""
    global _active_config
    _active_config = config
    try:
        run_state_machine_as_test(machine_cls, settings=settings())
    finally:
        _active_config = None
