from ._tdigest_mixin import TDigestCommandsMixin
from ._timeseries_mixin import TimeSeriesCommandsMixin
from ._topk_mixin import TopkCommandsMixin  # noqa: F401
from ._vectorset_mixin import VectorSetCommandsMixin  # noqa: F401

try:
    from jsonpath_ng.ext import parse  # noqa: F401
    from redis.commands.json.path import Path  # noqa: F401
    from ._json_mixin import JSONCommandsMixin  # noqa: F401
except ImportError as e:
    if e.name == "fakeredis.stack._json_mixin":
        raise e

    class JSONCommandsMixin:  # type: ignore # noqa: E303
        pass


try:
    import probables  # noqa: F401

    from ._bf_mixin import BFCommandsMixin
    from ._cf_mixin import CFCommandsMixin
    from ._cms_mixin import CMSCommandsMixin
except ImportError as e:
    if e.name == "fakeredis.stack._bf_mixin" or e.name == "fakeredis.stack._cf_mixin":
        raise e

    class BFCommandsMixin:  # type: ignore # noqa: E303
        pass

    class CFCommandsMixin:  # type: ignore # noqa: E303
        pass

    class CMSCommandsMixin:  # type: ignore # noqa: E303
        pass


__all__ = [
    "TopkCommandsMixin",
    "JSONCommandsMixin",
    "BFCommandsMixin",
    "CFCommandsMixin",
    "CMSCommandsMixin",
    "TDigestCommandsMixin",
    "TimeSeriesCommandsMixin",
    "VectorSetCommandsMixin",
]
