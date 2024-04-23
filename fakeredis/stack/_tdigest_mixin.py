from typing import List

from sortedcontainers import SortedList

from fakeredis._commands import command, CommandItem, Int, Key, Float
from fakeredis._helpers import SimpleString


class TDigest(SortedList):
    pass


class TDigestCommandsMixin:
    @command(name="TDIGEST.ADD", fixed=(Key(TDigest), Float), repeat=(Float,))
    def tdigest_add(self, key: CommandItem, *values: float) -> SimpleString:
        raise NotImplementedError

    @command(name="TDIGEST.BYRANK", fixed=(Key(TDigest), Int), repeat=(Int,))
    def tdigest_byrank(self, key: CommandItem, *ranks: int) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.BYREVRANK", fixed=(Key(TDigest), Int), repeat=(Int,))
    def tdigest_byrevrank(self, key: CommandItem, *ranks: int) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.CDF", fixed=(Key(TDigest), Float), repeat=(Float,))
    def tdigest_cdf(self, key: CommandItem, *values: float) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.CREATE", fixed=(Key(TDigest),), repeat=(bytes,))
    def tdigest_create(self, key: CommandItem, *args: bytes) -> SimpleString:
        raise NotImplementedError

    @command(name="TDIGEST.INFO", fixed=(Key(TDigest),), repeat=())
    def tdigest_info(self, key: CommandItem) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.MAX", fixed=(Key(TDigest),), repeat=())
    def tdigest_max(self, key: CommandItem) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.MERGE", fixed=(Key(TDigest), Int, Key(TDigest)), repeat=(Key(TDigest),))
    def tdigest_merge(self, key: CommandItem, numkeys: int, values: CommandItem) -> SimpleString:
        raise NotImplementedError

    @command(name="TDIGEST.MIN", fixed=(Key(TDigest),), repeat=())
    def tdigest_min(self, key: CommandItem) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.QUANTILE", fixed=(Key(TDigest), Float), repeat=(Float,))
    def tdigest_quantile(self, key: CommandItem, *values: float) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.RANK", fixed=(Key(TDigest), Float), repeat=(Float,))
    def tdigest_rank(self, key: CommandItem, *values: float) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.RESET", fixed=(Key(TDigest),), repeat=())
    def tdigest_reset(self, key: CommandItem) -> SimpleString:
        raise NotImplementedError

    @command(name="TDIGEST.REVRANK", fixed=(Key(TDigest), Float), repeat=(Float,))
    def tdigest_revrank(self, key: CommandItem, *values: float) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.TRIMMED_MEAN", fixed=(Key(TDigest), Float, Float), repeat=())
    def tdigest_trimmed_mean(self, key: CommandItem, lower: float, upper: float) -> List[bytes]:
        raise NotImplementedError
