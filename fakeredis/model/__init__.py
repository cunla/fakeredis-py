from ._acl import AccessControlList
from ._array import Array
from ._base_type import BaseModel
from ._client_info import ClientInfo
from ._command_info import (
    get_all_commands_info,
    get_categories,
    get_command_info,
    get_commands_by_category,
)
from ._expiring_members_set import ExpiringMembersSet
from ._hash import Hash
from ._stream import StreamEntryKey, StreamGroup, StreamRangeTest, XStream
from ._tdigest import TDigest
from ._timeseries_model import AGGREGATORS, TimeSeries, TimeSeriesRule
from ._topk import HeavyKeeper
from ._zset import ZSet

__all__ = [
    "AGGREGATORS",
    "AccessControlList",
    "Array",
    "BaseModel",
    "ClientInfo",
    "ExpiringMembersSet",
    "Hash",
    "HeavyKeeper",
    "StreamEntryKey",
    "StreamGroup",
    "StreamRangeTest",
    "TDigest",
    "TimeSeries",
    "TimeSeriesRule",
    "XStream",
    "ZSet",
    "get_all_commands_info",
    "get_categories",
    "get_command_info",
    "get_commands_by_category",
]

try:
    import numpy as np  # noqa: F401

    from ._vectorset import Vector, VectorSet  # noqa: F401

    __all__.extend(["Vector", "VectorSet"])
except ImportError:
    pass

try:
    import probables  # noqa: F401

    from ._cms import CountMinSketch  # noqa: F401
    from ._filters import ScalableBloomFilter, ScalableCuckooFilter  # noqa: F401

    __all__.extend(["CountMinSketch", "ScalableBloomFilter", "ScalableCuckooFilter"])
except ImportError:
    pass
