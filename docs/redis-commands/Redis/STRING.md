# Redis `string` commands (22/22 implemented)

## [APPEND](https://redis.io/commands/append/)

Appends a string to the value of a key. Creates the key if it doesn't exist.

## [DECR](https://redis.io/commands/decr/)

Decrements the integer value of a key by one. Uses 0 as initial value if the key doesn't exist.

## [DECRBY](https://redis.io/commands/decrby/)

Decrements a number from the integer value of a key. Uses 0 as initial value if the key doesn't exist.

## [GET](https://redis.io/commands/get/)

Returns the string value of a key.

## [GETDEL](https://redis.io/commands/getdel/)

Returns the string value of a key after deleting the key.

## [GETEX](https://redis.io/commands/getex/)

Returns the string value of a key after setting its expiration time.

## [GETRANGE](https://redis.io/commands/getrange/)

Returns a substring of the string stored at a key.

## [GETSET](https://redis.io/commands/getset/)

Returns the previous string value of a key after setting it to a new value.

## [INCR](https://redis.io/commands/incr/)

Increments the integer value of a key by one. Uses 0 as initial value if the key doesn't exist.

## [INCRBY](https://redis.io/commands/incrby/)

Increments the integer value of a key by a number. Uses 0 as initial value if the key doesn't exist.

## [INCRBYFLOAT](https://redis.io/commands/incrbyfloat/)

Increment the floating point value of a key by a number. Uses 0 as initial value if the key doesn't exist.

## [LCS](https://redis.io/commands/lcs/)

Finds the longest common substring.

## [MGET](https://redis.io/commands/mget/)

Atomically returns the string values of one or more keys.

## [MSET](https://redis.io/commands/mset/)

Atomically creates or modifies the string values of one or more keys.

## [MSETNX](https://redis.io/commands/msetnx/)

Atomically modifies the string values of one or more keys only when all keys don't exist.

## [PSETEX](https://redis.io/commands/psetex/)

Sets both string value and expiration time in milliseconds of a key. The key is created if it doesn't exist.

## [SET](https://redis.io/commands/set/)

Sets the string value of a key, ignoring its type. The key is created if it doesn't exist.

## [SETEX](https://redis.io/commands/setex/)

Sets the string value and expiration time of a key. Creates the key if it doesn't exist.

## [SETNX](https://redis.io/commands/setnx/)

Set the string value of a key only when the key doesn't exist.

## [SETRANGE](https://redis.io/commands/setrange/)

Overwrites a part of a string value with another by an offset. Creates the key if it doesn't exist.

## [STRLEN](https://redis.io/commands/strlen/)

Returns the length of a string value.

## [SUBSTR](https://redis.io/commands/substr/)

Returns a substring from a string value.



