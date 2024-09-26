# RedisBloom `bf` commands (10/10 implemented)

## [BF.RESERVE](https://redis.io/commands/bf.reserve/)

Creates a new Bloom Filter

## [BF.ADD](https://redis.io/commands/bf.add/)

Adds an item to a Bloom Filter

## [BF.MADD](https://redis.io/commands/bf.madd/)

Adds one or more items to a Bloom Filter. A filter will be created if it does not exist

## [BF.INSERT](https://redis.io/commands/bf.insert/)

Adds one or more items to a Bloom Filter. A filter will be created if it does not exist

## [BF.EXISTS](https://redis.io/commands/bf.exists/)

Checks whether an item exists in a Bloom Filter

## [BF.MEXISTS](https://redis.io/commands/bf.mexists/)

Checks whether one or more items exist in a Bloom Filter

## [BF.SCANDUMP](https://redis.io/commands/bf.scandump/)

Begins an incremental save of the bloom filter

## [BF.LOADCHUNK](https://redis.io/commands/bf.loadchunk/)

Restores a filter previously saved using SCANDUMP

## [BF.INFO](https://redis.io/commands/bf.info/)

Returns information about a Bloom Filter

## [BF.CARD](https://redis.io/commands/bf.card/)

Returns the cardinality of a Bloom filter



