from fakeredis._command_args_parsing import extract_args


def test_extract_args():
    args = (b'nx', b'ex', b'324', b'xx',)
    xx, nx, ex, keepttl = extract_args(args, ('nx', 'xx', '+ex', 'keepttl'))
    assert xx
    assert nx
    assert ex == 324
    assert not keepttl
