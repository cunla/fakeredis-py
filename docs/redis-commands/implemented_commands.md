# Supported commands

Here is a list of all redis [implemented commands](#implemented-commands) and a
list of [unimplemented commands](#unimplemented-commands).

------


## string commands

### [APPEND](https://redis.io/commands/append/)

Append a value to a key

### [DECR](https://redis.io/commands/decr/)

Decrement the integer value of a key by one

### [DECRBY](https://redis.io/commands/decrby/)

Decrement the integer value of a key by the given number

### [GET](https://redis.io/commands/get/)

Get the value of a key

### [GETDEL](https://redis.io/commands/getdel/)

Get the value of a key and delete the key

### [GETEX](https://redis.io/commands/getex/)

Get the value of a key and optionally set its expiration

### [GETRANGE](https://redis.io/commands/getrange/)

Get a substring of the string stored at a key

### [GETSET](https://redis.io/commands/getset/)

Set the string value of a key and return its old value

### [INCR](https://redis.io/commands/incr/)

Increment the integer value of a key by one

### [INCRBY](https://redis.io/commands/incrby/)

Increment the integer value of a key by the given amount

### [INCRBYFLOAT](https://redis.io/commands/incrbyfloat/)

Increment the float value of a key by the given amount

### [LCS](https://redis.io/commands/lcs/)

Find longest common substring

### [MGET](https://redis.io/commands/mget/)

Get the values of all the given keys

### [MSET](https://redis.io/commands/mset/)

Set multiple keys to multiple values

### [MSETNX](https://redis.io/commands/msetnx/)

Set multiple keys to multiple values, only if none of the keys exist

### [PSETEX](https://redis.io/commands/psetex/)

Set the value and expiration in milliseconds of a key

### [SET](https://redis.io/commands/set/)

Set the string value of a key

### [SETEX](https://redis.io/commands/setex/)

Set the value and expiration of a key

### [SETNX](https://redis.io/commands/setnx/)

Set the value of a key, only if the key does not exist

### [SETRANGE](https://redis.io/commands/setrange/)

Overwrite part of a string at key starting at the specified offset

### [STRLEN](https://redis.io/commands/strlen/)

Get the length of the value stored in a key

### [SUBSTR](https://redis.io/commands/substr/)

Get a substring of the string stored at a key


## server commands

### [BGSAVE](https://redis.io/commands/bgsave/)

Asynchronously save the dataset to disk

### [DBSIZE](https://redis.io/commands/dbsize/)

Return the number of keys in the selected database

### [FLUSHALL](https://redis.io/commands/flushall/)

Remove all keys from all databases

### [FLUSHDB](https://redis.io/commands/flushdb/)

Remove all keys from the current database

### [LASTSAVE](https://redis.io/commands/lastsave/)

Get the UNIX time stamp of the last successful save to disk

### [SAVE](https://redis.io/commands/save/)

Synchronously save the dataset to disk

### [SWAPDB](https://redis.io/commands/swapdb/)

Swaps two Redis databases

### [TIME](https://redis.io/commands/time/)

Return the current server time


## bitmap commands

### [BITCOUNT](https://redis.io/commands/bitcount/)

Count set bits in a string

### [BITOP](https://redis.io/commands/bitop/)

Perform bitwise operations between strings

### [BITPOS](https://redis.io/commands/bitpos/)

Find first bit set or clear in a string

### [GETBIT](https://redis.io/commands/getbit/)

Returns the bit value at offset in the string value stored at key

### [SETBIT](https://redis.io/commands/setbit/)

Sets or clears the bit at offset in the string value stored at key


## list commands

### [BLPOP](https://redis.io/commands/blpop/)

Remove and get the first element in a list, or block until one is available

### [BRPOP](https://redis.io/commands/brpop/)

Remove and get the last element in a list, or block until one is available

### [BRPOPLPUSH](https://redis.io/commands/brpoplpush/)

Pop an element from a list, push it to another list and return it; or block until one is available

### [LINDEX](https://redis.io/commands/lindex/)

Get an element from a list by its index

### [LINSERT](https://redis.io/commands/linsert/)

Insert an element before or after another element in a list

### [LLEN](https://redis.io/commands/llen/)

Get the length of a list

### [LMOVE](https://redis.io/commands/lmove/)

Pop an element from a list, push it to another list and return it

### [LPOP](https://redis.io/commands/lpop/)

Remove and get the first elements in a list

### [LPUSH](https://redis.io/commands/lpush/)

Prepend one or multiple elements to a list

### [LPUSHX](https://redis.io/commands/lpushx/)

Prepend an element to a list, only if the list exists

### [LRANGE](https://redis.io/commands/lrange/)

Get a range of elements from a list

### [LREM](https://redis.io/commands/lrem/)

Remove elements from a list

### [LSET](https://redis.io/commands/lset/)

Set the value of an element in a list by its index

### [LTRIM](https://redis.io/commands/ltrim/)

Trim a list to the specified range

### [RPOP](https://redis.io/commands/rpop/)

Remove and get the last elements in a list

### [RPOPLPUSH](https://redis.io/commands/rpoplpush/)

Remove the last element in a list, prepend it to another list and return it

### [RPUSH](https://redis.io/commands/rpush/)

Append one or multiple elements to a list

### [RPUSHX](https://redis.io/commands/rpushx/)

Append an element to a list, only if the list exists


## sorted-set commands

### [BZPOPMAX](https://redis.io/commands/bzpopmax/)

Remove and return the member with the highest score from one or more sorted sets, or block until one is available

### [BZPOPMIN](https://redis.io/commands/bzpopmin/)

Remove and return the member with the lowest score from one or more sorted sets, or block until one is available

### [ZADD](https://redis.io/commands/zadd/)

Add one or more members to a sorted set, or update its score if it already exists

### [ZCARD](https://redis.io/commands/zcard/)

Get the number of members in a sorted set

### [ZCOUNT](https://redis.io/commands/zcount/)

Count the members in a sorted set with scores within the given values

### [ZINCRBY](https://redis.io/commands/zincrby/)

Increment the score of a member in a sorted set

### [ZINTERSTORE](https://redis.io/commands/zinterstore/)

Intersect multiple sorted sets and store the resulting sorted set in a new key

### [ZLEXCOUNT](https://redis.io/commands/zlexcount/)

Count the number of members in a sorted set between a given lexicographical range

### [ZMSCORE](https://redis.io/commands/zmscore/)

Get the score associated with the given members in a sorted set

### [ZPOPMAX](https://redis.io/commands/zpopmax/)

Remove and return members with the highest scores in a sorted set

### [ZPOPMIN](https://redis.io/commands/zpopmin/)

Remove and return members with the lowest scores in a sorted set

### [ZRANGE](https://redis.io/commands/zrange/)

Return a range of members in a sorted set

### [ZRANGEBYLEX](https://redis.io/commands/zrangebylex/)

Return a range of members in a sorted set, by lexicographical range

### [ZRANGEBYSCORE](https://redis.io/commands/zrangebyscore/)

Return a range of members in a sorted set, by score

### [ZRANK](https://redis.io/commands/zrank/)

Determine the index of a member in a sorted set

### [ZREM](https://redis.io/commands/zrem/)

Remove one or more members from a sorted set

### [ZREMRANGEBYLEX](https://redis.io/commands/zremrangebylex/)

Remove all members in a sorted set between the given lexicographical range

### [ZREMRANGEBYRANK](https://redis.io/commands/zremrangebyrank/)

Remove all members in a sorted set within the given indexes

### [ZREMRANGEBYSCORE](https://redis.io/commands/zremrangebyscore/)

Remove all members in a sorted set within the given scores

### [ZREVRANGE](https://redis.io/commands/zrevrange/)

Return a range of members in a sorted set, by index, with scores ordered from high to low

### [ZREVRANGEBYLEX](https://redis.io/commands/zrevrangebylex/)

Return a range of members in a sorted set, by lexicographical range, ordered from higher to lower strings.

### [ZREVRANGEBYSCORE](https://redis.io/commands/zrevrangebyscore/)

Return a range of members in a sorted set, by score, with scores ordered from high to low

### [ZREVRANK](https://redis.io/commands/zrevrank/)

Determine the index of a member in a sorted set, with scores ordered from high to low

### [ZSCAN](https://redis.io/commands/zscan/)

Incrementally iterate sorted sets elements and associated scores

### [ZSCORE](https://redis.io/commands/zscore/)

Get the score associated with the given member in a sorted set

### [ZUNIONSTORE](https://redis.io/commands/zunionstore/)

Add multiple sorted sets and store the resulting sorted set in a new key


## generic commands

### [DEL](https://redis.io/commands/del/)

Delete a key

### [DUMP](https://redis.io/commands/dump/)

Return a serialized version of the value stored at the specified key.

### [EXISTS](https://redis.io/commands/exists/)

Determine if a key exists

### [EXPIRE](https://redis.io/commands/expire/)

Set a key's time to live in seconds

### [EXPIREAT](https://redis.io/commands/expireat/)

Set the expiration for a key as a UNIX timestamp

### [KEYS](https://redis.io/commands/keys/)

Find all keys matching the given pattern

### [MOVE](https://redis.io/commands/move/)

Move a key to another database

### [PERSIST](https://redis.io/commands/persist/)

Remove the expiration from a key

### [PEXPIRE](https://redis.io/commands/pexpire/)

Set a key's time to live in milliseconds

### [PEXPIREAT](https://redis.io/commands/pexpireat/)

Set the expiration for a key as a UNIX timestamp specified in milliseconds

### [PTTL](https://redis.io/commands/pttl/)

Get the time to live for a key in milliseconds

### [RANDOMKEY](https://redis.io/commands/randomkey/)

Return a random key from the keyspace

### [RENAME](https://redis.io/commands/rename/)

Rename a key

### [RENAMENX](https://redis.io/commands/renamenx/)

Rename a key, only if the new key does not exist

### [RESTORE](https://redis.io/commands/restore/)

Create a key using the provided serialized value, previously obtained using DUMP.

### [SCAN](https://redis.io/commands/scan/)

Incrementally iterate the keys space

### [SORT](https://redis.io/commands/sort/)

Sort the elements in a list, set or sorted set

### [TTL](https://redis.io/commands/ttl/)

Get the time to live for a key in seconds

### [TYPE](https://redis.io/commands/type/)

Determine the type stored at key

### [UNLINK](https://redis.io/commands/unlink/)

Delete a key asynchronously in another thread. Otherwise it is just as DEL, but non blocking.


## transactions commands

### [DISCARD](https://redis.io/commands/discard/)

Discard all commands issued after MULTI

### [EXEC](https://redis.io/commands/exec/)

Execute all commands issued after MULTI

### [MULTI](https://redis.io/commands/multi/)

Mark the start of a transaction block

### [UNWATCH](https://redis.io/commands/unwatch/)

Forget about all watched keys

### [WATCH](https://redis.io/commands/watch/)

Watch the given keys to determine execution of the MULTI/EXEC block


## connection commands

### [ECHO](https://redis.io/commands/echo/)

Echo the given string

### [PING](https://redis.io/commands/ping/)

Ping the server

### [SELECT](https://redis.io/commands/select/)

Change the selected database for the current connection


## scripting commands

### [EVAL](https://redis.io/commands/eval/)

Execute a Lua script server side

### [EVALSHA](https://redis.io/commands/evalsha/)

Execute a Lua script server side

### [SCRIPT](https://redis.io/commands/script/)

A container for Lua scripts management commands

### [SCRIPT EXISTS](https://redis.io/commands/script-exists/)

Check existence of scripts in the script cache.

### [SCRIPT FLUSH](https://redis.io/commands/script-flush/)

Remove all the scripts from the script cache.

### [SCRIPT HELP](https://redis.io/commands/script-help/)

Show helpful text about the different subcommands

### [SCRIPT LOAD](https://redis.io/commands/script-load/)

Load the specified Lua script into the script cache.


## hash commands

### [HDEL](https://redis.io/commands/hdel/)

Delete one or more hash fields

### [HEXISTS](https://redis.io/commands/hexists/)

Determine if a hash field exists

### [HGET](https://redis.io/commands/hget/)

Get the value of a hash field

### [HGETALL](https://redis.io/commands/hgetall/)

Get all the fields and values in a hash

### [HINCRBY](https://redis.io/commands/hincrby/)

Increment the integer value of a hash field by the given number

### [HINCRBYFLOAT](https://redis.io/commands/hincrbyfloat/)

Increment the float value of a hash field by the given amount

### [HKEYS](https://redis.io/commands/hkeys/)

Get all the fields in a hash

### [HLEN](https://redis.io/commands/hlen/)

Get the number of fields in a hash

### [HMGET](https://redis.io/commands/hmget/)

Get the values of all the given hash fields

### [HMSET](https://redis.io/commands/hmset/)

Set multiple hash fields to multiple values

### [HSCAN](https://redis.io/commands/hscan/)

Incrementally iterate hash fields and associated values

### [HSET](https://redis.io/commands/hset/)

Set the string value of a hash field

### [HSETNX](https://redis.io/commands/hsetnx/)

Set the value of a hash field, only if the field does not exist

### [HSTRLEN](https://redis.io/commands/hstrlen/)

Get the length of the value of a hash field

### [HVALS](https://redis.io/commands/hvals/)

Get all the values in a hash


## hyperloglog commands

### [PFADD](https://redis.io/commands/pfadd/)

Adds the specified elements to the specified HyperLogLog.

### [PFCOUNT](https://redis.io/commands/pfcount/)

Return the approximated cardinality of the set(s) observed by the HyperLogLog at key(s).

### [PFMERGE](https://redis.io/commands/pfmerge/)

Merge N different HyperLogLogs into a single one.


## pubsub commands

### [PSUBSCRIBE](https://redis.io/commands/psubscribe/)

Listen for messages published to channels matching the given patterns

### [PUBLISH](https://redis.io/commands/publish/)

Post a message to a channel

### [PUBSUB](https://redis.io/commands/pubsub/)

A container for Pub/Sub commands

### [PUBSUB CHANNELS](https://redis.io/commands/pubsub-channels/)

List active channels

### [PUBSUB HELP](https://redis.io/commands/pubsub-help/)

Show helpful text about the different subcommands

### [PUBSUB NUMSUB](https://redis.io/commands/pubsub-numsub/)

Get the count of subscribers for channels

### [PUNSUBSCRIBE](https://redis.io/commands/punsubscribe/)

Stop listening for messages posted to channels matching the given patterns

### [SUBSCRIBE](https://redis.io/commands/subscribe/)

Listen for messages published to the given channels

### [UNSUBSCRIBE](https://redis.io/commands/unsubscribe/)

Stop listening for messages posted to the given channels


## set commands

### [SADD](https://redis.io/commands/sadd/)

Add one or more members to a set

### [SCARD](https://redis.io/commands/scard/)

Get the number of members in a set

### [SDIFF](https://redis.io/commands/sdiff/)

Subtract multiple sets

### [SDIFFSTORE](https://redis.io/commands/sdiffstore/)

Subtract multiple sets and store the resulting set in a key

### [SINTER](https://redis.io/commands/sinter/)

Intersect multiple sets

### [SINTERCARD](https://redis.io/commands/sintercard/)

Intersect multiple sets and return the cardinality of the result

### [SINTERSTORE](https://redis.io/commands/sinterstore/)

Intersect multiple sets and store the resulting set in a key

### [SISMEMBER](https://redis.io/commands/sismember/)

Determine if a given value is a member of a set

### [SMEMBERS](https://redis.io/commands/smembers/)

Get all the members in a set

### [SMISMEMBER](https://redis.io/commands/smismember/)

Returns the membership associated with the given elements for a set

### [SMOVE](https://redis.io/commands/smove/)

Move a member from one set to another

### [SPOP](https://redis.io/commands/spop/)

Remove and return one or multiple random members from a set

### [SRANDMEMBER](https://redis.io/commands/srandmember/)

Get one or multiple random members from a set

### [SREM](https://redis.io/commands/srem/)

Remove one or more members from a set

### [SSCAN](https://redis.io/commands/sscan/)

Incrementally iterate Set elements

### [SUNION](https://redis.io/commands/sunion/)

Add multiple sets

### [SUNIONSTORE](https://redis.io/commands/sunionstore/)

Add multiple sets and store the resulting set in a key


## json commands

### [JSON.DEL](https://redis.io/commands/json.del/)

Deletes a value

### [JSON.FORGET](https://redis.io/commands/json.forget/)

Deletes a value

### [JSON.GET](https://redis.io/commands/json.get/)

Gets the value at one or more paths in JSON serialized form

### [JSON.TOGGLE](https://redis.io/commands/json.toggle/)

Toggles a boolean value

### [JSON.CLEAR](https://redis.io/commands/json.clear/)

Clears all values from an array or an object and sets numeric values to `0`

### [JSON.SET](https://redis.io/commands/json.set/)

Sets or updates the JSON value at a path

### [JSON.MGET](https://redis.io/commands/json.mget/)

Returns the values at a path from one or more keys

### [JSON.STRAPPEND](https://redis.io/commands/json.strappend/)

Appends a string to a JSON string value at path

### [JSON.STRLEN](https://redis.io/commands/json.strlen/)

Returns the length of the JSON String at path in key

### [JSON.ARRAPPEND](https://redis.io/commands/json.arrappend/)

Append one or more json values into the array at path after the last element in it.

### [JSON.ARRINDEX](https://redis.io/commands/json.arrindex/)

Returns the index of the first occurrence of a JSON scalar value in the array at path

### [JSON.ARRLEN](https://redis.io/commands/json.arrlen/)

Returns the length of the array at path

### [JSON.OBJLEN](https://redis.io/commands/json.objlen/)

Returns the number of keys of the object at path

### [JSON.TYPE](https://redis.io/commands/json.type/)

Returns the type of the JSON value at path


