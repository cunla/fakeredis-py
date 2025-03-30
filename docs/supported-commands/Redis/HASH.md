# Redis `hash` commands (25/27 implemented)

## [HDEL](https://redis.io/commands/hdel/)

Deletes one or more fields and their values from a hash. Deletes the hash if no fields remain.

## [HEXISTS](https://redis.io/commands/hexists/)

Determines whether a field exists in a hash.

## [HEXPIRE](https://redis.io/commands/hexpire/)

Set expiry for hash field using relative time to expire (seconds)

## [HEXPIREAT](https://redis.io/commands/hexpireat/)

Set expiry for hash field using an absolute Unix timestamp (seconds)

## [HEXPIRETIME](https://redis.io/commands/hexpiretime/)

Returns the expiration time of a hash field as a Unix timestamp, in seconds.

## [HGET](https://redis.io/commands/hget/)

Returns the value of a field in a hash.

## [HGETALL](https://redis.io/commands/hgetall/)

Returns all fields and values in a hash.

## [HINCRBY](https://redis.io/commands/hincrby/)

Increments the integer value of a field in a hash by a number. Uses 0 as initial value if the field doesn't exist.

## [HINCRBYFLOAT](https://redis.io/commands/hincrbyfloat/)

Increments the floating point value of a field by a number. Uses 0 as initial value if the field doesn't exist.

## [HKEYS](https://redis.io/commands/hkeys/)

Returns all fields in a hash.

## [HLEN](https://redis.io/commands/hlen/)

Returns the number of fields in a hash.

## [HMGET](https://redis.io/commands/hmget/)

Returns the values of all fields in a hash.

## [HMSET](https://redis.io/commands/hmset/)

Sets the values of multiple fields.

## [HPERSIST](https://redis.io/commands/hpersist/)

Removes the expiration time for each specified field

## [HPEXPIRE](https://redis.io/commands/hpexpire/)

Set expiry for hash field using relative time to expire (milliseconds)

## [HPEXPIREAT](https://redis.io/commands/hpexpireat/)

Set expiry for hash field using an absolute Unix timestamp (milliseconds)

## [HPEXPIRETIME](https://redis.io/commands/hpexpiretime/)

Returns the expiration time of a hash field as a Unix timestamp, in msec.

## [HPTTL](https://redis.io/commands/hpttl/)

Returns the TTL in milliseconds of a hash field.

## [HRANDFIELD](https://redis.io/commands/hrandfield/)

Returns one or more random fields from a hash.

## [HSCAN](https://redis.io/commands/hscan/)

Iterates over fields and values of a hash.

## [HSET](https://redis.io/commands/hset/)

Creates or modifies the value of a field in a hash.

## [HSETNX](https://redis.io/commands/hsetnx/)

Sets the value of a field in a hash only when the field doesn't exist.

## [HSTRLEN](https://redis.io/commands/hstrlen/)

Returns the length of the value of a field.

## [HTTL](https://redis.io/commands/httl/)

Returns the TTL in seconds of a hash field.

## [HVALS](https://redis.io/commands/hvals/)

Returns all values in a hash.


## Unsupported hash commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [HGETF](https://redis.io/commands/hgetf/) <small>(not implemented)</small>

For each specified field, returns its value and optionally set the field's remaining expiration time in seconds / milliseconds

#### [HSETF](https://redis.io/commands/hsetf/) <small>(not implemented)</small>

For each specified field, returns its value and optionally set the field's remaining expiration time in seconds / milliseconds


