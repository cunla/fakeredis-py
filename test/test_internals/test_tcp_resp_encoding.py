import pytest
from redis.exceptions import ResponseError

from fakeredis._helpers import SimpleError
from fakeredis._tcp_server import encode_reply

pytestmark = [pytest.mark.fake]


@pytest.mark.parametrize(
    ("value", "resp2", "resp3"),
    [
        (None, b"$-1\r\n", b"_\r\n"),
        (True, b":1\r\n", b"#t\r\n"),
        (False, b":0\r\n", b"#f\r\n"),
        (7, b":7\r\n", b":7\r\n"),
        (2**64, b"$20\r\n18446744073709551616\r\n", b"(18446744073709551616\r\n"),
        (1.5, b"$3\r\n1.5\r\n", b",1.5\r\n"),
        (b"OK", b"+OK\r\n", b"+OK\r\n"),
        (b"a\r\nb", b"$4\r\na\r\nb\r\n", b"$4\r\na\r\nb\r\n"),
        ([1, b"x", None], b"*3\r\n:1\r\n$1\r\nx\r\n$-1\r\n", b"*3\r\n:1\r\n$1\r\nx\r\n_\r\n"),
        ({b"k": 1.5}, b"*2\r\n$1\r\nk\r\n$3\r\n1.5\r\n", b"%1\r\n$1\r\nk\r\n,1.5\r\n"),
        ({b"a"}, b"*1\r\n$1\r\na\r\n", b"~1\r\n$1\r\na\r\n"),
        (SimpleError("WRONGTYPE nope"), b"-WRONGTYPE nope\r\n", b"-WRONGTYPE nope\r\n"),
        (ResponseError("boom"), b"-ERR boom\r\n", b"-ERR boom\r\n"),
    ],
)
def test_encode_reply(value, resp2: bytes, resp3: bytes):
    assert encode_reply(value, 2) == resp2
    assert encode_reply(value, 3) == resp3


def test_encode_reply_rejects_unknown_types():
    with pytest.raises(TypeError):
        encode_reply(object(), 3)
