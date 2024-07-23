from typing import List, Dict, Tuple, Union, Optional, Any

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import command, Key, CommandItem, Int, Float, Timestamp
from fakeredis._helpers import Database, SimpleString, OK, SimpleError, casematch


class TimeSeries:
    def __init__(
            self,
            name: bytes, database: Database,
            retention: int = 0, encoding: bytes = b"compressed", chunk_size: int = 4096,
            duplicate_policy: bytes = b"block",
            ignore_max_time_diff: int = 0, ignore_max_val_diff: int = 0,
            labels: Dict[str, str] = None,
            source_key: Optional[bytes] = None,
    ):
        super().__init__()
        self.name = name
        self._db = database
        self.retention = retention
        self.encoding = encoding
        self.chunk_size = chunk_size
        self.duplicate_policy = duplicate_policy
        self.ts_ind_map: Dict[int, int] = dict()  # Map from timestamp to index in sorted_list
        self.sorted_list: List[Tuple[int, float]] = list()
        self.max_timestamp: int = 0
        self.labels = labels or {}
        self.source_key = source_key
        self.rules: List[TimeSeriesRule] = list()

    def add(self, timestamp: int, value: float) -> Union[int, None, List[None]]:
        if self.retention != 0 and self.max_timestamp - timestamp > self.retention:
            if len(self.sorted_list) > 0:
                return self.sorted_list[-1][0]
            return []
        if timestamp in self.ts_ind_map:
            self.sorted_list[self.ts_ind_map[timestamp]] = (timestamp, value)
            return timestamp
        self.sorted_list.append((timestamp, value))
        self.ts_ind_map[timestamp] = len(self.sorted_list) - 1
        self.rules = [rule for rule in self.rules if rule.dest_key.name in self._db]
        for rule in self.rules:
            rule.apply((timestamp, value))
        self.max_timestamp = max(self.max_timestamp, timestamp)
        return timestamp

    def get(self) -> Optional[List[Union[int, float]]]:
        if len(self.sorted_list) == 0:
            return None
        return [self.sorted_list[-1][0], self.sorted_list[-1][1]]

    def delete(self, from_ts: int, to_ts: int) -> int:
        prev_size = len(self.sorted_list)
        self.sorted_list = [x for x in self.sorted_list if not (from_ts <= x[0] <= to_ts)]
        self.ts_ind_map = {k: v for k, v in self.ts_ind_map.items() if not (from_ts <= k <= to_ts)}
        return prev_size - len(self.sorted_list)

    def get_rule(self, dest_key: bytes) -> Optional["TimeSeriesRule"]:
        for rule in self.rules:
            if rule.dest_key.name == dest_key:
                return rule
        return None

    def add_rule(self, rule: "TimeSeriesRule") -> None:
        self.rules.append(rule)

    def delete_rule(self, rule: "TimeSeriesRule") -> None:
        self.rules.remove(rule)


class Aggregators:
    @staticmethod
    def var_p(values: List[float]) -> float:
        if len(values) == 0:
            return 0
        avg = sum(values) / len(values)
        return sum((x - avg) ** 2 for x in values) / len(values)

    @staticmethod
    def var_s(values: List[float]) -> float:
        if len(values) == 0:
            return 0
        avg = sum(values) / len(values)
        return sum((x - avg) ** 2 for x in values) / (len(values) - 1)

    @staticmethod
    def std_p(values: List[float]) -> float:
        return Aggregators.var_p(values) ** 0.5

    @staticmethod
    def std_s(values: List[float]) -> float:
        return Aggregators.var_s(values) ** 0.5


class TimeSeriesRule:
    AGGREGATORS = {
        b"avg": lambda x: sum(x) / len(x),
        b"sum": sum,
        b"min": min,
        b"max": max,
        b"range": lambda x: max(x) - min(x),
        b"count": len,
        b"first": lambda x: x[0],
        b"last": lambda x: x[-1],
        b"std.p": Aggregators.std_p,
        b"std.s": Aggregators.std_s,
        b"var.p": Aggregators.var_p,
        b"var.s": Aggregators.var_s,
        b"twa": lambda x: 0,
    }

    def __init__(
            self, source_key: TimeSeries, dest_key: TimeSeries,
            aggregator: bytes, bucket_duration: int,
            align_timestamp: int = 0,
    ):
        self.source_key = source_key
        self.dest_key = dest_key
        self.aggregator = aggregator.lower()
        self.bucket_duration = bucket_duration
        self.align_timestamp = align_timestamp
        self.current_bucket_start_ts: int = 0
        self.current_bucket: List[Tuple[int, float]] = list()
        self.dest_key.source_key = source_key.name

    def apply(self, record: Tuple[int, float]) -> None:
        ts, val = record
        bucket_start_ts = ts - (ts % self.bucket_duration) + self.align_timestamp
        if self.current_bucket_start_ts != bucket_start_ts:
            self._apply_bucket()
            self.current_bucket_start_ts = bucket_start_ts
            self.current_bucket = list()
        self.current_bucket.append(record)

    def _apply_bucket(self) -> None:
        if len(self.current_bucket) == 0:
            return
        if self.aggregator == b"twa":
            return
        relevant_values = [x[1] for x in self.current_bucket]
        value = TimeSeriesRule.AGGREGATORS[self.aggregator](relevant_values)
        self.dest_key.add(self.current_bucket_start_ts, value)


