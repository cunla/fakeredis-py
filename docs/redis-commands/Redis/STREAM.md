# Redis `stream` commands (20/20 implemented)

## [XACK](https://redis.io/commands/xack/)

Returns the number of messages that were successfully acknowledged by the consumer group member of a stream.

## [XADD](https://redis.io/commands/xadd/)

Appends a new message to a stream. Creates the key if it doesn't exist.

## [XAUTOCLAIM](https://redis.io/commands/xautoclaim/)

Changes, or acquires, ownership of messages in a consumer group, as if the messages were delivered to as consumer group member.

## [XCLAIM](https://redis.io/commands/xclaim/)

Changes, or acquires, ownership of a message in a consumer group, as if the message was delivered a consumer group member.

## [XDEL](https://redis.io/commands/xdel/)

Returns the number of messages after removing them from a stream.

## [XGROUP CREATE](https://redis.io/commands/xgroup-create/)

Creates a consumer group.

## [XGROUP CREATECONSUMER](https://redis.io/commands/xgroup-createconsumer/)

Creates a consumer in a consumer group.

## [XGROUP DELCONSUMER](https://redis.io/commands/xgroup-delconsumer/)

Deletes a consumer from a consumer group.

## [XGROUP DESTROY](https://redis.io/commands/xgroup-destroy/)

Destroys a consumer group.

## [XGROUP SETID](https://redis.io/commands/xgroup-setid/)

Sets the last-delivered ID of a consumer group.

## [XINFO CONSUMERS](https://redis.io/commands/xinfo-consumers/)

Returns a list of the consumers in a consumer group.

## [XINFO GROUPS](https://redis.io/commands/xinfo-groups/)

Returns a list of the consumer groups of a stream.

## [XINFO STREAM](https://redis.io/commands/xinfo-stream/)

Returns information about a stream.

## [XLEN](https://redis.io/commands/xlen/)

Return the number of messages in a stream.

## [XPENDING](https://redis.io/commands/xpending/)

Returns the information and entries from a stream consumer group's pending entries list.

## [XRANGE](https://redis.io/commands/xrange/)

Returns the messages from a stream within a range of IDs.

## [XREAD](https://redis.io/commands/xread/)

Returns messages from multiple streams with IDs greater than the ones requested. Blocks until a message is available otherwise.

## [XREADGROUP](https://redis.io/commands/xreadgroup/)

Returns new or historical messages from a stream for a consumer in a group. Blocks until a message is available otherwise.

## [XREVRANGE](https://redis.io/commands/xrevrange/)

Returns the messages from a stream within a range of IDs in reverse order.

## [XTRIM](https://redis.io/commands/xtrim/)

Deletes messages from the beginning of a stream.



