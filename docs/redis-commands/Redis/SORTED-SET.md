# `sorted-set` commands (35/35 implemented)

## [BZMPOP](https://redis.io/commands/bzmpop/)

Removes and returns a member by score from one or more sorted sets. Blocks until a member is available otherwise. Deletes the sorted set if the last element was popped.

## [BZPOPMAX](https://redis.io/commands/bzpopmax/)

Removes and returns the member with the highest score from one or more sorted sets. Blocks until a member available otherwise.  Deletes the sorted set if the last element was popped.

## [BZPOPMIN](https://redis.io/commands/bzpopmin/)

Removes and returns the member with the lowest score from one or more sorted sets. Blocks until a member is available otherwise. Deletes the sorted set if the last element was popped.

## [ZADD](https://redis.io/commands/zadd/)

Adds one or more members to a sorted set, or updates their scores. Creates the key if it doesn't exist.

## [ZCARD](https://redis.io/commands/zcard/)

Returns the number of members in a sorted set.

## [ZCOUNT](https://redis.io/commands/zcount/)

Returns the count of members in a sorted set that have scores within a range.

## [ZDIFF](https://redis.io/commands/zdiff/)

Returns the difference between multiple sorted sets.

## [ZDIFFSTORE](https://redis.io/commands/zdiffstore/)

Stores the difference of multiple sorted sets in a key.

## [ZINCRBY](https://redis.io/commands/zincrby/)

Increments the score of a member in a sorted set.

## [ZINTER](https://redis.io/commands/zinter/)

Returns the intersect of multiple sorted sets.

## [ZINTERCARD](https://redis.io/commands/zintercard/)

Returns the number of members of the intersect of multiple sorted sets.

## [ZINTERSTORE](https://redis.io/commands/zinterstore/)

Stores the intersect of multiple sorted sets in a key.

## [ZLEXCOUNT](https://redis.io/commands/zlexcount/)

Returns the number of members in a sorted set within a lexicographical range.

## [ZMPOP](https://redis.io/commands/zmpop/)

Returns the highest- or lowest-scoring members from one or more sorted sets after removing them. Deletes the sorted set if the last member was popped.

## [ZMSCORE](https://redis.io/commands/zmscore/)

Returns the score of one or more members in a sorted set.

## [ZPOPMAX](https://redis.io/commands/zpopmax/)

Returns the highest-scoring members from a sorted set after removing them. Deletes the sorted set if the last member was popped.

## [ZPOPMIN](https://redis.io/commands/zpopmin/)

Returns the lowest-scoring members from a sorted set after removing them. Deletes the sorted set if the last member was popped.

## [ZRANDMEMBER](https://redis.io/commands/zrandmember/)

Returns one or more random members from a sorted set.

## [ZRANGE](https://redis.io/commands/zrange/)

Returns members in a sorted set within a range of indexes.

## [ZRANGEBYLEX](https://redis.io/commands/zrangebylex/)

Returns members in a sorted set within a lexicographical range.

## [ZRANGEBYSCORE](https://redis.io/commands/zrangebyscore/)

Returns members in a sorted set within a range of scores.

## [ZRANGESTORE](https://redis.io/commands/zrangestore/)

Stores a range of members from sorted set in a key.

## [ZRANK](https://redis.io/commands/zrank/)

Returns the index of a member in a sorted set ordered by ascending scores.

## [ZREM](https://redis.io/commands/zrem/)

Removes one or more members from a sorted set. Deletes the sorted set if all members were removed.

## [ZREMRANGEBYLEX](https://redis.io/commands/zremrangebylex/)

Removes members in a sorted set within a lexicographical range. Deletes the sorted set if all members were removed.

## [ZREMRANGEBYRANK](https://redis.io/commands/zremrangebyrank/)

Removes members in a sorted set within a range of indexes. Deletes the sorted set if all members were removed.

## [ZREMRANGEBYSCORE](https://redis.io/commands/zremrangebyscore/)

Removes members in a sorted set within a range of scores. Deletes the sorted set if all members were removed.

## [ZREVRANGE](https://redis.io/commands/zrevrange/)

Returns members in a sorted set within a range of indexes in reverse order.

## [ZREVRANGEBYLEX](https://redis.io/commands/zrevrangebylex/)

Returns members in a sorted set within a lexicographical range in reverse order.

## [ZREVRANGEBYSCORE](https://redis.io/commands/zrevrangebyscore/)

Returns members in a sorted set within a range of scores in reverse order.

## [ZREVRANK](https://redis.io/commands/zrevrank/)

Returns the index of a member in a sorted set ordered by descending scores.

## [ZSCAN](https://redis.io/commands/zscan/)

Iterates over members and scores of a sorted set.

## [ZSCORE](https://redis.io/commands/zscore/)

Returns the score of a member in a sorted set.

## [ZUNION](https://redis.io/commands/zunion/)

Returns the union of multiple sorted sets.

## [ZUNIONSTORE](https://redis.io/commands/zunionstore/)

Stores the union of multiple sorted sets in a key.



