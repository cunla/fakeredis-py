# RedisTimeSeries `timeseries` commands (17/17 implemented)

## [TS.CREATE](https://redis.io/commands/ts.create/)

Create a new time series

## [TS.DEL](https://redis.io/commands/ts.del/)

Delete all samples between two timestamps for a given time series

## [TS.ALTER](https://redis.io/commands/ts.alter/)

Update the retention, chunk size, duplicate policy, and labels of an existing time series

## [TS.ADD](https://redis.io/commands/ts.add/)

Append a sample to a time series

## [TS.MADD](https://redis.io/commands/ts.madd/)

Append new samples to one or more time series

## [TS.INCRBY](https://redis.io/commands/ts.incrby/)

Increase the value of the sample with the maximum existing timestamp, or create a new sample with a value equal to the value of the sample with the maximum existing timestamp with a given increment

## [TS.DECRBY](https://redis.io/commands/ts.decrby/)

Decrease the value of the sample with the maximum existing timestamp, or create a new sample with a value equal to the value of the sample with the maximum existing timestamp with a given decrement

## [TS.CREATERULE](https://redis.io/commands/ts.createrule/)

Create a compaction rule

## [TS.DELETERULE](https://redis.io/commands/ts.deleterule/)

Delete a compaction rule

## [TS.RANGE](https://redis.io/commands/ts.range/)

Query a range in forward direction

## [TS.REVRANGE](https://redis.io/commands/ts.revrange/)

Query a range in reverse direction

## [TS.MRANGE](https://redis.io/commands/ts.mrange/)

Query a range across multiple time series by filters in forward direction

## [TS.MREVRANGE](https://redis.io/commands/ts.mrevrange/)

Query a range across multiple time-series by filters in reverse direction

## [TS.GET](https://redis.io/commands/ts.get/)

Get the sample with the highest timestamp from a given time series

## [TS.MGET](https://redis.io/commands/ts.mget/)

Get the sample with the highest timestamp from each time series matching a specific filter

## [TS.INFO](https://redis.io/commands/ts.info/)

Returns information and statistics for a time series

## [TS.QUERYINDEX](https://redis.io/commands/ts.queryindex/)

Get all time series keys matching a filter list



