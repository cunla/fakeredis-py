from ._tdigest_mixin import TDigestCommandsMixin
from ._timeseries_mixin import TimeSeriesCommandsMixin
from ._topk_mixin import TopkCommandsMixin

try:
    import numpy  # noqa: F401

    from ._vectorset_mixin import VectorSetCommandsMixin
except ImportError:

    class VectorSetCommandsMixin:  # type: ignore
        pass


try:
    from jsonpath_ng.ext import parse  # noqa: F401
    from redis.commands.json.path import Path  # noqa: F401

    from ._json_mixin import JSONCommandsMixin
except ImportError as e:
    if e.name == "fakeredis.stack._json_mixin":
        raise

    class JSONCommandsMixin:  # type: ignore
        pass


try:
    import probables  # noqa: F401

    from ._bf_mixin import BFCommandsMixin
    from ._cf_mixin import CFCommandsMixin
    from ._cms_mixin import CMSCommandsMixin
except ImportError as e:
    if e.name == "fakeredis.stack._bf_mixin" or e.name == "fakeredis.stack._cf_mixin":
        raise

    class BFCommandsMixin:  # type: ignore
        pass

    class CFCommandsMixin:  # type: ignore
        pass

    class CMSCommandsMixin:  # type: ignore
        pass


__all__ = [
    "BFCommandsMixin",
    "CFCommandsMixin",
    "CMSCommandsMixin",
    "JSONCommandsMixin",
    "TDigestCommandsMixin",
    "TimeSeriesCommandsMixin",
    "TopkCommandsMixin",
    "VectorSetCommandsMixin",
]