class TimeSeriesCommandsMixin:
    # TimeSeries commands
    def __init__(self, *args, **kwargs):
        self._db: Database

    def _create_timeseries(self, name: bytes, *args) -> TimeSeries:
        (retention, encoding, chunk_size, duplicate_policy,
         (ignore_max_time_diff, ignore_max_val_diff)), left_args = extract_args(
            args, ("+retention", "*encoding", "+chunk_size", "*duplicate_policy", "++ignore"),
            error_on_unexpected=False,
        )
        retention = retention or 0
        encoding = encoding or b"COMPRESSED"
        if not (casematch(encoding, b"COMPRESSED") or casematch(encoding, b"UNCOMPRESSED")):
            raise SimpleError(msgs.BAD_SUBCOMMAND_MSG.format("TS.CREATE"))
        encoding = encoding.lower()
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
        duplicate_policy = duplicate_policy.lower()
        if len(left_args) > 0 and (not casematch(left_args[0], b"LABELS") or len(left_args) % 2 != 1):
            raise SimpleError(msgs.BAD_SUBCOMMAND_MSG.format("TS.ADD"))
        labels = dict(zip(left_args[1::2], left_args[2::2])) if len(left_args) > 0 else {}

        res = TimeSeries(
            name=name, database=self._db,
            retention=retention, encoding=encoding, chunk_size=chunk_size, duplicate_policy=duplicate_policy,
            ignore_max_time_diff=ignore_max_time_diff, ignore_max_val_diff=ignore_max_val_diff, labels=labels,
        )
        return res

    @command(name="TS.INFO", fixed=(Key(TimeSeries),), repeat=(bytes,))
    def ts_info(self, key: CommandItem, *args: bytes) -> List[Any]:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        return [
            b"totalSamples", len(key.value.sorted_list),
            b"memoryUsage", len(key.value.sorted_list) * 8 + len(key.value.encoding),
            b"firstTimestamp", key.value.sorted_list[0][0] if len(key.value.sorted_list) > 0 else 0,
            b"lastTimestamp", key.value.sorted_list[-1][0] if len(key.value.sorted_list) > 0 else 0,
            b"retentionTime", key.value.retention,
            b"chunkCount", len(key.value.sorted_list) * 8 // key.value.chunk_size,
            b"chunkSize", key.value.chunk_size,
            b"chunkType", key.value.encoding,
            b"duplicatePolicy", key.value.duplicate_policy,
            b"labels", [[k, v] for k, v in key.value.labels.items()],
            b"sourceKey", key.value.source_key,
            b"rules", [],
            b"keySelfName", key.value.name,
            b"Chunks", [],
        ]

    @command(name="TS.CREATE", fixed=(Key(TimeSeries),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_create(self, key: CommandItem, *args: bytes) -> SimpleString:
        if key.value is not None:
            raise SimpleError(msgs.TIMESERIES_KEY_EXISTS)
        key.value = self._create_timeseries(key.key, *args)
        return OK

    @command(name="TS.ADD", fixed=(Key(TimeSeries), Timestamp, Float), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_add(self, key: CommandItem, timestamp: int, value: float, *args: bytes) -> int:
        if key.value is None:
            key.update(self._create_timeseries(key.key, *args))
        res = key.value.add(timestamp, value)
        return res

    @command(name="TS.GET", fixed=(Key(TimeSeries),), repeat=(bytes,))
    def ts_get(self, key: CommandItem, *args: bytes) -> Optional[List[Union[int, float]]]:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
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
                raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
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

    @command(
        name="TS.CREATERULE",
        fixed=(Key(TimeSeries), Key(TimeSeries), bytes, bytes, Int),
        repeat=(Int,),
        flags=msgs.FLAG_DO_NOT_CREATE,
    )
    def ts_createrule(
            self,
            source_key: CommandItem,
            dest_key: CommandItem,
            _: bytes,
            aggregator: bytes,
            bucket_duration: int,
            *args: int,
    ) -> SimpleString:
        if source_key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        if dest_key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        if len(args) > 1:
            raise SimpleError(msgs.WRONG_ARGS_MSG6)
        try:
            align_timestamp = int(args[0]) if len(args) == 1 else 0
        except ValueError:
            raise SimpleError(msgs.WRONG_ARGS_MSG6)
        existing_rule = source_key.value.get_rule(dest_key.key)
        if existing_rule is not None:
            raise SimpleError(msgs.TIMESERIES_RULE_EXISTS)
        if aggregator not in TimeSeriesRule.AGGREGATORS:
            raise SimpleError(msgs.TIMESERIES_BAD_AGGREGATION_TYPE)
        rule = TimeSeriesRule(source_key.value, dest_key.value, aggregator, bucket_duration, align_timestamp)
        source_key.value.add_rule(rule)
        return OK

    @command(name="TS.DELETERULE", fixed=(Key(TimeSeries), Key(TimeSeries)), repeat=(), flags=msgs.FLAG_DO_NOT_CREATE, )
    def ts_deleterule(self, source_key: CommandItem, dest_key: CommandItem) -> bytes:
        if source_key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        res: Optional[TimeSeriesRule] = source_key.value.get_rule(dest_key.key)
        if res is None:
            raise SimpleError(msgs.NOT_FOUND_MSG)
        source_key.value.delete_rule(res)
        return OK

    @command(name="TS.DECRBY", fixed=(Key(TimeSeries), Float), repeat=(bytes,))
    def ts_decrby(self, key: CommandItem, subtrahend: float, *args: bytes) -> bytes:
        pass

    @command(name="TS.INCRBY", fixed=(Key(TimeSeries), Float), repeat=(bytes,))
    def ts_incrby(self, key: CommandItem, addend: float, *args: bytes) -> bytes:
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
