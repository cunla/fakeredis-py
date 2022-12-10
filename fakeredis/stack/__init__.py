try:
    from jsonpath_ng.ext import parse  # noqa: F401
    from redis.commands.json.path import Path  # noqa: F401
    from ._json_mixin import JSONCommandsMixin, JSONObject  # noqa: F401
except ImportError:
    class JSONCommandsMixin:
        pass
