from typing import List

from sortedcontainers import SortedList

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import command, CommandItem, Int, Key, Float
from fakeredis._helpers import SimpleString, SimpleError, OK, Database


class TDigest(SortedList):
    def __init__(self, compression: int = 100):
        super().__init__()
        self.compression = compression


class TDigestCommandsMixin:
    def __init__(self, *args, **kwargs):
        self._db: Database

    @command(name="TDIGEST.CREATE", fixed=(Key(TDigest),), repeat=(bytes,),
             flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_create(self, key: CommandItem, *args: bytes) -> SimpleString:
        if key.value is not None:
            raise SimpleError(msgs.TDIGEST_KEY_EXISTS)
        (compression,), left_args = extract_args(args, ("+compression",), )
        if compression is None:
            compression = 100
        key.update(TDigest(compression))
        return OK

    @command(
        name="TDIGEST.RESET", fixed=(Key(TDigest),), repeat=(),
        flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_reset(self, key: CommandItem) -> SimpleString:
        if key.value is None:
            raise SimpleError(msgs.TDIGEST_KEY_NOT_EXISTS)
        key.value.clear()
        return OK

    @command(
        name="TDIGEST.ADD", fixed=(Key(TDigest), Float), repeat=(Float,),
        flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_add(self, key: CommandItem, *values: float) -> SimpleString:
        if key.value is None:
            raise SimpleError(msgs.TDIGEST_KEY_NOT_EXISTS)
        # parsing
        try:
            values_to_add = [float(val) for val in values]
        except ValueError:
            raise SimpleError(msgs.TDIGEST_ERROR_PARSING_VALUE)
        # adding
        key.value.update(values_to_add)
        return OK

    @command(
        name="TDIGEST.BYRANK", fixed=(Key(TDigest), Int), repeat=(Int,),
        flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_byrank(self, key: CommandItem, *ranks: int) -> List[bytes]:
        raise NotImplementedError

    @command(
        name="TDIGEST.BYREVRANK", fixed=(Key(TDigest), Int), repeat=(Int,),
        flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_byrevrank(self, key: CommandItem, *ranks: int) -> List[bytes]:
        raise NotImplementedError

    @command(
        name="TDIGEST.MERGE", fixed=(Key(TDigest), Int, bytes), repeat=(bytes,),
        flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_merge(self, dest: CommandItem, numkeys: int, *args: bytes) -> SimpleString:
        if len(args) < numkeys:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("tdigest.merge"))
        sources_names = args[:numkeys]
        (compression, override), _ = extract_args(args[numkeys:], ("+compression", "override"))
        sources = [self._db.get(name).value for name in sources_names if name in self._db]
        if len(sources) != len(sources_names):
            raise SimpleError(msgs.TDIGEST_KEY_NOT_EXISTS)

        if override:
            if dest.value is None:
                compression = compression or max([source.compression for source in sources])
                dest.value = TDigest(compression)
            else:
                dest.value.clear()
        if dest.value is None:
            raise SimpleError(msgs.TDIGEST_KEY_NOT_EXISTS)
        for source in sources:
            dest.value.update(source)
        dest.updated()
        return OK

    @command(
        name="TDIGEST.MAX", fixed=(Key(TDigest),), repeat=(),
        flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_max(self, key: CommandItem) -> bytes:
        if key.value is None:
            raise SimpleError(msgs.TDIGEST_KEY_NOT_EXISTS)
        if len(key.value) == 0:
            return b"nan"
        return str(key.value[-1]).encode()

    @command(name="TDIGEST.MIN", fixed=(Key(TDigest),), repeat=(),
             flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_min(self, key: CommandItem) -> bytes:
        if key.value is None:
            raise SimpleError(msgs.TDIGEST_KEY_NOT_EXISTS)
        if len(key.value) == 0:
            return b"nan"
        return str(key.value[0]).encode()

    @command(
        name="TDIGEST.CDF", fixed=(Key(TDigest), Float), repeat=(Float,),
        flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_cdf(self, key: CommandItem, *values: float) -> List[bytes]:
        raise NotImplementedError

    @command(
        name="TDIGEST.INFO", fixed=(Key(TDigest),), repeat=(),
        flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_info(self, key: CommandItem) -> List[bytes]:
        return [
            b"Compression", key.value.compression,
            b"Capacity", len(key.value),
            b"Merged nodes", len(key.value),
            b"Unmerged nodes", 0,
            b"Merged weight", len(key.value),
            b"Unmerged weight", 0,
            b"Observations", len(key.value),
            b"Total compressions", len(key.value),
            b"Memory usage", len(key.value),
        ]

    @command(name="TDIGEST.QUANTILE", fixed=(Key(TDigest), Float), repeat=(Float,),
             flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_quantile(self, key: CommandItem, *values: float) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.RANK", fixed=(Key(TDigest), Float), repeat=(Float,),
             flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_rank(self, key: CommandItem, *values: float) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.REVRANK", fixed=(Key(TDigest), Float), repeat=(Float,),
             flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_revrank(self, key: CommandItem, *values: float) -> List[bytes]:
        raise NotImplementedError

    @command(name="TDIGEST.TRIMMED_MEAN", fixed=(Key(TDigest), Float, Float), repeat=(),
             flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL)
    def tdigest_trimmed_mean(self, key: CommandItem, lower: float, upper: float) -> List[bytes]:
        raise NotImplementedError
