from __future__ import annotations

import pytest

from fakeredis._helpers import SimpleError
from fakeredis.model import StreamEntryKey, StreamRangeTest, XStream


def _add(stream: XStream, fields: list[bytes], entry_key: bytes = b"*") -> bytes | None:
    requested, seq_given = (None, True) if entry_key == b"*" else StreamEntryKey.parse_xadd_id(entry_key, True)
    key = stream.next_id(requested, seq_given)
    if key is not None:
        stream.add(fields, key)
    return key.encode() if key is not None else None


@pytest.mark.fake
def test_xstream():
    stream = XStream()
    _add(stream, [b"0", b"0", b"1", b"1", b"2", b"2", b"3", b"3"], b"0-1")
    _add(stream, [b"1", b"1", b"2", b"2", b"3", b"3", b"4", b"4"], b"1-2")
    _add(stream, [b"2", b"2", b"3", b"3", b"4", b"4"], b"1-3")
    _add(stream, [b"3", b"3", b"4", b"4"], b"2-1")
    _add(stream, [b"3", b"3", b"4", b"4"], b"2-2")
    _add(stream, [b"3", b"3", b"4", b"4"], b"3-1")
    assert _add(stream, [b"3", b"3", b"4", b"4"], b"4-*") == b"4-0"
    assert _add(stream, [b"3", b"3", b"4", b"4"], b"4-*") == b"4-1"
    assert _add(stream, [b"3", b"3", b"4", b"4"], b"4-1") is None
    assert stream.last_item_key() == b"4-1"
    with pytest.raises(SimpleError):
        _add(stream, [b"3", b"3", b"4", b"4"], b"4-*-*")
    assert len(stream) == 8
    i = iter(stream)
    assert next(i) == [b"0-1", [b"0", b"0", b"1", b"1", b"2", b"2", b"3", b"3"]]
    assert next(i) == [b"1-2", [b"1", b"1", b"2", b"2", b"3", b"3", b"4", b"4"]]
    assert next(i) == [b"1-3", [b"2", b"2", b"3", b"3", b"4", b"4"]]
    assert next(i) == [b"2-1", [b"3", b"3", b"4", b"4"]]
    assert next(i) == [b"2-2", [b"3", b"3", b"4", b"4"]]

    assert stream.find_index_key_as_str("1-2") == (1, True)
    assert stream.find_index_key_as_str("0-1") == (0, True)
    assert stream.find_index_key_as_str("2-1") == (3, True)
    assert stream.find_index_key_as_str("1-4") == (3, False)

    lst = stream.irange(StreamRangeTest.decode(b"0-2"), StreamRangeTest.decode(b"3-0"))
    assert len(lst) == 4

    stream = XStream()
    assert stream.delete(["1"]) == 0
    entry_key = _add(stream, [b"0", b"0", b"1", b"1", b"2", b"2", b"3", b"3"])
    assert len(stream) == 1
    assert stream.delete([entry_key]) == 1
    assert len(stream) == 0
    # The ID of a deleted entry is not handed out again.
    assert _add(stream, [b"f", b"v"], entry_key) is None


@pytest.mark.fake
@pytest.mark.parametrize(
    "value,size",
    [
        (b"0", 2),
        (b"127", 2),
        (b"128", 3),
        (b"-1", 3),
        (b"-4096", 3),
        (b"4096", 4),
        (b"-9223372036854775808", 10),
        (b"9223372036854775808", 21),  # past int64, so a 19-byte string
        (b"007", 5),  # leading zeros keep it a string
        (b"-0", 4),
        (b"", 2),
        (b"x" * 63, 65),
        (b"x" * 64, 67),
        (b"x" * 126, 130),  # a two-byte back-length from 128 encoded bytes on
        (b"x" * 4096, 4103),
    ],
)
def test_listpack_element_size(value: bytes, size: int):
    from fakeredis.model._stream import _lp_str_size

    assert _lp_str_size(value) == size
