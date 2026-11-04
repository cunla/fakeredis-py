"""Tests for the time series commands and arguments added in redis 8.10: TS.QUERYLABELS, TS.NRANGE/TS.NREVRANGE, TS.READ
and TS.MRANGE/TS.MREVRANGE EXCLUDEEMPTY."""

import math
import threading
from time import sleep

import pytest
import redis

from fakeredis._typing import ClientType
from test.testtools import get_protocol_version, raw_command

timeseries_tests = pytest.importorskip("probables")

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.supported_server_versions(min_redis_ver="8.10"),
        pytest.mark.unsupported_server_types("dragonfly", "valkey", "kividb"),
    ]
)


def _value(v):
    """A sample value as a float, or "nan": RESP2 sends values as bulk strings (NaN as `NaN`), RESP3 as doubles."""
    f = float(v)
    return "nan" if math.isnan(f) else f


def _samples(res) -> list:
    """Normalize TS.READ-style [timestamp, value] rows."""
    return [[t, _value(v)] for t, v in res]


def _rows(res) -> list:
    """Normalize TS.NRANGE-style [timestamp, [value, ...]] rows."""
    return [[t, [_value(v) for v in values]] for t, values in res]


@pytest.fixture
def labelled(r: ClientType) -> ClientType:
    raw_command(r, "TS.CREATE", "study:temp", "LABELS", "room", "study", "type", "temperature")
    raw_command(r, "TS.CREATE", "study:hum", "LABELS", "room", "study", "type", "humidity")
    raw_command(r, "TS.CREATE", "kitchen:temp", "LABELS", "room", "kitchen", "type", "temperature", "floor", "1")
    raw_command(r, "TS.CREATE", "unlabelled")
    return r


@pytest.fixture
def sample(r: ClientType) -> ClientType:
    raw_command(r, "TS.CREATE", "a", "LABELS", "room", "study")
    raw_command(r, "TS.CREATE", "b", "LABELS", "room", "kitchen")
    raw_command(r, "TS.CREATE", "c", "LABELS", "room", "kitchen")
    raw_command(r, "TS.MADD", "a", 1000, 10, "a", 2000, 12, "a", 2500, 13, "b", 1000, 20, "b", 3000, 25)
    return r


def _querylabels(r: ClientType, *args) -> list:
    return sorted(raw_command(r, "TS.QUERYLABELS", *args))


def test_ts_querylabels(labelled: ClientType):
    assert _querylabels(labelled, "LABELS") == [b"floor", b"room", b"type"]
    assert _querylabels(labelled, "LABELS", "FILTER", "room=study") == [b"room", b"type"]
    assert _querylabels(labelled, "VALUES", "type") == [b"humidity", b"temperature"]
    assert _querylabels(labelled, "values", "room", "filter", "type=temperature") == [b"kitchen", b"study"]
    assert _querylabels(labelled, "VALUES", "missing") == []
    assert _querylabels(labelled, "VALUES", "room", "FILTER", "room=cellar") == []
    # `label=` selects the series without that label, `label!=` those with it.
    assert _querylabels(labelled, "VALUES", "room", "FILTER", "type=temperature", "floor=") == [b"study"]
    assert _querylabels(labelled, "VALUES", "room", "FILTER", "type=temperature", "floor!=") == [b"kitchen"]
    assert _querylabels(labelled, "VALUES", "type", "FILTER", "room=(study,kitchen)", "type!=humidity") == [
        b"temperature"
    ]


def test_ts_querylabels_resp3_set(labelled: ClientType):
    if get_protocol_version(labelled) != 3:
        pytest.skip("RESP3 only")
    assert set(raw_command(labelled, "TS.QUERYLABELS", "LABELS")) == {b"floor", b"room", b"type"}


def test_ts_querylabels_errors(labelled: ClientType):
    for args, message in [
        (("VALUES",), "wrong number of arguments for 'ts.querylabels' command"),
        (("FOO",), "TSDB: unknown subtype, must be one of LABELS|VALUES"),
        (("LABELS", "extra"), "TSDB: unknown argument, expected FILTER"),
        (("VALUES", "room", "extra"), "TSDB: unknown argument, expected FILTER"),
        (("LABELS", "FILTER"), "TSDB: FILTER given with no filter expressions"),
        (("LABELS", "FILTER", "bad"), "TSDB: failed parsing labels"),
        (("LABELS", "FILTER", "room!=study"), "TSDB: please provide at least one matcher"),
        (("LABELS", "FILTER", "room="), "TSDB: please provide at least one matcher"),
    ]:
        with pytest.raises(redis.ResponseError) as ctx:
            raw_command(labelled, "TS.QUERYLABELS", *args)
        assert str(ctx.value) == message


