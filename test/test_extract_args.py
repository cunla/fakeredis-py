from fakeredis._commands import extract_args


def test_extract_args():
    xx, nx, ex, keepttl = extract_args(
        (b'nx', b'ex', b'324', b'xx',),
        ('nx', 'xx', '+ex', 'keepttl'))
    assert xx
    assert nx
    assert ex == 324
    assert not keepttl
