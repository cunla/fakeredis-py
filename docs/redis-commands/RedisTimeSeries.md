# Time Series commands

Module currently not implemented in fakeredis.


### Unsupported timeseries commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [TS.CREATE](https://redis.io/commands/ts.create/) <small>(not implemented)</small>

Create a new time series

#### [TS.DEL](https://redis.io/commands/ts.del/) <small>(not implemented)</small>

Delete all samples between two timestamps for a given time series

#### [TS.ALTER](https://redis.io/commands/ts.alter/) <small>(not implemented)</small>

Update the retention, chunk size, duplicate policy, and labels of an existing time series

#### [TS.ADD](https://redis.io/commands/ts.add/) <small>(not implemented)</small>

Append a sample to a time series

#### [TS.MADD](https://redis.io/commands/ts.madd/) <small>(not implemented)</small>

Append new samples to one or more time series

#### [TS.INCRBY](https://redis.io/commands/ts.incrby/) <small>(not implemented)</small>

Increase the value of the sample with the maximal existing timestamp, or create a new sample with a value equal to the value of the sample with the maximal existing timestamp with a given increment

#### [TS.DECRBY](https://redis.io/commands/ts.decrby/) <small>(not implemented)</small>

Decrease the value of the sample with the maximal existing timestamp, or create a new sample with a value equal to the value of the sample with the maximal existing timestamp with a given decrement

#### [TS.CREATERULE](https://redis.io/commands/ts.createrule/) <small>(not implemented)</small>

Create a compaction rule

#### [TS.DELETERULE](https://redis.io/commands/ts.deleterule/) <small>(not implemented)</small>

Delete a compaction rule

#### [TS.RANGE](https://redis.io/commands/ts.range/) <small>(not implemented)</small>

Query a range in forward direction

#### [TS.REVRANGE](https://redis.io/commands/ts.revrange/) <small>(not implemented)</small>

Query a range in reverse direction

#### [TS.MRANGE](https://redis.io/commands/ts.mrange/) <small>(not implemented)</small>

Query a range across multiple time series by filters in forward direction

#### [TS.MREVRANGE](https://redis.io/commands/ts.mrevrange/) <small>(not implemented)</small>

Query a range across multiple time-series by filters in reverse direction

#### [TS.GET](https://redis.io/commands/ts.get/) <small>(not implemented)</small>

Get the last sample

#### [TS.MGET](https://redis.io/commands/ts.mget/) <small>(not implemented)</small>

Get the last samples matching a specific filter

#### [TS.INFO](https://redis.io/commands/ts.info/) <small>(not implemented)</small>

Returns information and statistics for a time series

#### [TS.QUERYINDEX](https://redis.io/commands/ts.queryindex/) <small>(not implemented)</small>

Get all time series keys matching a filter list


