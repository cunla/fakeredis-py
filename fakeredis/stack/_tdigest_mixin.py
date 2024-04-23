from typing import List

from fakeredis._commands import command, CommandItem, Int, Key, Float
from fakeredis._helpers import SimpleString


class TDigest:
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

    # TDIGEST.CREATE
    # TDIGEST.INFO
    # TDIGEST.MAX
    # TDIGEST.MERGE
    # TDIGEST.MIN
    # TDIGEST.QUANTILE
    # TDIGEST.RANK
    # TDIGEST.RESET
    # TDIGEST.REVRANK
    # TDIGEST.TRIMMED_MEAN
