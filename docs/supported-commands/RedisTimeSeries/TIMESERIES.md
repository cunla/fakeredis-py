# RedisTimeSeries `timeseries` commands (21/21 implemented)

## [TS.ADD](https://redis.io/commands/ts.add/)

Append a sample to a time series

## [TS.ALTER](https://redis.io/commands/ts.alter/)

Update the retention, chunk size, duplicate policy, and labels of an existing time series

## [TS.CREATE](https://redis.io/commands/ts.create/)

Create a new time series

## [TS.CREATERULE](https://redis.io/commands/ts.createrule/)

Create a compaction rule

## [TS.DECRBY](https://redis.io/commands/ts.decrby/)

Decrease the value of the latest sample

## [TS.DEL](https://redis.io/commands/ts.del/)

Delete all samples between two timestamps for a given time series

## [TS.DELETERULE](https://redis.io/commands/ts.deleterule/)

Delete a compaction rule

## [TS.GET](https://redis.io/commands/ts.get/)

Get the sample with the highest timestamp from a given time series

## [TS.INCRBY](https://redis.io/commands/ts.incrby/)

Increase the value of the latest sample

## [TS.INFO](https://redis.io/commands/ts.info/)

Returns information and statistics for a time series

## [TS.MADD](https://redis.io/commands/ts.madd/)

Append new samples to one or more time series

## [TS.MGET](https://redis.io/commands/ts.mget/)

Get the sample with the highest timestamp from each time series matching a specific filter

## [TS.MRANGE](https://redis.io/commands/ts.mrange/)

Query a range across multiple time series by filters in forward direction

## [TS.MREVRANGE](https://redis.io/commands/ts.mrevrange/)

Query a range across multiple time series by filters in reverse direction

## [TS.NRANGE](https://redis.io/commands/ts.nrange/)

Query a range across multiple time series in forward direction, returning the results pivoted by timestamp (one value column per key)

## [TS.NREVRANGE](https://redis.io/commands/ts.nrevrange/)

Query a range across multiple time series in reverse direction, returning the results pivoted by timestamp (one value column per key)

## [TS.QUERYINDEX](https://redis.io/commands/ts.queryindex/)

Get all time series keys matching a filter list

## [TS.QUERYLABELS](https://redis.io/commands/ts.querylabels/)

Get all label names, or all values of a given label, for time series matching a filter list, or all series

## [TS.RANGE](https://redis.io/commands/ts.range/)

Query a range in forward direction

## [TS.READ](https://redis.io/commands/ts.read/)

Read: return up to max_count samples with timestamp >= timestamp. With BLOCK, waits up to milliseconds ms until at least min_count qualifying samples exist

## [TS.REVRANGE](https://redis.io/commands/ts.revrange/)

Query a range in reverse direction



