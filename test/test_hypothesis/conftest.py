from __future__ import annotations

import os
from typing import TYPE_CHECKING, Tuple

import pytest
import redis
from hypothesis import settings

from .base import MachineConfig

if TYPE_CHECKING:
    from test.conftest import ServerDetails

# The differential machines run many command sequences and are slow, so keep
# the example count tunable for fast local iteration (set
# FAKEREDIS_HYPOTHESIS_EXAMPLES) while defaulting to a thorough-but-affordable
# count for CI.
settings.register_profile(
    "fakeredis",
    max_examples=int(os.environ.get("FAKEREDIS_HYPOTHESIS_EXAMPLES", "250")),
)
settings.load_profile("fakeredis")


@pytest.fixture
def hypothesis_config(real_server_details: ServerDetails, real_server_address: Tuple[str, int]) -> MachineConfig:
    """Server details for a differential Hypothesis machine.

    Reuses the session-scoped ``real_server_details``/``real_server_address``
    fixtures (test/conftest.py) so there is no import-time server detection.
    """
    host, port = real_server_address
    client = redis.StrictRedis(host, port=port, db=2)
    try:
        if client.info("server").get("arch_bits") != 64:
            pytest.skip("real server is not 64-bit")
    finally:
        client.connection_pool.disconnect()
    return MachineConfig(
        server_type=real_server_details.server_type,
        version=real_server_details.server_version,
        host=host,
        port=port,
    )