def test_ts_nrange(sample: ClientType):
    nan = "nan"
    assert _rows(raw_command(sample, "TS.NRANGE", 2, "a", "b", "-", "+")) == [
        [1000, [10.0, 20.0]],
        [2000, [12.0, nan]],
        [2500, [13.0, nan]],
        [3000, [nan, 25.0]],
    ]
    assert _rows(raw_command(sample, "TS.NREVRANGE", 2, "a", "b", "-", "+")) == [
        [3000, [nan, 25.0]],
        [2500, [13.0, nan]],
        [2000, [12.0, nan]],
        [1000, [10.0, 20.0]],
    ]
    assert _rows(raw_command(sample, "TS.NRANGE", 2, "a", "b", 1500, 2600)) == [
        [2000, [12.0, nan]],
        [2500, [13.0, nan]],
    ]
    assert raw_command(sample, "TS.NRANGE", 1, "a", 2000, 1000) == []
    assert raw_command(sample, "TS.NRANGE", 1, "c", "-", "+") == []
    # A repeated key contributes a value per occurrence; COUNT applies to the joined rows.
    assert _rows(raw_command(sample, "TS.NRANGE", 2, "a", "a", "-", "+", "COUNT", 2)) == [
        [1000, [10.0, 10.0]],
        [2000, [12.0, 12.0]],
    ]
    assert _rows(raw_command(sample, "TS.NREVRANGE", 2, "a", "b", "-", "+", "COUNT", 2)) == [
        [3000, [nan, 25.0]],
        [2500, [13.0, nan]],
    ]
    # The filters apply to each series before the join.
    assert _rows(raw_command(sample, "TS.NRANGE", 2, "a", "b", "-", "+", "FILTER_BY_VALUE", 11, 21)) == [
        [1000, [nan, 20.0]],
        [2000, [12.0, nan]],
        [2500, [13.0, nan]],
    ]
    assert _rows(raw_command(sample, "TS.NRANGE", 2, "a", "b", "-", "+", "FILTER_BY_TS", 1000, 3000)) == [
        [1000, [10.0, 20.0]],
        [3000, [nan, 25.0]],
    ]


def test_ts_nrange_resp2_nan(sample: ClientType):
    if get_protocol_version(sample) != 2:
        pytest.skip("RESP2 only")
    assert raw_command(sample, "TS.NRANGE", 2, "a", "b", 3000, 3000) == [[3000, [b"NaN", b"25"]]]


def test_ts_nrange_aggregation(sample: ClientType):
    nan = "nan"
    # One aggregator argument per key, in key order, sharing the bucket duration.
    assert _rows(raw_command(sample, "TS.NRANGE", 2, "a", "b", "-", "+", "AGGREGATION", "avg", "sum", 1000)) == [
        [1000, [10.0, 20.0]],
        [2000, [12.5, nan]],
        [3000, [nan, 25.0]],
    ]
    # A comma-separated list gives a key a value per aggregator.
    assert _rows(raw_command(sample, "TS.NRANGE", 2, "a", "b", "-", "+", "AGGREGATION", "avg,max", "count", 1000)) == [
        [1000, [10.0, 10.0, 1.0]],
        [2000, [12.5, 13.0, nan]],
        [3000, [nan, nan, 1.0]],
    ]
    # EMPTY reports the empty buckets inside a series' own range; sum reports 0 for them.
    res = raw_command(sample, "TS.NREVRANGE", 2, "a", "b", "-", "+", "AGGREGATION", "sum", "sum", 1000, "EMPTY")
    assert _rows(res) == [[3000, [nan, 25.0]], [2000, [25.0, 0.0]], [1000, [10.0, 20.0]]]
    res = raw_command(sample, "TS.NRANGE", 1, "a", "-", "+", "AGGREGATION", "sum", 1000, "BUCKETTIMESTAMP", "+")
    assert _rows(res) == [[2000, [10.0]], [3000, [25.0]]]
    res = raw_command(sample, "TS.NRANGE", 1, "a", "-", "+", "ALIGN", 500, "AGGREGATION", "sum", 1000)
    assert _rows(res) == [[500, [10.0]], [1500, [12.0]], [2500, [13.0]]]


