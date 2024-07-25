from typing import List, Dict, Tuple, Union, Optional

from fakeredis import _msgs as msgs
from fakeredis._helpers import Database, SimpleError


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
        self.ignore_max_time_diff = ignore_max_time_diff
        self.ignore_max_val_diff = ignore_max_val_diff
        self.rules: List[TimeSeriesRule] = list()

    def add(
            self, timestamp: int, value: float, duplicate_policy: Optional[bytes] = None
    ) -> Union[int, None, List[None]]:
        if self.retention != 0 and self.max_timestamp - timestamp > self.retention:
            raise SimpleError(msgs.TIMESERIES_TIMESTAMP_OLDER_THAN_RETENTION)
        if duplicate_policy is None:
            duplicate_policy = self.duplicate_policy
        if timestamp in self.ts_ind_map:  # Duplicate policy
            self.sorted_list[self.ts_ind_map[timestamp]] = (timestamp, value)
            return timestamp
        self.sorted_list.append((timestamp, value))
        self.ts_ind_map[timestamp] = len(self.sorted_list) - 1
        self.rules = [rule for rule in self.rules if rule.dest_key.name in self._db]
        for rule in self.rules:
            rule.apply((timestamp, value))
        self.max_timestamp = max(self.max_timestamp, timestamp)
        return timestamp

    def incrby(self, timestamp: int, value: float) -> Union[int, None]:
        if len(self.sorted_list) == 0:
            return self.add(timestamp, value)
        if timestamp == self.max_timestamp:
            ind = self.ts_ind_map[timestamp]
            self.sorted_list[ind] = (timestamp, self.sorted_list[ind][1] + value)
        elif timestamp > self.max_timestamp:
            ind = self.ts_ind_map[self.max_timestamp]
            self.add(timestamp, self.sorted_list[ind][1] + value)
        else:  # timestamp < self.sorted_list[ind][0]
            raise SimpleError(msgs.TIMESERIES_TIMESTAMP_LOWER_THAN_MAX)
        return timestamp

    def get(self) -> Optional[List[Union[int, float]]]:
        if len(self.sorted_list) == 0:
            return None
        ind = self.ts_ind_map[self.max_timestamp]
        return [self.sorted_list[ind][0], self.sorted_list[ind][1]]

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
        rule.dest_key.source_key = None

    def range(
            self, from_ts: int, to_ts: int,
            latest: bool, value_min: Optional[float], value_max: Optional[float], count: Optional[int],
    ) -> List[List[Union[int, float]]]:
        value_min = value_min or float("-inf")
        value_max = value_max or float("inf")
        res: List[List[Union[int, float]]] = [
            [x[0], x[1]] for x in self.sorted_list
            if (from_ts <= x[0] <= to_ts
                and value_min <= x[1] <= value_max)
        ]
        if count:
            res = res[:count]
        return res


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
