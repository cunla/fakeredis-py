import time
from typing import List, Dict, Tuple, Union, Optional, Any

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import command, Key, CommandItem, Int, Float, Timestamp
from fakeredis._helpers import Database, SimpleString, OK, SimpleError, casematch


class TimeSeries:
    def __init__(
            self,
            retention: int = 0, encoding: str = "compressed", chunk_size: int = 0,
            duplicate_policy: str = None,
            ignore_max_time_diff: int = 0, ignore_max_val_diff: int = 0,
            labels: Dict[str, str] = None,
    ):
        super().__init__()
        self.retention = retention
        self.encoding = encoding
        self.chunk_size = chunk_size
        self.duplicate_policy = duplicate_policy
        self.map: Dict[int, float] = dict()
        self.sorted_list: List[Tuple[int, float]] = list()
        self.labels = labels or {}

    def add(self, timestamp: int, value: float) -> Union[int, None, List[None]]:
        if self.retention != 0 and time.time() - timestamp > self.retention:
            if len(self.sorted_list) > 0:
                return self.sorted_list[-1][0]
            return []
        self.map[timestamp] = value
        self.sorted_list.append((timestamp, value))
        return timestamp

    def get(self) -> Optional[List[Union[int, float]]]:
        if len(self.sorted_list) == 0:
            return None
        return [self.sorted_list[-1][0], self.sorted_list[-1][1]]

    def delete(self, from_ts: int, to_ts: int) -> int:
        prev_size = len(self.sorted_list)
        self.sorted_list = [x for x in self.sorted_list if not (from_ts <= x[0] <= to_ts)]
        self.map = {k: v for k, v in self.map.items() if not (from_ts <= k <= to_ts)}
        return prev_size - len(self.sorted_list)


_timeseries: List[TimeSeries] = list()


class TimeSeriesCommandsMixin:
    # TimeSeries commands
    def __init__(self, *args, **kwargs):
        self._db: Database

    def _create_timeseries(self, *args) -> TimeSeries:
        (retention, encoding, chunk_size, duplicate_policy,
         (ignore_max_time_diff, ignore_max_val_diff)), left_args = extract_args(
            args, ("+retention", "*encoding", "+chunk_size", "*duplicate_policy", "++ignore"),
            error_on_unexpected=False,
        )
        retention = retention or 0
        encoding = encoding or b"COMPRESSED"
        if not (casematch(encoding, b"COMPRESSED") or casematch(encoding, b"UNCOMPRESSED")):
            raise SimpleError(msgs.BAD_SUBCOMMAND_MSG.format("TS.CREATE"))
        encoding = encoding.decode().lower()
        chunk_size = chunk_size or 4096
        if chunk_size % 8 != 0:
            raise SimpleError(msgs.BAD_SUBCOMMAND_MSG.format("TS.CREATE"))
        duplicate_policy = duplicate_policy or b"BLOCK"
        if (not casematch(duplicate_policy, b"BLOCK")
                and not casematch(duplicate_policy, b"FIRST")
                and not casematch(duplicate_policy, b"LAST")
                and not casematch(duplicate_policy, b"MIN")
                and not casematch(duplicate_policy, b"MAX")
                and not casematch(duplicate_policy, b"SUM")):
            raise SimpleError(msgs.BAD_SUBCOMMAND_MSG.format("TS.CREATE"))
        duplicate_policy = duplicate_policy.decode().lower()
        if len(left_args) > 0 and (not casematch(left_args[0], b"LABELS") or len(left_args) % 2 != 1):
            raise SimpleError(msgs.BAD_SUBCOMMAND_MSG.format("TS.ADD"))
        labels = dict(zip(left_args[1::2], left_args[2::2])) if len(left_args) > 0 else {}

        return TimeSeries(
            retention=retention, encoding=encoding, chunk_size=chunk_size, duplicate_policy=duplicate_policy,
            ignore_max_time_diff=ignore_max_time_diff, ignore_max_val_diff=ignore_max_val_diff,
            labels=labels)

    @command(name="TS.CREATE", fixed=(Key(TimeSeries),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_create(self, key: CommandItem, *args: bytes) -> SimpleString:
        if key.value is not None:
            raise SimpleError(msgs.TIMESERIES_KEY_EXISTS)
        key.value = self._create_timeseries(*args)
        _timeseries.append(key.value)
        return OK

    @command(name="TS.ADD", fixed=(Key(TimeSeries), Timestamp, Float), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_add(self, key: CommandItem, timestamp: int, value: float, *args: bytes) -> int:
        if key.value is None:
            key.update(self._create_timeseries(*args))
            _timeseries.append(key.value)
        return key.value.add(timestamp, value)

    @command(name="TS.GET", fixed=(Key(TimeSeries),), repeat=(bytes,))
    def ts_get(self, key: CommandItem, *args: bytes) -> Optional[List[Union[int, float]]]:
        if key.value is None:
            raise SimpleError(msgs.NO_KEY_MSG)
        return key.value.get()

    @command(
        name="TS.MADD",
        fixed=(Key(TimeSeries), Timestamp, Float),
        repeat=(Key(TimeSeries), Timestamp, Float),
        flags=msgs.FLAG_DO_NOT_CREATE,
    )
    def ts_madd(self, *args: Any) -> List[int]:
        if len(args) % 3 != 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6)
        results: List[int] = list()
        for i in range(0, len(args), 3):
            key, timestamp, value = args[i:i + 3]
            if key.value is None:
                raise SimpleError(msgs.NO_KEY_MSG)
            results.append(key.value.add(timestamp, value))
        return results

    @command(name="TS.DEL", fixed=(Key(TimeSeries), Int, Int), repeat=())
    def ts_del(self, key: CommandItem, from_ts: int, to_ts: int) -> bytes:
        if key.value is None:
            raise SimpleError(msgs.NO_KEY_MSG)
        if from_ts > to_ts:
            raise SimpleError(msgs.WRONG_ARGS_MSG7)
        return key.value.delete(from_ts, to_ts)

    @command(name="TS.MGET", fixed=(bytes,), repeat=(bytes,))
    def ts_mget(self, *args: bytes) -> bytes:
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

    @command(name="TS.DELETERULE", fixed=(Key(TimeSeries), Key(TimeSeries)), repeat=())
    def ts_deleterule(self, source_key: CommandItem, dest_key: CommandItem) -> bytes:
        pass

    @command(name="TS.INFO", fixed=(Key(TimeSeries),), repeat=(bytes,))
    def ts_info(self, key: CommandItem, *args: bytes) -> bytes:
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
