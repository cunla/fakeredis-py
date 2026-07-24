import time
from typing import Any, Dict


# Subclassing a parameterized generic is evaluated at runtime, so use typing.Dict
# (not the PEP 585 builtin) to keep this importable on Python 3.8.
class ClientInfo(Dict[str, Any]):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        kwargs.setdefault("-created", int(time.time()))
        kwargs.setdefault("resp", 2)
        kwargs.setdefault("user", "default")
        for k, v in kwargs.items():
            self[k.replace("_", "-")] = v
        for k in [
            "id",
            "db",
            "idle",
            "sub",
            "psub",
            "multi",
            "qbuf",
            "qbuf-free",
            "obl",
            "argv-mem",
            "oll",
            "omem",
            "tot-mem",
        ]:
            self.setdefault(k, 0)

    def items(self) -> Any:
        res = {k: v for k, v in super().items() if not k.startswith("-")}
        res["age"] = int(time.time()) - int(self.get("-created", 0))
        return res.items()

    @property
    def user(self) -> bytes:
        return str(self.get("user", "")).encode()

    @property
    def protocol_version(self) -> int:
        return int(self.get("resp", 2))

    def as_bytes(self) -> bytes:
        return " ".join([f"{k}={v}" for k, v in self.items()]).encode()
