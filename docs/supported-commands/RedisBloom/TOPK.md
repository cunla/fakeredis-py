# RedisBloom `topk` commands (7/7 implemented)

## [TOPK.ADD](https://redis.io/commands/topk.add/)

Adds an item to a Top-k sketch. Multiple items can be added at the same time.

## [TOPK.COUNT](https://redis.io/commands/topk.count/)

Return the count for one or more items are in a sketch

## [TOPK.INCRBY](https://redis.io/commands/topk.incrby/)

Increases the count of one or more items by increment

## [TOPK.INFO](https://redis.io/commands/topk.info/)

Returns information about a sketch

## [TOPK.LIST](https://redis.io/commands/topk.list/)

Return the full list of items in Top-K sketch.

## [TOPK.QUERY](https://redis.io/commands/topk.query/)

Checks whether one or more items are in a sketch

## [TOPK.RESERVE](https://redis.io/commands/topk.reserve/)

Initializes a Top-K sketch with specified parameters
