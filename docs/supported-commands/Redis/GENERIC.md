# Redis `generic` commands (24/31 implemented)

## [COPY](https://redis.io/commands/copy/)

Copies the value of a key to a new key.

## [DEL](https://redis.io/commands/del/)

Deletes one or more keys.

## [DUMP](https://redis.io/commands/dump/)

Returns a serialized representation of the value stored at a key.

## [EXISTS](https://redis.io/commands/exists/)

Determines whether one or more keys exist.

## [EXPIRE](https://redis.io/commands/expire/)

Sets the expiration time of a key in seconds.

## [EXPIREAT](https://redis.io/commands/expireat/)

Sets the expiration time of a key to a Unix timestamp.

## [EXPIRETIME](https://redis.io/commands/expiretime/)

Returns the expiration time of a key as a Unix timestamp.

## [KEYS](https://redis.io/commands/keys/)

Returns all key names that match a pattern.

## [MOVE](https://redis.io/commands/move/)

Moves a key to another database.

## [PERSIST](https://redis.io/commands/persist/)

Removes the expiration time of a key.

## [PEXPIRE](https://redis.io/commands/pexpire/)

Sets the expiration time of a key in milliseconds.

## [PEXPIREAT](https://redis.io/commands/pexpireat/)

Sets the expiration time of a key to a Unix milliseconds timestamp.

## [PEXPIRETIME](https://redis.io/commands/pexpiretime/)

Returns the expiration time of a key as a Unix milliseconds timestamp.

## [PTTL](https://redis.io/commands/pttl/)

Returns the expiration time in milliseconds of a key.

## [RANDOMKEY](https://redis.io/commands/randomkey/)

Returns a random key name from the database.

## [RENAME](https://redis.io/commands/rename/)

Renames a key and overwrites the destination.

## [RENAMENX](https://redis.io/commands/renamenx/)

Renames a key only when the target key name doesn't exist.

## [RESTORE](https://redis.io/commands/restore/)

Creates a key from the serialized representation of a value.

## [SCAN](https://redis.io/commands/scan/)

Iterates over the key names in the database.

## [SORT](https://redis.io/commands/sort/)

Sorts the elements in a list, a set, or a sorted set, optionally storing the result.

## [SORT_RO](https://redis.io/commands/sort_ro/)

Returns the sorted elements of a list, a set, or a sorted set.

## [TTL](https://redis.io/commands/ttl/)

Returns the expiration time in seconds of a key.

## [TYPE](https://redis.io/commands/type/)

Determines the type of value stored at a key.

## [UNLINK](https://redis.io/commands/unlink/)

Asynchronously deletes one or more keys.


## Unsupported generic commands 
> To implement support for a command, see [here](../../../guides/implement-command/) 

#### [BLESS](https://redis.io/commands/bless/) <small>(not implemented)</small>

A container for key-blessing commands.

#### [BLESS CLEAR](https://redis.io/commands/bless-clear/) <small>(not implemented)</small>

Removes protection flags from a key.

#### [BLESS GET](https://redis.io/commands/bless-get/) <small>(not implemented)</small>

Returns the active protection flags of a key.

#### [BLESS SCAN](https://redis.io/commands/bless-scan/) <small>(not implemented)</small>

Incrementally iterates the blessed keys of the current database that carry the given flag.

#### [BLESS SET](https://redis.io/commands/bless-set/) <small>(not implemented)</small>

Adds protection flags to a key against memory pressure.

#### [WAIT](https://redis.io/commands/wait/) <small>(not implemented)</small>

Blocks until the asynchronous replication of all preceding write commands sent by the connection is completed.

#### [WAITAOF](https://redis.io/commands/waitaof/) <small>(not implemented)</small>

Blocks until all of the preceding write commands sent by the connection are written to the append-only file of the master and/or replicas.


