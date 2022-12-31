import pytest

from fakeredis._command_args_parsing import extract_args
from fakeredis._helpers import SimpleError


def test_extract_args():
    args = (b'nx', b'ex', b'324', b'xx',)
    (xx, nx, ex, keepttl), _ = extract_args(args, ('nx', 'xx', '+ex', 'keepttl'))
    assert xx
    assert nx
    assert ex == 324
    assert not keepttl


def test_extract_args__should_raise_error():
    args = (b'nx', b'ex', b'324', b'xx', b'something')
    with pytest.raises(SimpleError):
        (xx, nx, ex, keepttl), _ = extract_args(args, ('nx', 'xx', '+ex', 'keepttl'))


def test_extract_args__should_return_something():
    args = (b'nx', b'ex', b'324', b'xx', b'something')

    (xx, nx, ex, keepttl), left = extract_args(
        args, ('nx', 'xx', '+ex', 'keepttl'), error_on_unexpected=False)
    assert xx
    assert nx
    assert ex == 324
    assert not keepttl
    assert left == [b'something', ]

    args = (b'nx', b'something', b'ex', b'324', b'xx',)

    (xx, nx, ex, keepttl), left = extract_args(
        args, ('nx', 'xx', '+ex', 'keepttl'), error_on_unexpected=False)
    assert xx
    assert nx
    assert ex == 324
    assert not keepttl
    assert left == [b'something', ]


def test_extract_args__multiple_numbers():
    args = (b'nx', b'limit', b'324', b'123', b'xx',)

    (xx, nx, limit, keepttl), _ = extract_args(
        args, ('nx', 'xx', '++limit', 'keepttl'))
    assert xx
    assert nx
    assert limit == [324, 123]
    assert not keepttl


def test_extract_args__extract_non_numbers():
    args = (b'by', b'dd', b'nx', b'limit', b'324', b'123', b'xx',)

    (xx, nx, limit, sortby), _ = extract_args(
        args, ('nx', 'xx', '++limit', '*by'))
    assert xx
    assert nx
    assert limit == [324, 123]
    assert sortby == b'dd'
