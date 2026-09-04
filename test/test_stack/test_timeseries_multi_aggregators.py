"""Tests for multiple aggregators in a single TS.RANGE/TS.REVRANGE/TS.MRANGE/TS.MREVRANGE (redis 8.8)."""

import pytest

from fakeredis._typing import ClientType
from test.testtools import get_protocol_version, raw_command

timeseries_tests = pytest.importorskip("probables")

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.supported_server_versions(min_redis_ver="8.7.2"),
        pytest.mark.unsupported_server_types("dragonfly", "valkey"),
    ]
)


@pytest.fixture
def sample(r: ClientType) -> ClientType:
    raw_command(r, "TS.CREATE", "ts1", "LABELS", "type", "temp")
    raw_command(r, "TS.MADD", "ts1", 1000, 30, "ts1", 1010, 35, "ts1", 1020, 40, "ts1", 2000, 100, "ts1", 2010, 110)
    return r


def _values(res) -> list:
    """Normalize (timestamp, value...) rows: RESP2 returns values as bulk strings, RESP3 as doubles."""
    return [[row[0]] + [float(x) for x in row[1:]] for row in res]


def test_ts_range_multiple_aggregators(sample: ClientType):
    res = raw_command(sample, "TS.RANGE", "ts1", "-", "+", "AGGREGATION", "min,avg,max", 1000)
    assert _values(res) == [[1000, 30.0, 35.0, 40.0], [2000, 100.0, 105.0, 110.0]]


def test_ts_range_duplicate_aggregators(sample: ClientType):
    res = raw_command(sample, "TS.RANGE", "ts1", "-", "+", "AGGREGATION", "min,min", 1000)
    assert _values(res) == [[1000, 30.0, 30.0], [2000, 100.0, 100.0]]


def test_ts_revrange_multiple_aggregators(sample: ClientType):
    res = raw_command(sample, "TS.REVRANGE", "ts1", "-", "+", "AGGREGATION", "min,max", 1000)
    assert _values(res) == [[2000, 100.0, 110.0], [1000, 30.0, 40.0]]


def test_ts_range_multiple_aggregators_with_count(sample: ClientType):
    res = raw_command(sample, "TS.RANGE", "ts1", "-", "+", "COUNT", 1, "AGGREGATION", "min,max", 1000)
    assert _values(res) == [[1000, 30.0, 40.0]]


def test_ts_mrange_multiple_aggregators(sample: ClientType):
    res = raw_command(sample, "TS.MRANGE", "-", "+", "AGGREGATION", "min,max", 1000, "FILTER", "type=temp")
    expected = [[1000, 30.0, 40.0], [2000, 100.0, 110.0]]
    if get_protocol_version(sample) == 2:
        assert len(res) == 1 and res[0][0] == b"ts1"
        assert _values(res[0][-1]) == expected
    else:
        assert _values(res[b"ts1"][-1]) == expected


def test_ts_mrevrange_multiple_aggregators(sample: ClientType):
    res = raw_command(sample, "TS.MREVRANGE", "-", "+", "AGGREGATION", "min,max", 1000, "FILTER", "type=temp")
    expected = [[2000, 100.0, 110.0], [1000, 30.0, 40.0]]
    if get_protocol_version(sample) == 2:
        assert _values(res[0][-1]) == expected
    else:
        assert _values(res[b"ts1"][-1]) == expected


def test_ts_range_invalid_aggregator_in_list(sample: ClientType):
    with pytest.raises(Exception, match="Unknown aggregation type"):
        raw_command(sample, "TS.RANGE", "ts1", "-", "+", "AGGREGATION", "min,bogus", 1000)
    # Whitespace between aggregators is not allowed
    with pytest.raises(Exception, match="Unknown aggregation type"):
        raw_command(sample, "TS.RANGE", "ts1", "-", "+", "AGGREGATION", "min, max", 1000)
