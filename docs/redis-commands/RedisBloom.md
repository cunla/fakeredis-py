# Probabilistic commands

Module currently not implemented in fakeredis.


### Unsupported bf commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [BF.RESERVE](https://redis.io/commands/bf.reserve/)

Creates a new Bloom Filter

#### [BF.ADD](https://redis.io/commands/bf.add/)

Adds an item to a Bloom Filter

#### [BF.MADD](https://redis.io/commands/bf.madd/)

Adds one or more items to a Bloom Filter. A filter will be created if it does not exist

#### [BF.INSERT](https://redis.io/commands/bf.insert/)

Adds one or more items to a Bloom Filter. A filter will be created if it does not exist

#### [BF.EXISTS](https://redis.io/commands/bf.exists/)

Checks whether an item exists in a Bloom Filter

#### [BF.MEXISTS](https://redis.io/commands/bf.mexists/)

Checks whether one or more items exist in a Bloom Filter

#### [BF.SCANDUMP](https://redis.io/commands/bf.scandump/)

Begins an incremental save of the bloom filter

#### [BF.LOADCHUNK](https://redis.io/commands/bf.loadchunk/)

Restores a filter previously saved using SCANDUMP

#### [BF.INFO](https://redis.io/commands/bf.info/)

Returns information about a Bloom Filter



### Unsupported cf commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [CF.RESERVE](https://redis.io/commands/cf.reserve/)

Creates a new Cuckoo Filter

#### [CF.ADD](https://redis.io/commands/cf.add/)

Adds an item to a Cuckoo Filter

#### [CF.ADDNX](https://redis.io/commands/cf.addnx/)

Adds an item to a Cuckoo Filter if the item did not exist previously.

#### [CF.INSERT](https://redis.io/commands/cf.insert/)

Adds one or more items to a Cuckoo Filter. A filter will be created if it does not exist

#### [CF.INSERTNX](https://redis.io/commands/cf.insertnx/)

Adds one or more items to a Cuckoo Filter if the items did not exist previously. A filter will be created if it does not exist

#### [CF.EXISTS](https://redis.io/commands/cf.exists/)

Checks whether one or more items exist in a Cuckoo Filter

#### [CF.MEXISTS](https://redis.io/commands/cf.mexists/)

Checks whether one or more items exist in a Cuckoo Filter

#### [CF.DEL](https://redis.io/commands/cf.del/)

Deletes an item from a Cuckoo Filter

#### [CF.COUNT](https://redis.io/commands/cf.count/)

Return the number of times an item might be in a Cuckoo Filter

#### [CF.SCANDUMP](https://redis.io/commands/cf.scandump/)

Begins an incremental save of the bloom filter

#### [CF.LOADCHUNK](https://redis.io/commands/cf.loadchunk/)

Restores a filter previously saved using SCANDUMP

#### [CF.INFO](https://redis.io/commands/cf.info/)

Returns information about a Cuckoo Filter



### Unsupported cms commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [CMS.INITBYDIM](https://redis.io/commands/cms.initbydim/)

Initializes a Count-Min Sketch to dimensions specified by user

#### [CMS.INITBYPROB](https://redis.io/commands/cms.initbyprob/)

Initializes a Count-Min Sketch to accommodate requested tolerances.

#### [CMS.INCRBY](https://redis.io/commands/cms.incrby/)

Increases the count of one or more items by increment

#### [CMS.QUERY](https://redis.io/commands/cms.query/)

Returns the count for one or more items in a sketch

#### [CMS.MERGE](https://redis.io/commands/cms.merge/)

Merges several sketches into one sketch

#### [CMS.INFO](https://redis.io/commands/cms.info/)

Returns information about a sketch



### Unsupported topk commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [TOPK.RESERVE](https://redis.io/commands/topk.reserve/)

Initializes a TopK with specified parameters

#### [TOPK.ADD](https://redis.io/commands/topk.add/)

Increases the count of one or more items by increment

#### [TOPK.INCRBY](https://redis.io/commands/topk.incrby/)

Increases the count of one or more items by increment

#### [TOPK.QUERY](https://redis.io/commands/topk.query/)

Checks whether one or more items are in a sketch

#### [TOPK.COUNT](https://redis.io/commands/topk.count/)

Return the count for one or more items are in a sketch

#### [TOPK.LIST](https://redis.io/commands/topk.list/)

Return full list of items in Top K list

#### [TOPK.INFO](https://redis.io/commands/topk.info/)

Returns information about a sketch



### Unsupported tdigest commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [TDIGEST.CREATE](https://redis.io/commands/tdigest.create/)

Allocates memory and initializes a new t-digest sketch

#### [TDIGEST.RESET](https://redis.io/commands/tdigest.reset/)

Resets a t-digest sketch: empty the sketch and re-initializes it.

#### [TDIGEST.ADD](https://redis.io/commands/tdigest.add/)

Adds one or more observations to a t-digest sketch

#### [TDIGEST.MERGE](https://redis.io/commands/tdigest.merge/)

Merges multiple t-digest sketches into a single sketch

#### [TDIGEST.MIN](https://redis.io/commands/tdigest.min/)

Returns the minimum observation value from a t-digest sketch

#### [TDIGEST.MAX](https://redis.io/commands/tdigest.max/)

Returns the maximum observation value from a t-digest sketch

#### [TDIGEST.QUANTILE](https://redis.io/commands/tdigest.quantile/)

Returns, for each input fraction, an estimation of the value (floating point) that is smaller than the given fraction of observations

#### [TDIGEST.CDF](https://redis.io/commands/tdigest.cdf/)

Returns, for each input value, an estimation of the fraction (floating-point) of (observations smaller than the given value + half the observations equal to the given value)

#### [TDIGEST.TRIMMED_MEAN](https://redis.io/commands/tdigest.trimmed_mean/)

Returns an estimation of the mean value from the sketch, excluding observation values outside the low and high cutoff quantiles

#### [TDIGEST.RANK](https://redis.io/commands/tdigest.rank/)

Returns, for each input value (floating-point), the estimated rank of the value (the number of observations in the sketch that are smaller than the value + half the number of observations that are equal to the value)

#### [TDIGEST.REVRANK](https://redis.io/commands/tdigest.revrank/)

Returns, for each input value (floating-point), the estimated reverse rank of the value (the number of observations in the sketch that are larger than the value + half the number of observations that are equal to the value)

#### [TDIGEST.BYRANK](https://redis.io/commands/tdigest.byrank/)

Returns, for each input rank, an estimation of the value (floating-point) with that rank

#### [TDIGEST.BYREVRANK](https://redis.io/commands/tdigest.byrevrank/)

Returns, for each input reverse rank, an estimation of the value (floating-point) with that reverse rank

#### [TDIGEST.INFO](https://redis.io/commands/tdigest.info/)

Returns information and statistics about a t-digest sketch


