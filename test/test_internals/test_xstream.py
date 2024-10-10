import pytest

from fakeredis.model import XStream, StreamRangeTest


@pytest.mark.fake
def test_xstream():
    stream = XStream()
    stream.add([0, 0, 1, 1, 2, 2, 3, 3], "0-1")
    stream.add([1, 1, 2, 2, 3, 3, 4, 4], "1-2")
    stream.add([2, 2, 3, 3, 4, 4], "1-3")
    stream.add([3, 3, 4, 4], "2-1")
    stream.add([3, 3, 4, 4], "2-2")
    stream.add([3, 3, 4, 4], "3-1")
    assert stream.add([3, 3, 4, 4], "4-*") == b"4-0"
    assert stream.last_item_key() == b"4-0"
    assert stream.add([3, 3, 4, 4], "4-*-*") is None
    assert len(stream) == 7
    i = iter(stream)
    assert next(i) == [b"0-1", [0, 0, 1, 1, 2, 2, 3, 3]]
    assert next(i) == [b"1-2", [1, 1, 2, 2, 3, 3, 4, 4]]
    assert next(i) == [b"1-3", [2, 2, 3, 3, 4, 4]]
    assert next(i) == [b"2-1", [3, 3, 4, 4]]
    assert next(i) == [b"2-2", [3, 3, 4, 4]]

    assert stream.find_index_key_as_str("1-2") == (1, True)
    assert stream.find_index_key_as_str("0-1") == (0, True)
    assert stream.find_index_key_as_str("2-1") == (3, True)
    assert stream.find_index_key_as_str("1-4") == (3, False)

    lst = stream.irange(StreamRangeTest.decode(b"0-2"), StreamRangeTest.decode(b"3-0"))
    assert len(lst) == 4

    stream = XStream()
    assert stream.delete(["1"]) == 0
    entry_key: bytes = stream.add([0, 0, 1, 1, 2, 2, 3, 3])
    assert len(stream) == 1
    assert (
        stream.delete(
            [
                entry_key,
            ]
        )
        == 1
    )
    assert len(stream) == 0