def test_ts_nrange_errors(sample: ClientType):
    sample.set("str", "value")
    for args, message in [
        ((0, "-", "+"), "wrong number of arguments for 'ts.nrange' command"),
        ((3, "a", "b", "-", "+"), "wrong number of arguments for 'ts.nrange' command"),
        (("x", "a", "-", "+"), "TSDB: numkeys must be a positive integer"),
        ((-1, "a", "-", "+"), "TSDB: numkeys must be a positive integer"),
        ((1, "a", "x", "+"), "TSDB: wrong fromTimestamp"),
        ((1, "a", "-", "+", "COUNT", 0), "TSDB: Invalid COUNT value"),
        ((1, "a", "-", "+", "AGGREGATION", "sum"), "TSDB: Couldn't parse AGGREGATION"),
        (
            (2, "a", "b", "-", "+", "AGGREGATION", "avg", 1000),
            "TSDB: the number of AGGREGATION arguments must be equal to numkeys",
        ),
        ((2, "a", "b", "-", "+", "AGGREGATION", "avg", "foo", 1000), "TSDB: Unknown aggregation type"),
        ((2, "a", "b", "-", "+", "AGGREGATION", "sum", "sum", 0), "TSDB: bucketDuration must be greater than zero"),
        ((1, "a", "-", "+", "FILTER_BY_TS"), "TSDB: FILTER_BY_TS one or more arguments are missing"),
        ((2, "a", "missing", "-", "+"), "TSDB: the key does not exist"),
        ((2, "missing", "str", "-", "+"), "TSDB: the key does not exist"),
        ((2, "str", "missing", "-", "+"), "WRONGTYPE Operation against a key holding the wrong kind of value"),
    ]:
        with pytest.raises(redis.ResponseError) as ctx:
            raw_command(sample, "TS.NRANGE", *args)
        assert str(ctx.value) == message, args


def _mrange_names(res) -> list:
    return [series[0] for series in res] if isinstance(res, list) else list(res)


def test_ts_mrange_excludeempty(sample: ClientType):
    names = ["a", "b", "c"]
    filters = ("FILTER", "room=(study,kitchen)")
    assert _mrange_names(raw_command(sample, "TS.MRANGE", 2000, 2600, *filters)) == [n.encode() for n in names]
    assert _mrange_names(raw_command(sample, "TS.MRANGE", 2000, 2600, "EXCLUDEEMPTY", *filters)) == [b"a"]
    assert _mrange_names(raw_command(sample, "TS.MREVRANGE", 2000, 2600, "excludeempty", *filters)) == [b"a"]
    assert _mrange_names(raw_command(sample, "TS.MRANGE", "-", "+", "WITHLABELS", "EXCLUDEEMPTY", *filters)) == [
        b"a",
        b"b",
    ]
    # Emptiness is judged on the reply, after aggregation.
    res = raw_command(sample, "TS.MRANGE", 2000, 2600, "EXCLUDEEMPTY", "AGGREGATION", "sum", 1000, *filters)
    assert _mrange_names(res) == [b"a"]


def test_ts_mrange_excludeempty_errors(sample: ClientType):
    with pytest.raises(redis.ResponseError, match="^TSDB: EXCLUDEEMPTY is not allowed with GROUPBY$"):
        raw_command(
            sample, "TS.MRANGE", "-", "+", "EXCLUDEEMPTY", "FILTER", "room=study", "GROUPBY", "room", "REDUCE", "sum"
        )
    # After FILTER, the word is read as a filter expression.
    with pytest.raises(redis.ResponseError, match="^TSDB: failed parsing labels$"):
        raw_command(sample, "TS.MRANGE", "-", "+", "FILTER", "room=study", "EXCLUDEEMPTY")


def test_ts_read(sample: ClientType):
    everything = [[1000, 10.0], [2000, 12.0], [2500, 13.0]]
    assert _samples(raw_command(sample, "TS.READ", "a", 0)) == everything
    assert _samples(raw_command(sample, "TS.READ", "a", "-")) == everything
    assert _samples(raw_command(sample, "TS.READ", "a", 1001)) == everything[1:]
    # `+` is the latest sample, included; `$` is past it.
    assert _samples(raw_command(sample, "TS.READ", "a", "+")) == everything[2:]
    assert raw_command(sample, "TS.READ", "a", "$") == []
    assert _samples(raw_command(sample, "TS.READ", "a", "-", "MAX_COUNT", 2)) == everything[:2]
    assert _samples(raw_command(sample, "TS.READ", "a", 0, "max_count", 1, "block", 10, 1)) == everything[:1]
    assert raw_command(sample, "TS.READ", "missing", 0) == []
    assert raw_command(sample, "TS.READ", "c", "-") == []
    # A read already satisfied does not block, and does not wait for more than MAX_COUNT.
    assert _samples(raw_command(sample, "TS.READ", "a", 0, "BLOCK", 0, 2)) == everything
    # On timeout, the samples there are, however few.
    assert _samples(raw_command(sample, "TS.READ", "a", 1500, "BLOCK", 50, 5)) == everything[1:]
    assert raw_command(sample, "TS.READ", "a", "$", "BLOCK", 50, 1) == []
    assert raw_command(sample, "TS.READ", "missing", 0, "BLOCK", 50, 1) == []


