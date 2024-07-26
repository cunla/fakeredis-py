import time
from typing import List, Union, Optional, Any

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import command, Key, CommandItem, Int, Float, Timestamp
from fakeredis._helpers import Database, SimpleString, OK, SimpleError, casematch
from ._timeseries_model import TimeSeries, TimeSeriesRule, AGGREGATORS


class TimeSeriesCommandsMixin:  # TimeSeries commands
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._db: Database

    DUPLICATE_POLICIES = [b"BLOCK", b"FIRST", b"LAST", b"MIN", b"MAX", b"SUM"]

    @staticmethod
    def _validate_duplicate_policy(duplicate_policy: bytes) -> bool:
        return duplicate_policy is None or any(
            [casematch(duplicate_policy, item) for item in TimeSeriesCommandsMixin.DUPLICATE_POLICIES])

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
            raise SimpleError(msgs.TIMESERIES_BAD_CHUNK_SIZE)
        if not self._validate_duplicate_policy(duplicate_policy):
            raise SimpleError(msgs.TIMESERIES_INVALID_DUPLICATE_POLICY)
        duplicate_policy = duplicate_policy.lower() if duplicate_policy else None
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
            b"rules", [
                [rule.dest_key.name, rule.bucket_duration, rule.aggregator.upper(), rule.align_timestamp] for rule in
                key.value.rules
            ],
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
        (on_duplicate,), left_args = extract_args(args, ("*on_duplicate",), error_on_unexpected=False)
        if key.value is None:
            key.update(self._create_timeseries(key.key, *args))
        if not self._validate_duplicate_policy(on_duplicate):
            raise SimpleError(msgs.TIMESERIES_INVALID_DUPLICATE_POLICY)
        res = key.value.add(timestamp, value, on_duplicate)
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

    @command(name="TS.DEL", fixed=(Key(TimeSeries), Int, Int), repeat=(), flags=msgs.FLAG_DO_NOT_CREATE, )
    def ts_del(self, key: CommandItem, from_ts: int, to_ts: int) -> bytes:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        return key.value.delete(from_ts, to_ts)

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
        if aggregator not in AGGREGATORS:
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

    def _ts_inc_or_dec(self, key: CommandItem, addend: float, *args: bytes) -> bytes:
        (ts,), left_args = extract_args(args, ("+timestamp",), error_on_unexpected=False, )
        if key.value is None:
            key.update(self._create_timeseries(key.key, *left_args))
        timeseries = key.value
        if ts is None:
            if len(timeseries.sorted_list) == 0:
                ts = int(time.time())
            else:
                ts = timeseries.sorted_list[-1][0]
        if len(timeseries.sorted_list) > 0 and ts < timeseries.sorted_list[-1][0]:
            raise SimpleError(msgs.TIMESERIES_INVALID_TIMESTAMP)
        return key.value.incrby(ts, addend)

    @command(name="TS.INCRBY", fixed=(Key(TimeSeries), Float), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE, )
    def ts_incrby(self, key: CommandItem, addend: float, *args: bytes) -> bytes:
        return self._ts_inc_or_dec(key, addend, *args)

    @command(name="TS.DECRBY", fixed=(Key(TimeSeries), Float), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE, )
    def ts_decrby(self, key: CommandItem, subtrahend: float, *args: bytes) -> bytes:
        return self._ts_inc_or_dec(key, -subtrahend, *args)

    @command(name="TS.ALTER", fixed=(Key(TimeSeries),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_alter(self, key: CommandItem, *args: bytes) -> bytes:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)

        ((retention, chunk_size, duplicate_policy, (ignore_max_time_diff, ignore_max_val_diff)),
         left_args) = extract_args(
            args, ("+retention", "+chunk_size", "*duplicate_policy", "++ignore"), error_on_unexpected=False)

        if chunk_size is not None and chunk_size % 8 != 0:
            raise SimpleError(msgs.TIMESERIES_BAD_CHUNK_SIZE)
        if not self._validate_duplicate_policy(duplicate_policy):
            raise SimpleError(msgs.TIMESERIES_INVALID_DUPLICATE_POLICY)
        duplicate_policy = duplicate_policy.lower() if duplicate_policy else None
        if len(left_args) > 0 and (not casematch(left_args[0], b"LABELS") or len(left_args) % 2 != 1):
            raise SimpleError(msgs.BAD_SUBCOMMAND_MSG.format("TS.ADD"))
        labels = dict(zip(left_args[1::2], left_args[2::2])) if len(left_args) > 0 else {}

        key.value.retention = retention or key.value.retention
        key.value.chunk_size = chunk_size or key.value.chunk_size
        key.value.duplicate_policy = duplicate_policy or key.value.duplicate_policy
        key.value.ignore_max_time_diff = ignore_max_time_diff or key.value.ignore_max_time_diff
        key.value.ignore_max_val_diff = ignore_max_val_diff or key.value.ignore_max_val_diff
        key.value.labels = labels or key.value.labels
        key.updated()
        return OK

    def _range(
            self, reverse: bool, key: CommandItem, from_ts: int, to_ts: int, *args: bytes
    ) -> List[List[Union[int, float]]]:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        RANGE_ARGS = ("latest", "++filter_by_value", "+count", "*align", "*+aggregation", "+buckettimestamp", "empty")
        (latest, (value_min, value_max), count, align, (aggregator, bucket_duration), bucket_timestamp,
         empty), left_args = extract_args(args, RANGE_ARGS, error_on_unexpected=False, left_from_first_unexpected=False)
        latest = True
        filter_ts: Optional[List[int]] = None
        if len(left_args) > 0:
            if not casematch(left_args[0], b"FILTER_BY_TS"):
                raise SimpleError(msgs.WRONG_ARGS_MSG6)
            left_args = left_args[1:]
            filter_ts = [int(x) for x in left_args]
        if aggregator is None and (align is not None or bucket_timestamp is not None or empty):
            raise SimpleError(msgs.WRONG_ARGS_MSG6)
        if align is not None:
            if align == b"+":
                align = to_ts
            elif align == b"-":
                align = from_ts
            else:
                align = int(align)
        if aggregator is not None and aggregator not in AGGREGATORS:
            raise SimpleError(msgs.TIMESERIES_BAD_AGGREGATION_TYPE)
        if aggregator is None:
            res = key.value.range(from_ts, to_ts, value_min, value_max, count, filter_ts, reverse)
        else:
            res = key.value.aggregate(from_ts, to_ts,
                                      latest, value_min, value_max, count, filter_ts,
                                      align, aggregator, bucket_duration,
                                      bucket_timestamp, empty, reverse)

        res = [[x[0], x[1]] for x in res]
        return res

    @command(name="TS.RANGE", fixed=(Key(TimeSeries), Timestamp, Timestamp), repeat=(bytes,),
             flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_range(self, key: CommandItem, from_ts: int, to_ts: int, *args: bytes) -> List[List[Union[int, float]]]:
        return self._range(False, key, from_ts, to_ts, *args)

    @command(name="TS.REVRANGE", fixed=(Key(TimeSeries), Timestamp, Timestamp), repeat=(bytes,),
             flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_revrange(self, key: CommandItem, from_ts: int, to_ts: int, *args: bytes) -> List[List[Union[int, float]]]:
        res = self._range(True, key, from_ts, to_ts, *args)
        return res

    @command(name="TS.MGET", fixed=(bytes,), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_mget(self, *args: bytes) -> bytes:
        pass

    @command(name="TS.MRANGE", fixed=(Int, Int), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_mrange(self, from_ts: int, to_ts: int, *args: bytes) -> bytes:
        pass

    @command(name="TS.MREVRANGE", fixed=(Int, Int), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_mrevrange(self, from_ts: int, to_ts: int, *args: bytes) -> bytes:
        pass

    @command(name="TS.QUERYINDEX", fixed=(bytes,), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_queryindex(self, filterExpr: bytes, *args: bytes) -> bytes:
        pass
