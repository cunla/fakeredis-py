from typing import List

from fakeredis import _msgs as msgs
from fakeredis._commands import command, Key, CommandItem, Int, Float
from fakeredis._helpers import Database, SimpleString, OK, SimpleError


class TimeSeries:
    pass


class TimeSeriesCommandsMixin:
    # TimeSeries commands
    def __init__(self, *args, **kwargs):
        self._db: Database

    @command(name="TS.CREATE", fixed=(Key(TimeSeries),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_create(self, key: CommandItem, *args: bytes) -> SimpleString:
        if key.value is not None:
            raise SimpleError(msgs.TIMESERIES_KEY_EXISTS)
        key.update(TimeSeries())
        return OK

    @command(
        name="TS.ADD",
        fixed=(Key(TimeSeries), bytes, bytes),
        repeat=(bytes,),
        flags=msgs.FLAG_DO_NOT_CREATE + msgs.FLAG_LEAVE_EMPTY_VAL,
    )
    def ts_add(self, key: CommandItem, timestamp: bytes, value: bytes, *args: bytes) -> bytes:
        pass

    @command(name="TS.ALTER", fixed=(Key(TimeSeries),), repeat=(bytes,))
    def ts_alter(self, key: CommandItem, *args: bytes) -> bytes:
        pass

    @command(name="TS.CREATERULE", fixed=(Key(TimeSeries), Key(TimeSeries), bytes, bytes, Int), repeat=(bytes,))
    def ts_createrule(
            self,
            source_key: CommandItem,
            dest_key: CommandItem,
            _: bytes,
            aggregator: bytes,
            bucket_duration: int,
            *args: bytes,
    ) -> SimpleString:
        pass

    @command(name="TS.DECRBY", fixed=(Key(TimeSeries), Float), repeat=(bytes,))
    def ts_decrby(self, key: CommandItem, subtrahend: float, *args: bytes) -> bytes:
        pass

    @command(name="TS.INCRBY", fixed=(Key(TimeSeries), Float), repeat=(bytes,))
    def ts_incrby(self, key: CommandItem, addend: float, *args: bytes) -> bytes:
        pass

    @command(name="TS.DEL", fixed=(Key(TimeSeries), Int, Int), repeat=())
    def ts_del(self, key: CommandItem, from_ts: int, to_ts: int) -> bytes:
        pass

    @command(name="TS.DELETERULE", fixed=(Key(TimeSeries), Key(TimeSeries)), repeat=())
    def ts_deleterule(self, source_key: CommandItem, dest_key: CommandItem) -> bytes:
        pass

    @command(name="TS.GET", fixed=(Key(TimeSeries),), repeat=(bytes,))
    def ts_get(self, key: CommandItem, *args: bytes) -> bytes:
        pass

    @command(name="TS.INFO", fixed=(Key(TimeSeries),), repeat=(bytes,))
    def ts_info(self, key: CommandItem, *args: bytes) -> bytes:
        pass

    @command(
        name="TS.MADD",
        fixed=(Key(TimeSeries), Int, bytes),
        repeat=(
                Key(TimeSeries),
                Int,
                bytes,
        ),
    )
    def ts_madd(self, *args: bytes) -> List[int]:
        pass

    @command(name="TS.MGET", fixed=(bytes,), repeat=(bytes,))
    def ts_mget(self, *args: bytes) -> bytes:
        pass

    @command(name="TS.MRANGE", fixed=(Int, Int), repeat=(bytes,))
    def ts_mrange(self, from_ts: int, to_ts: int, *args: bytes) -> bytes:
        pass

    @command(name="TS.MREVRANGE", fixed=(Int, Int), repeat=(bytes,))
    def ts_mrevrange(self, from_ts: int, to_ts: int, *args: bytes) -> bytes:
        pass

    @command(name="TS.QUERYINDEX", fixed=(bytes,), repeat=(bytes,))
    def ts_queryindex(self, filterExpr: bytes, *args: bytes) -> bytes:
        pass

    @command(name="TS.RANGE", fixed=(Key(TimeSeries), Int, Int), repeat=(bytes,))
    def ts_range(self, key: CommandItem, from_ts: int, to_ts: int, *args: bytes) -> bytes:
        pass

    @command(name="TS.REVRANGE", fixed=(Key(TimeSeries), Int, Int), repeat=(bytes,))
    def ts_revrange(self, key: CommandItem, from_ts: int, to_ts: int, *args: bytes) -> bytes:
        pass