def test_ts_read_errors(sample: ClientType):
    sample.set("str", "value")
    for args, message in [
        (("a", 0, "FOO"), "wrong number of arguments for 'ts.read' command"),
        (("a", 0, "MAX_COUNT"), "wrong number of arguments for 'ts.read' command"),
        (("a", 0, "BLOCK", 10), "wrong number of arguments for 'ts.read' command"),
        (("a", 0, "MAX_COUNT", 1, "MAX_COUNT", 2), "wrong number of arguments for 'ts.read' command"),
        (("a", -1), "TSDB: invalid timestamp"),
        (("a", "1.5"), "TSDB: invalid timestamp"),
        (("a", "x"), "TSDB: invalid timestamp"),
        (("a", 0, "MAX_COUNT", 0), "TSDB: MAX_COUNT must be a positive integer"),
        (("a", 0, "MAX_COUNT", "x"), "TSDB: MAX_COUNT must be a positive integer"),
        (("a", 0, "BLOCK", -1, 1), "TSDB: BLOCK milliseconds must be a non-negative integer"),
        (("a", 0, "BLOCK", "x", 1), "TSDB: BLOCK milliseconds must be a non-negative integer"),
        (("a", 0, "BLOCK", 10, "x"), "TSDB: BLOCK milliseconds must be a non-negative integer"),
        (("a", 0, "BLOCK", 10, 0), "TSDB: BLOCK min_count must be a positive integer"),
        (("a", 0, "BLOCK", 10, 3, "MAX_COUNT", 2), "TSDB: BLOCK min_count must be <= MAX_COUNT"),
        # The options are checked first, then the timestamp, then the key.
        (("a", "x", "MAX_COUNT", 0), "TSDB: MAX_COUNT must be a positive integer"),
        (("str", "x"), "TSDB: invalid timestamp"),
        (("str", 0), "WRONGTYPE Operation against a key holding the wrong kind of value"),
    ]:
        with pytest.raises(redis.ResponseError) as ctx:
            raw_command(sample, "TS.READ", *args)
        assert str(ctx.value) == message, args


@pytest.mark.slow
def test_ts_read_blocks_until_enough_samples(sample: ClientType):
    def add():
        sleep(0.2)
        raw_command(sample, "TS.ADD", "a", 4000, 1)
        sleep(0.2)
        raw_command(sample, "TS.ADD", "a", 5000, 2)

    thread = threading.Thread(target=add)
    thread.start()
    try:
        # `$` is resolved when the command arrives, so it keeps pointing past the samples there were then.
        res = raw_command(sample, "TS.READ", "a", "$", "BLOCK", 5000, 2)
    finally:
        thread.join()
    assert _samples(res) == [[4000, 1.0], [5000, 2.0]]


@pytest.mark.slow
def test_ts_read_key_removed_while_blocked(sample: ClientType):
    def delete():
        sleep(0.2)
        sample.delete("a")

    thread = threading.Thread(target=delete)
    thread.start()
    try:
        assert raw_command(sample, "TS.READ", "a", "$", "BLOCK", 5000, 1) == []
    finally:
        thread.join()


def test_ts_read_block_in_transaction(sample: ClientType):
    p = sample.pipeline()
    p.execute_command("TS.READ", "a", 0, "BLOCK", 0, 1)
    p.execute_command("TS.READ", "a", 0, "BLOCK", 0, 50)
    res = p.execute(raise_on_error=False)
    # Only a read that would have to wait is refused.
    assert _samples(res[0]) == [[1000, 10.0], [2000, 12.0], [2500, 13.0]]
    assert isinstance(res[1], redis.ResponseError)
    assert str(res[1]) == (
        "TSDB: blocking TS.READ (with BLOCK) is not allowed inside MULTI, EVAL, or a deny-blocking context"
    )
