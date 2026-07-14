"""Tests for the JSON.SET FPHA argument (redis 8.8): forcing an FP type for homogeneous FP arrays."""

import json

import pytest

from fakeredis._typing import ClientType
from test import testtools

json_tests = pytest.importorskip("jsonpath_ng")

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.supported_server_versions(min_redis_ver="8.7.2"),
        pytest.mark.unsupported_server_types("dragonfly", "valkey"),
    ]
)


def _get(r: ClientType, key: str):
    # The legacy `.` path returns the raw document on both real redis and fakeredis,
    # while `$` wrapping differs; parsing the JSON also ignores formatting differences.
    return json.loads(testtools.raw_command(r, "JSON.GET", key, "."))


def test_fpha_converts_integers_to_floats(r: ClientType):
    assert testtools.raw_command(r, "JSON.SET", "doc", "$", "[[1,2,3,4e3],[5,6.0,7,8]]", "FPHA", "FP16") == b"OK"
    assert _get(r, "doc") == [[1.0, 2.0, 3.0, 4000.0], [5.0, 6.0, 7.0, 8.0]]


def test_fpha_all_integer_array(r: ClientType):
    assert testtools.raw_command(r, "JSON.SET", "doc", "$", "[1,2,3]", "FPHA", "FP16") == b"OK"
    res = _get(r, "doc")
    assert res == [1.0, 2.0, 3.0]
    assert all(type(item) is float for item in res)


@pytest.mark.parametrize(
    "fpha_type,expected",
    [
        ("FP16", [0.1235]),
        ("BF16", [0.1235]),
        ("FP32", [0.12345679]),
        ("FP64", [0.123456789]),
    ],
)
def test_fpha_quantization(r: ClientType, fpha_type: str, expected: list):
    assert testtools.raw_command(r, "JSON.SET", "doc", "$", "[0.123456789]", "FPHA", fpha_type) == b"OK"
    assert _get(r, "doc") == expected


def test_fpha_representable_values_unchanged(r: ClientType):
    assert testtools.raw_command(r, "JSON.SET", "doc", "$", "[0.1,0.2,0.3]", "FPHA", "FP16") == b"OK"
    assert _get(r, "doc") == [0.1, 0.2, 0.3]


def test_fpha_mixed_array_untouched(r: ClientType):
    # An array with non-numeric elements is not a homogeneous FP array
    assert testtools.raw_command(r, "JSON.SET", "doc", "$", '[1.5,"a",2.5]', "FPHA", "FP16") == b"OK"
    assert _get(r, "doc") == [1.5, "a", 2.5]


def test_fpha_array_nested_in_object(r: ClientType):
    assert testtools.raw_command(r, "JSON.SET", "doc", "$", '{"v":[1,2]}', "FPHA", "FP16") == b"OK"
    assert _get(r, "doc") == {"v": [1.0, 2.0]}


def test_fpha_lowercase_type(r: ClientType):
    assert testtools.raw_command(r, "JSON.SET", "doc", "$", "[1,2]", "FPHA", "fp16") == b"OK"
    assert _get(r, "doc") == [1.0, 2.0]


def test_fpha_with_condition(r: ClientType):
    assert testtools.raw_command(r, "JSON.SET", "doc", "$", "[1.5]", "FPHA", "FP32", "NX") == b"OK"
    assert testtools.raw_command(r, "JSON.SET", "doc", "$", "[2.5]", "NX", "FPHA", "FP32") is None


@pytest.mark.parametrize(
    "value,fpha_type,expected_error",
    [
        ("[1.5,70000.0]", "FP16", "value out of range for F16 at line 1 column 13"),
        ("[-70000.0]", "FP16", "value out of range for F16 at line 1 column 10"),
        ("[1.5,1e39]", "BF16", "value out of range for BF16 at line 1 column 10"),
        ("[1.5,1e39]", "FP32", "value out of range for F32 at line 1 column 10"),
    ],
)
def test_fpha_out_of_range(r: ClientType, value: str, fpha_type: str, expected_error: str):
    with pytest.raises(Exception, match=expected_error):
        testtools.raw_command(r, "JSON.SET", "doc", "$", value, "FPHA", fpha_type)
    assert testtools.raw_command(r, "JSON.GET", "doc", "$") is None


def test_fpha_invalid_type(r: ClientType):
    with pytest.raises(Exception, match="invalid FPHA type"):
        testtools.raw_command(r, "JSON.SET", "doc", "$", "[1.5]", "FPHA", "FP8")


def test_fpha_missing_type(r: ClientType):
    with pytest.raises(Exception, match="wrong number of arguments"):
        testtools.raw_command(r, "JSON.SET", "doc", "$", "[1.5]", "FPHA")
