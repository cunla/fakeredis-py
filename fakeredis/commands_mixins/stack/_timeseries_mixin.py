from __future__ import annotations

import itertools
import math
import sys
import time
from typing import Any, ClassVar, cast

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import Float, Int, extract_args
from fakeredis._commands import Key, command
from fakeredis._core import CommandItem
from fakeredis._helpers import OK, SimpleError, SimpleString, casematch
from fakeredis.commands_mixins._mixin_base import CommandsMixinBase
from fakeredis.model import AGGREGATORS, TimeSeries, TimeSeriesRule


class Timestamp(Int):
    """Argument converter for timestamps"""

    @classmethod
    def decode(cls, value: bytes, decode_error: str | None = None) -> int:
        if value == b"*":
            return int(time.time() * 1000)
        if value == b"-":
            return -1
        if value == b"+":
            return sys.maxsize
        return super().decode(value, decode_error=msgs.INVALID_EXPIRE_MSG)


class TimeSeriesCommandsMixin(CommandsMixinBase):  # TimeSeries commands
    _timeseries_keys: ClassVar[set[bytes]] = set()
    DUPLICATE_POLICIES: ClassVar[list[bytes]] = [b"BLOCK", b"FIRST", b"LAST", b"MIN", b"MAX", b"SUM"]

    @staticmethod
    def _filter_expression_check(ts: TimeSeries, filter_expression: bytes) -> bool:
        if not filter_expression:
            return True
        if filter_expression.find(b"!=") != -1:
            if len(filter_expression.split(b"!=")) != 2:
                raise SimpleError(msgs.TIMESERIES_BAD_FILTER_EXPRESSION)
            label, value = filter_expression.split(b"!=")
            if value in (b"", b"-"):
                return label in ts.labels

            if value.startswith(b"(") and value.endswith(b")"):
                values = set(value[1:-1].split(b","))
                return label in ts.labels and ts.labels[label] not in values
            return label not in ts.labels or ts.labels[label] != value
        if filter_expression.find(b"=") != -1:
            if len(filter_expression.split(b"=")) != 2:
                raise SimpleError(msgs.TIMESERIES_BAD_FILTER_EXPRESSION)
            label, value = filter_expression.split(b"=")
            if value in (b"", b"-"):
                return label not in ts.labels
            if value.startswith(b"(") and value.endswith(b")"):
                values = set(value[1:-1].split(b","))
                return label in ts.labels and ts.labels[label] in values
            return label in ts.labels and ts.labels[label] == value
        raise SimpleError(msgs.TIMESERIES_BAD_FILTER_EXPRESSION)

    def _get_timeseries(self, filter_expressions: list[bytes]) -> list[TimeSeries]:
        res: list[TimeSeries] = []
        TimeSeriesCommandsMixin._timeseries_keys = {
            k for k in TimeSeriesCommandsMixin._timeseries_keys if k in self._db
        }
        for ts_key in sorted(TimeSeriesCommandsMixin._timeseries_keys):
            ts = self._db[ts_key].value
            if all(self._filter_expression_check(ts, expr) for expr in filter_expressions):
                res.append(ts)
        return res

    @staticmethod
    def _validate_duplicate_policy(duplicate_policy: bytes) -> bool:
        return duplicate_policy is None or any(
            casematch(duplicate_policy, item) for item in TimeSeriesCommandsMixin.DUPLICATE_POLICIES
        )

    def _create_timeseries(self, name: bytes, *args: bytes) -> TimeSeries:
        (retention, encoding, chunk_size, duplicate_policy, (ignore_max_time_diff, ignore_max_val_diff)), left_args = (
            extract_args(
                args,
                ("+retention", "*encoding", "+chunk_size", "*duplicate_policy", "++ignore"),
                error_on_unexpected=False,
            )
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

        if duplicate_policy is None and self.version >= (8,):
            # In Redis 8.0, the default duplicate policy is BLOCK
            duplicate_policy = b"block"
        res = TimeSeries(
            name=name,
            database=self._db,
            retention=retention,
            encoding=encoding,
            chunk_size=chunk_size,
            duplicate_policy=duplicate_policy,
            ignore_max_time_diff=ignore_max_time_diff,
            ignore_max_val_diff=ignore_max_val_diff,
            labels=labels,
        )
        self._timeseries_keys.add(name)
        return res

    @command(name="TS.INFO", fixed=(Key(TimeSeries),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_info(self, key: CommandItem, *args: bytes) -> dict[bytes, Any]:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        if self._resp_version == 2:
            labels = [[k, v] for k, v in key.value.labels.items()]
            rules: Any = [
                [rule.dest_key.name, rule.bucket_duration, rule.aggregator.upper(), rule.align_timestamp]
                for rule in key.value.rules
            ]
        else:
            labels = key.value.labels
            rules = {
                rule.dest_key.name: [rule.bucket_duration, rule.aggregator.upper(), rule.align_timestamp]
                for rule in key.value.rules
            }
        return {
            b"totalSamples": len(key.value.sorted_list),
            b"memoryUsage": len(key.value.sorted_list) * 8 + len(key.value.encoding),
            b"firstTimestamp": key.value.sorted_list[0][0] if len(key.value.sorted_list) > 0 else 0,
            b"lastTimestamp": key.value.sorted_list[-1][0] if len(key.value.sorted_list) > 0 else 0,
            b"retentionTime": key.value.retention,
            b"chunkCount": len(key.value.sorted_list) * 8 // key.value.chunk_size,
            b"chunkSize": key.value.chunk_size,
            b"chunkType": key.value.encoding,
            b"duplicatePolicy": key.value.duplicate_policy,
            b"labels": labels,
            b"sourceKey": key.value.source_key,
            b"rules": rules,
            b"keySelfName": key.value.name,
            b"Chunks": [],
        }

    @command(name="TS.CREATE", fixed=(Key(TimeSeries),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_create(self, key: CommandItem, *args: bytes) -> SimpleString:
        if key.value is not None:
            raise SimpleError(msgs.TIMESERIES_KEY_EXISTS)
        key.value = self._create_timeseries(key.key, *args)
        return OK

    @command(name="TS.ADD", fixed=(Key(TimeSeries), Timestamp, Float), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_add(self, key: CommandItem, timestamp: int, value: float, *args: bytes) -> int:
        (on_duplicate,), _left_args = extract_args(args, ("*on_duplicate",), error_on_unexpected=False)
        if key.value is None:
            key.update(self._create_timeseries(key.key, *args))
        if not self._validate_duplicate_policy(on_duplicate):
            raise SimpleError(msgs.TIMESERIES_INVALID_DUPLICATE_POLICY)
        res = cast(int, key.value.add(timestamp, value, on_duplicate))
        key.updated()
        return res

    @command(name="TS.GET", fixed=(Key(TimeSeries),), repeat=(bytes,))
    def ts_get(self, key: CommandItem, *args: bytes) -> list[int | float] | None:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        res = key.value.get()
        if res is None and self._resp_version == 3:
            res = []
        return res  # type: ignore[no-any-return]

    @command(
        name="TS.MADD",
        fixed=(Key(TimeSeries), Timestamp, Float),
        repeat=(Key(TimeSeries), Timestamp, Float),
        flags=msgs.FLAG_DO_NOT_CREATE,
    )
    def ts_madd(self, *args: Any) -> list[Any]:
        if len(args) % 3 != 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6)
        results: list[Any] = []
        for i in range(0, len(args), 3):
            key, timestamp, value = args[i : i + 3]
            if key.value is None:
                results.append(SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST))
            else:
                results.append(key.value.add(timestamp, value))
                key.updated()
        return results

    @command(name="TS.DEL", fixed=(Key(TimeSeries), Int, Int), repeat=(), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_del(self, key: CommandItem, from_ts: int, to_ts: int) -> int:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        return cast(int, key.value.delete(from_ts, to_ts))

    @command(
        name="TS.CREATERULE",
        fixed=(Key(TimeSeries), Key(TimeSeries), bytes, bytes, Int),
        repeat=(bytes,),
        flags=msgs.FLAG_DO_NOT_CREATE,
    )
    def ts_createrule(
        self,
        source_key: CommandItem,
        dest_key: CommandItem,
        _: bytes,
        aggregator: bytes,
        bucket_duration: int,
        *args: bytes,
    ) -> SimpleString:
        if source_key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        if dest_key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        if len(args) > 1:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("ts.createrule"))
        try:
            align_timestamp = int(args[0]) if len(args) == 1 else 0
        except ValueError:
            raise SimpleError(msgs.TIMESERIES_BAD_TIMESTAMP)
        existing_rule = source_key.value.get_rule(dest_key.key)
        if existing_rule is not None:
            raise SimpleError(msgs.TIMESERIES_RULE_EXISTS)
        if aggregator not in AGGREGATORS:
            raise SimpleError(msgs.TIMESERIES_BAD_AGGREGATION_TYPE)
        rule = TimeSeriesRule(source_key.value, dest_key.value, aggregator, bucket_duration, align_timestamp)
        source_key.value.add_rule(rule)
        return OK

    @command(
        name="TS.DELETERULE",
        fixed=(Key(TimeSeries), Key(TimeSeries)),
        repeat=(),
        flags=msgs.FLAG_DO_NOT_CREATE,
    )
    def ts_deleterule(self, source_key: CommandItem, dest_key: CommandItem) -> SimpleString:
        if source_key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        res: TimeSeriesRule | None = source_key.value.get_rule(dest_key.key)
        if res is None:
            raise SimpleError(msgs.TIMESERIES_RULE_DOES_NOT_EXIST)
        source_key.value.delete_rule(res)
        return OK

    def _ts_inc_or_dec(self, key: CommandItem, addend: float, *args: bytes) -> int:
        (ts,), left_args = extract_args(
            args,
            ("+timestamp",),
            error_on_unexpected=False,
        )
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
        try:
            return cast(int, key.value.incrby(ts, addend))
        except ValueError:
            msg = (
                msgs.TIMESERIES_TIMESTAMP_LOWER_THAN_MAX_V7
                if self.version >= (7,)
                else msgs.TIMESERIES_TIMESTAMP_LOWER_THAN_MAX_V6
            )
            raise SimpleError(msg)

    @command(name="TS.INCRBY", fixed=(Key(TimeSeries), Float), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_incrby(self, key: CommandItem, addend: float, *args: bytes) -> int:
        return self._ts_inc_or_dec(key, addend, *args)

    @command(name="TS.DECRBY", fixed=(Key(TimeSeries), Float), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_decrby(self, key: CommandItem, subtrahend: float, *args: bytes) -> int:
        return self._ts_inc_or_dec(key, -subtrahend, *args)

    @command(name="TS.ALTER", fixed=(Key(TimeSeries),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_alter(self, key: CommandItem, *args: bytes) -> SimpleString:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)

        ((retention, chunk_size, duplicate_policy, (ignore_max_time_diff, ignore_max_val_diff)), left_args) = (
            extract_args(
                args, ("+retention", "+chunk_size", "*duplicate_policy", "++ignore"), error_on_unexpected=False
            )
        )

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

    def _range(self, reverse: bool, ts: TimeSeries, from_ts: int, to_ts: int, *args: bytes) -> list[list[int | float]]:
        RANGE_ARGS = ("latest", "++filter_by_value", "+count", "*align", "*+aggregation", "*buckettimestamp", "empty")
        (
            (
                latest,
                (value_min, value_max),
                count,
                align,
                (aggregator, bucket_duration),
                bucket_timestamp,
                empty,
            ),
            left_args,
        ) = extract_args(args, RANGE_ARGS, error_on_unexpected=False, left_from_first_unexpected=False)
        latest = True
        # The module skips arguments it does not recognise; FILTER_BY_TS takes the timestamps that follow it.
        filter_ts: list[int] | None = None
        for i, arg in enumerate(left_args):
            if casematch(arg, b"FILTER_BY_TS"):
                filter_ts = [int(x) for x in itertools.takewhile(lambda x: x.isdigit(), left_args[i + 1 :])]
                if not filter_ts:
                    raise SimpleError(msgs.TIMESERIES_FILTER_BY_TS_MISSING)
                break
        if aggregator is None and (align is not None or bucket_timestamp is not None or empty):
            raise SimpleError(msgs.WRONG_ARGS_MSG6)
        if bucket_timestamp is not None and bucket_timestamp not in (b"-", b"+", b"~"):
            raise SimpleError(msgs.WRONG_ARGS_MSG6)
        if align is not None:
            if align == b"+":
                align = to_ts
            elif align == b"-":
                align = from_ts
            else:
                align = int(align)
        if aggregator is None:
            res = ts.range(from_ts, to_ts, value_min, value_max, count, filter_ts, reverse)
            return [[x[0], x[1]] for x in res]

        # Since redis 8.8, multiple comma-separated aggregators can be given in a single command.
        aggregators: list[bytes] = aggregator.lower().split(b",")
        if any(agg not in AGGREGATORS for agg in aggregators):
            raise SimpleError(msgs.TIMESERIES_BAD_AGGREGATION_TYPE)
        if len(aggregators) > 1 and (self.version < (8, 8) or self.server_type != "redis"):
            raise SimpleError(msgs.TIMESERIES_BAD_AGGREGATION_TYPE)
        aggregated = [
            ts.aggregate(
                from_ts,
                to_ts,
                latest,
                value_min,
                value_max,
                count,
                filter_ts,
                align,
                agg,
                bucket_duration,
                bucket_timestamp,
                empty,
                reverse,
            )
            for agg in aggregators
        ]
        # Each bucket row is (timestamp, value-per-aggregator...); all aggregators share the same buckets.
        result: list[list[int | float]] = [
            [row[0]] + [aggregated[j][i][1] for j in range(len(aggregators))] for i, row in enumerate(aggregated[0])
        ]
        return result

    @command(
        name="TS.RANGE", fixed=(Key(TimeSeries), Timestamp, Timestamp), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE
    )
    def ts_range(self, key: CommandItem, from_ts: int, to_ts: int, *args: bytes) -> list[list[int | float]]:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        return self._samples_reply(self._range(False, key.value, from_ts, to_ts, *args))

    @command(
        name="TS.REVRANGE",
        fixed=(Key(TimeSeries), Timestamp, Timestamp),
        repeat=(bytes,),
        flags=msgs.FLAG_DO_NOT_CREATE,
    )
    def ts_revrange(self, key: CommandItem, from_ts: int, to_ts: int, *args: bytes) -> list[list[int | float]]:
        if key.value is None:
            raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
        return self._samples_reply(self._range(True, key.value, from_ts, to_ts, *args))

    @command(name="TS.MGET", fixed=(bytes,), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_mget(self, *args: bytes) -> list[list[bytes | list[list[int | float]]]]:
        latest, with_labels, selected_labels, filter_expression = False, False, None, None
        i = 0
        while i < len(args):
            if casematch(args[i], b"LATEST"):
                latest = True  # noqa: F841
                i += 1
            elif casematch(args[i], b"WITHLABELS"):
                with_labels = True
                i += 1
            elif casematch(args[i], b"SELECTED_LABELS"):
                selected_labels = []
                i += 1
                while i < len(args) and casematch(args[i], b"FILTER"):
                    selected_labels.append(args[i])
            elif casematch(args[i], b"FILTER"):
                filter_expression = []
                i += 1
                while i < len(args):
                    filter_expression.append(args[i])
                    i += 1

        if with_labels and selected_labels is not None:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("ts.mget"))
        if filter_expression is None or len(filter_expression) == 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("ts.mget"))

        timeseries = self._get_timeseries(filter_expression)
        res: Any
        if self._resp_version == 2:
            if with_labels:
                return [[ts.name, [[k, v] for (k, v) in ts.labels.items()], ts.get()] for ts in timeseries]
            if selected_labels is not None:
                res = [
                    [ts.name, [[label, ts.labels[label]] for label in selected_labels if label in ts.labels], ts.get()]
                    for ts in timeseries
                ]
            else:
                res = [[ts.name, [], ts.get()] for ts in timeseries]
        else:
            if with_labels:
                res = {ts.name: [ts.labels, ts.get() or []] for ts in timeseries}
            elif selected_labels is not None:
                res = {
                    ts.name: [
                        {label: ts.labels[label] for label in selected_labels if label in ts.labels},
                        ts.get() or [],
                    ]
                    for ts in timeseries
                }
            else:
                res = {ts.name: [{}, ts.get() or []] for ts in timeseries}
        return res  # type: ignore[no-any-return]

    @command(name="TS.QUERYINDEX", fixed=(bytes,), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_queryindex(self, *args: bytes) -> list[bytes]:
        filter_expressions = list(args)
        timeseries = self._get_timeseries(filter_expressions)
        return [ts.name for ts in timeseries]

    def _group_by_label(
        self, reverse: bool, ts_dict: dict[bytes, list[Any]], label: bytes, reducer: bytes
    ) -> dict[bytes, list[Any]]:
        # ts_dict: name -> [labels, ..., measurements]
        reducer = reducer.lower()
        if reducer not in AGGREGATORS:
            raise SimpleError(msgs.TIMESERIES_BAD_AGGREGATION_TYPE)
        ts_map: dict[bytes, dict[int, list[float]]] = {}  # label_value -> timestamp -> values
        for ts_data in ts_dict.values():
            # Find label value
            labels_dict = ts_data[0]
            label_value = labels_dict.get(label, None)
            if not label_value:
                raise SimpleError(msgs.TIMESERIES_BAD_FILTER_EXPRESSION)
            if label_value not in ts_map:
                ts_map[label_value] = {}
            # Collect measurements
            for timestamp, value in ts_data[-1]:
                if timestamp not in ts_map[label_value]:
                    ts_map[label_value][timestamp] = []
                ts_map[label_value][timestamp].append(value)
        res = {}
        for label_value, timestamp_values in ts_map.items():
            sorted_timestamps = sorted(timestamp_values.keys())
            name = f"{label.decode()}={label_value.decode()}"
            sources = [ts_name.decode() for ts_name in ts_map]
            labels = {label: label_value, b"__reducer__": reducer, b"__source__": sources}
            measurements: list[list[int | float]] = [
                [timestamp, float(AGGREGATORS[reducer](timestamp_values[timestamp]))] for timestamp in sorted_timestamps
            ]
            if reverse:
                measurements.reverse()
            res[name.encode("utf-8")] = [labels, {b"reducers": [reducer]}, {b"sources": sources}, measurements]
        return res

    def _mrange(self, reverse: bool, from_ts: int, to_ts: int, *args: bytes) -> Any:
        args_lower = [arg.lower() for arg in args]
        arg_words = {
            b"latest",
            b"withlabels",
            b"selected_labels",
            b"filter",
            b"groupby",
            b"reduce",
            b"count",
            b"aggregation",
            b"filter_by_value",
            b"filter_by_ts",
            b"align",
        }
        left_args = []
        latest, with_labels, selected_labels, filter_expression, group_by, reducer = (
            False,
            False,
            None,
            None,
            None,
            None,
        )
        exclude_empty = False
        i = 0
        while i < len(args_lower):
            if args_lower[i] == b"latest":
                latest = True  # noqa: F841
                i += 1
            elif args_lower[i] == b"excludeempty":
                # Only recognised before FILTER: after it, the word is taken as a (malformed) filter expression.
                exclude_empty = True
                i += 1
            elif args_lower[i] == b"withlabels":
                with_labels = True
                i += 1
            elif args_lower[i] == b"selected_labels":
                selected_labels = []
                i += 1
                while i < len(args_lower) and args_lower[i] not in arg_words:
                    selected_labels.append(args_lower[i])
                    i += 1
            elif args_lower[i] == b"filter":
                filter_expression = []
                i += 1
                while i < len(args_lower) and args_lower[i] not in arg_words:
                    filter_expression.append(args[i])
                    i += 1
            elif i + 3 < len(args_lower) and args_lower[i] == b"groupby" and args_lower[i + 2] == b"reduce":
                group_by = args[i + 1]
                reducer = args_lower[i + 3]
                i += 4
            else:
                left_args.append(args[i])
                i += 1

        if with_labels and selected_labels is not None:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("ts.mrange"))
        if filter_expression is None or len(filter_expression) == 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("ts.mrange"))
        if exclude_empty and group_by is not None:
            raise SimpleError(msgs.TIMESERIES_EXCLUDEEMPTY_WITH_GROUPBY)

        aggregators: list[bytes] = []
        for i, arg in enumerate(left_args[:-1]):
            if casematch(arg, b"aggregation"):
                aggregators = left_args[i + 1].lower().split(b",")
        timeseries = self._get_timeseries(filter_expression)
        res: Any
        if with_labels or (group_by is not None and reducer is not None):
            res = {
                ts.name: [
                    ts.labels,
                    {b"aggregators": aggregators},
                    self._range(reverse, ts, from_ts, to_ts, *left_args),
                ]
                for ts in timeseries
            }
        elif selected_labels is not None:
            res = {
                ts.name: [
                    {label: ts.labels[label] for label in selected_labels if label in ts.labels},
                    {b"aggregators": aggregators},
                    self._range(reverse, ts, from_ts, to_ts, *left_args),
                ]
                for ts in timeseries
            }
        else:
            res = {
                ts.name: [
                    {},
                    {b"aggregators": aggregators},
                    self._range(reverse, ts, from_ts, to_ts, *left_args),
                ]
                for ts in timeseries
            }
        if exclude_empty:
            res = {ts_name: ts_data for ts_name, ts_data in res.items() if ts_data[-1]}
        if group_by is not None and reducer is not None:
            res = self._group_by_label(reverse, res, group_by, reducer)
        if self._resp_version == 2:
            res = [[ts_name, [[k, v] for k, v in ts_data[0].items()], ts_data[-1]] for ts_name, ts_data in res.items()]
        return res

    @command(name="TS.MRANGE", fixed=(Timestamp, Timestamp), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_mrange(self, from_ts: int, to_ts: int, *args: bytes) -> list[list[bytes | list[list[int | float]]]]:
        return self._mrange(False, from_ts, to_ts, *args)  # type: ignore[no-any-return]

    @command(name="TS.MREVRANGE", fixed=(Timestamp, Timestamp), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_mrevrange(self, from_ts: int, to_ts: int, *args: bytes) -> list[list[bytes | list[list[int | float]]]]:
        return self._mrange(True, from_ts, to_ts, *args)  # type: ignore[no-any-return]

    def _samples_reply(self, rows: list[list[Any]]) -> list[list[Any]]:
        """Shape (timestamp, value...) rows, whose values may also be nested lists, for the protocol in use.

        RESP2 sends the values as strings, and the module spells NaN as `NaN`.
        """
        if self._resp_version != 2:
            return rows

        def value(v: Any) -> Any:
            if isinstance(v, list):
                return [value(x) for x in v]
            return b"NaN" if isinstance(v, float) and math.isnan(v) else v

        return [[row[0]] + [value(v) for v in row[1:]] for row in rows]

    @command(name="TS.QUERYLABELS", fixed=(bytes,), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_querylabels(self, subtype: bytes, *args: bytes) -> list[bytes]:
        """TS.QUERYLABELS <LABELS | VALUES label> [FILTER filterExpr [filterExpr ...]]"""
        label: bytes | None = None
        if casematch(subtype, b"values"):
            if not args:
                raise SimpleError(msgs.WRONG_ARGS_MSG6.format("ts.querylabels"))
            label, args = args[0], args[1:]
        elif not casematch(subtype, b"labels"):
            raise SimpleError(msgs.TIMESERIES_QUERYLABELS_BAD_SUBTYPE)
        filters: list[bytes] = []
        if args:
            if not casematch(args[0], b"filter"):
                raise SimpleError(msgs.TIMESERIES_QUERYLABELS_EXPECTED_FILTER)
            filters = list(args[1:])
            if not filters:
                raise SimpleError(msgs.TIMESERIES_FILTER_WITHOUT_EXPRESSIONS)
            if any(b"=" not in expr for expr in filters):
                raise SimpleError(msgs.TIMESERIES_BAD_FILTER_EXPRESSION)
            # At least one filter must select series by value (`label=value` or `label=(...)`).
            if not any(b"!=" not in expr and expr.split(b"=", 1)[1] not in (b"", b"-") for expr in filters):
                raise SimpleError(msgs.TIMESERIES_NO_MATCHER)
        found: set[bytes] = set()
        for ts in self._get_timeseries(filters):
            if label is None:
                found.update(ts.labels)
            elif label in ts.labels:
                found.add(ts.labels[label])
        return sorted(found)

    def _nrange(self, reverse: bool, command_name: str, args: tuple[bytes, ...]) -> list[list[Any]]:
        """TS.N[REV]RANGE numkeys key [key ...] fromTimestamp toTimestamp [options...]

        Runs TS.[REV]RANGE over each key and joins the results by timestamp: a row per timestamp holds each key's
        values in key order, NaN where the key has none. With AGGREGATION, each key gets its own aggregator argument.
        """
        numkeys = Int.decode(args[0], msgs.TIMESERIES_NUMKEYS_NOT_POSITIVE)
        if numkeys < 0:
            raise SimpleError(msgs.TIMESERIES_NUMKEYS_NOT_POSITIVE)
        if numkeys == 0 or len(args) < numkeys + 3:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format(command_name))
        keys = args[1 : 1 + numkeys]
        try:
            from_ts = Timestamp.decode(args[1 + numkeys])
        except SimpleError:
            raise SimpleError(msgs.TIMESERIES_WRONG_FROM_TIMESTAMP)
        try:
            to_ts = Timestamp.decode(args[2 + numkeys])
        except SimpleError:
            raise SimpleError(msgs.TIMESERIES_WRONG_TO_TIMESTAMP)

        options = args[3 + numkeys :]
        count: int | None = None
        aggregators: tuple[bytes, ...] | None = None
        bucket_duration = b""
        range_args: list[bytes] = []  # the options that TS.RANGE shares, passed on for each key
        i = 0
        while i < len(options):
            if casematch(options[i], b"count"):
                count = Int.decode(options[i + 1], msgs.TIMESERIES_INVALID_COUNT) if i + 1 < len(options) else 0
                if count <= 0:
                    raise SimpleError(msgs.TIMESERIES_INVALID_COUNT)
                i += 2
            elif casematch(options[i], b"aggregation"):
                # The aggregator arguments run up to the bucket duration, the first integer.
                end = i + 1
                while end < len(options) and not options[end].lstrip(b"-").isdigit():
                    end += 1
                if end == len(options):
                    raise SimpleError(msgs.TIMESERIES_BAD_AGGREGATION)
                aggregators, bucket_duration = options[i + 1 : end], options[end]
                if len(aggregators) != numkeys:
                    raise SimpleError(msgs.TIMESERIES_AGGREGATION_COUNT_NOT_NUMKEYS)
                if Int.decode(bucket_duration) <= 0:
                    raise SimpleError(msgs.TIMESERIES_BUCKET_DURATION_NOT_POSITIVE)
                i = end + 1
            else:
                range_args.append(options[i])
                i += 1

        series: list[TimeSeries] = []
        for key in keys:
            item = self._db.get(key)
            if item is None:
                raise SimpleError(msgs.TIMESERIES_KEY_DOES_NOT_EXIST)
            if not isinstance(item.value, TimeSeries):
                raise SimpleError(msgs.WRONGTYPE_MSG)
            series.append(item.value)

        per_key: list[dict[int, list[Any]]] = []
        widths: list[int] = []
        for k, ts in enumerate(series):
            key_args = list(range_args)
            if aggregators is not None:
                key_args += [b"AGGREGATION", aggregators[k], bucket_duration]
                widths.append(len(aggregators[k].split(b",")))
            else:
                widths.append(1)
            per_key.append({int(row[0]): row[1:] for row in self._range(reverse, ts, from_ts, to_ts, *key_args)})

        timestamps = sorted({t for rows in per_key for t in rows}, reverse=reverse)
        if count is not None:
            timestamps = timestamps[:count]
        nan = float("nan")
        return self._samples_reply(
            [[t, [v for rows, width in zip(per_key, widths) for v in rows.get(t, [nan] * width)]] for t in timestamps]
        )

    @command(name="TS.NRANGE", fixed=(bytes, bytes, bytes, bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_nrange(self, *args: bytes) -> list[list[Any]]:
        return self._nrange(False, "ts.nrange", args)

    @command(name="TS.NREVRANGE", fixed=(bytes, bytes, bytes, bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_nrevrange(self, *args: bytes) -> list[list[Any]]:
        return self._nrange(True, "ts.nrevrange", args)

    @staticmethod
    def _read_samples(ts: TimeSeries | None, cursor: int, max_count: int | None) -> list[list[Any]]:
        """The samples at or after `cursor`, oldest first, at most `max_count` of them."""
        if ts is None:
            return []
        return [[t, v] for t, v in sorted(x for x in ts.sorted_list if x[0] >= cursor)][:max_count]

    @command(name="TS.READ", fixed=(bytes, bytes), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def ts_read(self, key: bytes, timestamp: bytes, *args: bytes) -> Any:
        """TS.READ key timestamp [BLOCK milliseconds min_count] [MAX_COUNT max_count]"""
        block_ms: int | None = None
        min_count = 1
        max_count: int | None = None
        seen: set[bytes] = set()
        i = 0
        while i < len(args):
            option = args[i].upper()
            if option == b"BLOCK" and option not in seen and i + 2 < len(args):
                block_ms = Int.decode(args[i + 1], msgs.TIMESERIES_READ_BAD_BLOCK_MS)
                # The module reports a malformed min_count with the milliseconds message too.
                min_count = Int.decode(args[i + 2], msgs.TIMESERIES_READ_BAD_BLOCK_MS)
                if block_ms < 0:
                    raise SimpleError(msgs.TIMESERIES_READ_BAD_BLOCK_MS)
                if min_count < 1:
                    raise SimpleError(msgs.TIMESERIES_READ_BAD_MIN_COUNT)
                i += 3
            elif option == b"MAX_COUNT" and option not in seen and i + 1 < len(args):
                max_count = Int.decode(args[i + 1], msgs.TIMESERIES_READ_BAD_MAX_COUNT)
                if max_count < 1:
                    raise SimpleError(msgs.TIMESERIES_READ_BAD_MAX_COUNT)
                i += 2
            else:
                raise SimpleError(msgs.WRONG_ARGS_MSG6.format("ts.read"))
            seen.add(option)
        if block_ms is not None and max_count is not None and min_count > max_count:
            raise SimpleError(msgs.TIMESERIES_READ_MIN_ABOVE_MAX)
        if timestamp not in (b"-", b"+", b"$"):
            if not timestamp.isdigit():
                raise SimpleError(msgs.TIMESERIES_INVALID_TIMESTAMP)
            Int.decode(timestamp, msgs.TIMESERIES_INVALID_TIMESTAMP)

        def lookup() -> TimeSeries | None:
            """The series under `key` now, or None if it is missing (or has since been replaced by another type)."""
            item = self._db.get(key) if self._db is not None else None
            return item.value if item is not None and isinstance(item.value, TimeSeries) else None

        item = self._db.get(key)
        if item is not None and not isinstance(item.value, TimeSeries):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        # The cursor is resolved once, when the command arrives, so it stays put while the client is blocked.
        timestamps = [t for t, _ in item.value.sorted_list] if item is not None else []
        if timestamp == b"-":
            cursor = min(timestamps, default=0)
        elif timestamp == b"+":
            cursor = max(timestamps, default=0)
        elif timestamp == b"$":
            cursor = max(timestamps) + 1 if timestamps else 0
        else:
            cursor = int(timestamp)

        def shape(samples: list[list[Any]] | None) -> list[list[Any]]:
            # A timeout returns whatever qualifies by then.
            return self._samples_reply(
                samples if samples is not None else self._read_samples(lookup(), cursor, max_count)
            )

        if block_ms is None:
            return shape(None)

        existed = item is not None

        def read_pass(first_pass: bool) -> list[list[Any]] | None:
            ts = lookup()
            if ts is None:
                return [] if existed else None  # A series removed while blocked answers with an empty list.
            samples = self._read_samples(ts, cursor, None)
            return samples[:max_count] if len(samples) >= min_count else None

        if read_pass(True) is None and (self._in_transaction or self._script_resp is not None):
            raise SimpleError(msgs.TIMESERIES_READ_BLOCK_NOT_ALLOWED)
        return self._blocking(block_ms / 1000, read_pass, shape)
