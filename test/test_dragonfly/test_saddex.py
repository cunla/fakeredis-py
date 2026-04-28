from __future__ import annotations

from time import sleep

import pytest

from fakeredis._typing import ClientType
from test import testtools

pytestmark = []
pytestmark.extend(
    [
        pytest.mark.unsupported_server_types("redis", "valkey"),
    ]
)


@pytest.mark.slow
def test_saddex(r: ClientType):
    set_name = "foo"
    assert testtools.raw_command(r, "saddex", set_name, 1, "m1", "m2") == 2
    sleep(1.01)
    assert set(r.smembers("foo")) == set()


@pytest.mark.slow
def test_saddex_expire_members(r: ClientType):
    set_name = "foo"
    assert testtools.raw_command(r, "saddex", set_name, 1, "m1", "m2") == 2
    assert r.sadd(set_name, "m3", "m4") == 2
    assert testtools.raw_command(r, "saddex", set_name, 1, "m3") == 0
    sleep(1.1)
    assert set(r.smembers("foo")) == {b"m3", b"m4"}
