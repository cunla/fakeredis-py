-----
Here is a list of all redis [implemented commands](#implemented-commands) and a
list of [unimplemented commands](#unimplemented-commands).

# Implemented Commands
### string
 * [APPEND](https://redis.io/commands/append/)
   Append a value to a key
 * [DECR](https://redis.io/commands/decr/)
   Decrement the integer value of a key by one
 * [DECRBY](https://redis.io/commands/decrby/)
   Decrement the integer value of a key by the given number
 * [GET](https://redis.io/commands/get/)
   Get the value of a key
 * [GETDEL](https://redis.io/commands/getdel/)
   Get the value of a key and delete the key
 * [GETRANGE](https://redis.io/commands/getrange/)
   Get a substring of the string stored at a key
 * [GETSET](https://redis.io/commands/getset/)
   Set the string value of a key and return its old value
 * [INCR](https://redis.io/commands/incr/)
   Increment the integer value of a key by one
 * [INCRBY](https://redis.io/commands/incrby/)
   Increment the integer value of a key by the given amount
 * [INCRBYFLOAT](https://redis.io/commands/incrbyfloat/)
   Increment the float value of a key by the given amount
 * [MGET](https://redis.io/commands/mget/)
   Get the values of all the given keys
 * [MSET](https://redis.io/commands/mset/)
   Set multiple keys to multiple values
 * [MSETNX](https://redis.io/commands/msetnx/)
   Set multiple keys to multiple values, only if none of the keys exist
 * [PSETEX](https://redis.io/commands/psetex/)
   Set the value and expiration in milliseconds of a key
 * [SET](https://redis.io/commands/set/)
   Set the string value of a key
 * [SETEX](https://redis.io/commands/setex/)
   Set the value and expiration of a key
 * [SETNX](https://redis.io/commands/setnx/)
   Set the value of a key, only if the key does not exist
 * [SETRANGE](https://redis.io/commands/setrange/)
   Overwrite part of a string at key starting at the specified offset
 * [STRLEN](https://redis.io/commands/strlen/)
   Get the length of the value stored in a key
 * [SUBSTR](https://redis.io/commands/substr/)
   Get a substring of the string stored at a key

### server
 * [BGSAVE](https://redis.io/commands/bgsave/)
   Asynchronously save the dataset to disk
 * [DBSIZE](https://redis.io/commands/dbsize/)
   Return the number of keys in the selected database
 * [FLUSHALL](https://redis.io/commands/flushall/)
   Remove all keys from all databases
 * [FLUSHDB](https://redis.io/commands/flushdb/)
   Remove all keys from the current database
 * [LASTSAVE](https://redis.io/commands/lastsave/)
   Get the UNIX time stamp of the last successful save to disk
 * [SAVE](https://redis.io/commands/save/)
   Synchronously save the dataset to disk
 * [SWAPDB](https://redis.io/commands/swapdb/)
   Swaps two Redis databases
 * [TIME](https://redis.io/commands/time/)
   Return the current server time

### bitmap
 * [BITCOUNT](https://redis.io/commands/bitcount/)
   Count set bits in a string
 * [GETBIT](https://redis.io/commands/getbit/)
   Returns the bit value at offset in the string value stored at key
 * [SETBIT](https://redis.io/commands/setbit/)
   Sets or clears the bit at offset in the string value stored at key

### list
 * [BLPOP](https://redis.io/commands/blpop/)
   Remove and get the first element in a list, or block until one is available
 * [BRPOP](https://redis.io/commands/brpop/)
   Remove and get the last element in a list, or block until one is available
 * [BRPOPLPUSH](https://redis.io/commands/brpoplpush/)
   Pop an element from a list, push it to another list and return it; or block until one is available
 * [LINDEX](https://redis.io/commands/lindex/)
   Get an element from a list by its index
 * [LINSERT](https://redis.io/commands/linsert/)
   Insert an element before or after another element in a list
 * [LLEN](https://redis.io/commands/llen/)
   Get the length of a list
 * [LMOVE](https://redis.io/commands/lmove/)
   Pop an element from a list, push it to another list and return it
 * [LPOP](https://redis.io/commands/lpop/)
   Remove and get the first elements in a list
 * [LPUSH](https://redis.io/commands/lpush/)
   Prepend one or multiple elements to a list
 * [LPUSHX](https://redis.io/commands/lpushx/)
   Prepend an element to a list, only if the list exists
 * [LRANGE](https://redis.io/commands/lrange/)
   Get a range of elements from a list
 * [LREM](https://redis.io/commands/lrem/)
   Remove elements from a list
 * [LSET](https://redis.io/commands/lset/)
   Set the value of an element in a list by its index
 * [LTRIM](https://redis.io/commands/ltrim/)
   Trim a list to the specified range
 * [RPOP](https://redis.io/commands/rpop/)
   Remove and get the last elements in a list
 * [RPOPLPUSH](https://redis.io/commands/rpoplpush/)
   Remove the last element in a list, prepend it to another list and return it
 * [RPUSH](https://redis.io/commands/rpush/)
   Append one or multiple elements to a list
 * [RPUSHX](https://redis.io/commands/rpushx/)
   Append an element to a list, only if the list exists

### sorted-set
 * [BZPOPMAX](https://redis.io/commands/bzpopmax/)
   Remove and return the member with the highest score from one or more sorted sets, or block until one is available
 * [BZPOPMIN](https://redis.io/commands/bzpopmin/)
   Remove and return the member with the lowest score from one or more sorted sets, or block until one is available
 * [ZADD](https://redis.io/commands/zadd/)
   Add one or more members to a sorted set, or update its score if it already exists
 * [ZCARD](https://redis.io/commands/zcard/)
   Get the number of members in a sorted set
 * [ZCOUNT](https://redis.io/commands/zcount/)
   Count the members in a sorted set with scores within the given values
 * [ZINCRBY](https://redis.io/commands/zincrby/)
   Increment the score of a member in a sorted set
 * [ZINTERSTORE](https://redis.io/commands/zinterstore/)
   Intersect multiple sorted sets and store the resulting sorted set in a new key
 * [ZLEXCOUNT](https://redis.io/commands/zlexcount/)
   Count the number of members in a sorted set between a given lexicographical range
 * [ZMSCORE](https://redis.io/commands/zmscore/)
   Get the score associated with the given members in a sorted set
 * [ZPOPMAX](https://redis.io/commands/zpopmax/)
   Remove and return members with the highest scores in a sorted set
 * [ZPOPMIN](https://redis.io/commands/zpopmin/)
   Remove and return members with the lowest scores in a sorted set
 * [ZRANGE](https://redis.io/commands/zrange/)
   Return a range of members in a sorted set
 * [ZRANGEBYLEX](https://redis.io/commands/zrangebylex/)
   Return a range of members in a sorted set, by lexicographical range
 * [ZRANGEBYSCORE](https://redis.io/commands/zrangebyscore/)
   Return a range of members in a sorted set, by score
 * [ZRANK](https://redis.io/commands/zrank/)
   Determine the index of a member in a sorted set
 * [ZREM](https://redis.io/commands/zrem/)
   Remove one or more members from a sorted set
 * [ZREMRANGEBYLEX](https://redis.io/commands/zremrangebylex/)
   Remove all members in a sorted set between the given lexicographical range
 * [ZREMRANGEBYRANK](https://redis.io/commands/zremrangebyrank/)
   Remove all members in a sorted set within the given indexes
 * [ZREMRANGEBYSCORE](https://redis.io/commands/zremrangebyscore/)
   Remove all members in a sorted set within the given scores
 * [ZREVRANGE](https://redis.io/commands/zrevrange/)
   Return a range of members in a sorted set, by index, with scores ordered from high to low
 * [ZREVRANGEBYLEX](https://redis.io/commands/zrevrangebylex/)
   Return a range of members in a sorted set, by lexicographical range, ordered from higher to lower strings.
 * [ZREVRANGEBYSCORE](https://redis.io/commands/zrevrangebyscore/)
   Return a range of members in a sorted set, by score, with scores ordered from high to low
 * [ZREVRANK](https://redis.io/commands/zrevrank/)
   Determine the index of a member in a sorted set, with scores ordered from high to low
 * [ZSCAN](https://redis.io/commands/zscan/)
   Incrementally iterate sorted sets elements and associated scores
 * [ZSCORE](https://redis.io/commands/zscore/)
   Get the score associated with the given member in a sorted set
 * [ZUNIONSTORE](https://redis.io/commands/zunionstore/)
   Add multiple sorted sets and store the resulting sorted set in a new key

### generic
 * [DEL](https://redis.io/commands/del/)
   Delete a key
 * [DUMP](https://redis.io/commands/dump/)
   Return a serialized version of the value stored at the specified key.
 * [EXISTS](https://redis.io/commands/exists/)
   Determine if a key exists
 * [EXPIRE](https://redis.io/commands/expire/)
   Set a key's time to live in seconds
 * [EXPIREAT](https://redis.io/commands/expireat/)
   Set the expiration for a key as a UNIX timestamp
 * [KEYS](https://redis.io/commands/keys/)
   Find all keys matching the given pattern
 * [MOVE](https://redis.io/commands/move/)
   Move a key to another database
 * [PERSIST](https://redis.io/commands/persist/)
   Remove the expiration from a key
 * [PEXPIRE](https://redis.io/commands/pexpire/)
   Set a key's time to live in milliseconds
 * [PEXPIREAT](https://redis.io/commands/pexpireat/)
   Set the expiration for a key as a UNIX timestamp specified in milliseconds
 * [PTTL](https://redis.io/commands/pttl/)
   Get the time to live for a key in milliseconds
 * [RANDOMKEY](https://redis.io/commands/randomkey/)
   Return a random key from the keyspace
 * [RENAME](https://redis.io/commands/rename/)
   Rename a key
 * [RENAMENX](https://redis.io/commands/renamenx/)
   Rename a key, only if the new key does not exist
 * [RESTORE](https://redis.io/commands/restore/)
   Create a key using the provided serialized value, previously obtained using DUMP.
 * [SCAN](https://redis.io/commands/scan/)
   Incrementally iterate the keys space
 * [SORT](https://redis.io/commands/sort/)
   Sort the elements in a list, set or sorted set
 * [TTL](https://redis.io/commands/ttl/)
   Get the time to live for a key in seconds
 * [TYPE](https://redis.io/commands/type/)
   Determine the type stored at key
 * [UNLINK](https://redis.io/commands/unlink/)
   Delete a key asynchronously in another thread. Otherwise it is just as DEL, but non blocking.

### transactions
 * [DISCARD](https://redis.io/commands/discard/)
   Discard all commands issued after MULTI
 * [EXEC](https://redis.io/commands/exec/)
   Execute all commands issued after MULTI
 * [MULTI](https://redis.io/commands/multi/)
   Mark the start of a transaction block
 * [UNWATCH](https://redis.io/commands/unwatch/)
   Forget about all watched keys
 * [WATCH](https://redis.io/commands/watch/)
   Watch the given keys to determine execution of the MULTI/EXEC block

### connection
 * [ECHO](https://redis.io/commands/echo/)
   Echo the given string
 * [PING](https://redis.io/commands/ping/)
   Ping the server
 * [SELECT](https://redis.io/commands/select/)
   Change the selected database for the current connection

### scripting
 * [EVAL](https://redis.io/commands/eval/)
   Execute a Lua script server side
 * [EVALSHA](https://redis.io/commands/evalsha/)
   Execute a Lua script server side
 * [SCRIPT](https://redis.io/commands/script/)
   A container for Lua scripts management commands
 * [SCRIPT EXISTS](https://redis.io/commands/script-exists/)
   Check existence of scripts in the script cache.
 * [SCRIPT FLUSH](https://redis.io/commands/script-flush/)
   Remove all the scripts from the script cache.
 * [SCRIPT LOAD](https://redis.io/commands/script-load/)
   Load the specified Lua script into the script cache.

### hash
 * [HDEL](https://redis.io/commands/hdel/)
   Delete one or more hash fields
 * [HEXISTS](https://redis.io/commands/hexists/)
   Determine if a hash field exists
 * [HGET](https://redis.io/commands/hget/)
   Get the value of a hash field
 * [HGETALL](https://redis.io/commands/hgetall/)
   Get all the fields and values in a hash
 * [HINCRBY](https://redis.io/commands/hincrby/)
   Increment the integer value of a hash field by the given number
 * [HINCRBYFLOAT](https://redis.io/commands/hincrbyfloat/)
   Increment the float value of a hash field by the given amount
 * [HKEYS](https://redis.io/commands/hkeys/)
   Get all the fields in a hash
 * [HLEN](https://redis.io/commands/hlen/)
   Get the number of fields in a hash
 * [HMGET](https://redis.io/commands/hmget/)
   Get the values of all the given hash fields
 * [HMSET](https://redis.io/commands/hmset/)
   Set multiple hash fields to multiple values
 * [HSCAN](https://redis.io/commands/hscan/)
   Incrementally iterate hash fields and associated values
 * [HSET](https://redis.io/commands/hset/)
   Set the string value of a hash field
 * [HSETNX](https://redis.io/commands/hsetnx/)
   Set the value of a hash field, only if the field does not exist
 * [HSTRLEN](https://redis.io/commands/hstrlen/)
   Get the length of the value of a hash field
 * [HVALS](https://redis.io/commands/hvals/)
   Get all the values in a hash

### hyperloglog
 * [PFADD](https://redis.io/commands/pfadd/)
   Adds the specified elements to the specified HyperLogLog.
 * [PFCOUNT](https://redis.io/commands/pfcount/)
   Return the approximated cardinality of the set(s) observed by the HyperLogLog at key(s).
 * [PFMERGE](https://redis.io/commands/pfmerge/)
   Merge N different HyperLogLogs into a single one.

### pubsub
 * [PSUBSCRIBE](https://redis.io/commands/psubscribe/)
   Listen for messages published to channels matching the given patterns
 * [PUBLISH](https://redis.io/commands/publish/)
   Post a message to a channel
 * [PUNSUBSCRIBE](https://redis.io/commands/punsubscribe/)
   Stop listening for messages posted to channels matching the given patterns
 * [SUBSCRIBE](https://redis.io/commands/subscribe/)
   Listen for messages published to the given channels
 * [UNSUBSCRIBE](https://redis.io/commands/unsubscribe/)
   Stop listening for messages posted to the given channels

### set
 * [SADD](https://redis.io/commands/sadd/)
   Add one or more members to a set
 * [SCARD](https://redis.io/commands/scard/)
   Get the number of members in a set
 * [SDIFF](https://redis.io/commands/sdiff/)
   Subtract multiple sets
 * [SDIFFSTORE](https://redis.io/commands/sdiffstore/)
   Subtract multiple sets and store the resulting set in a key
 * [SINTER](https://redis.io/commands/sinter/)
   Intersect multiple sets
 * [SINTERCARD](https://redis.io/commands/sintercard/)
   Intersect multiple sets and return the cardinality of the result
 * [SINTERSTORE](https://redis.io/commands/sinterstore/)
   Intersect multiple sets and store the resulting set in a key
 * [SISMEMBER](https://redis.io/commands/sismember/)
   Determine if a given value is a member of a set
 * [SMEMBERS](https://redis.io/commands/smembers/)
   Get all the members in a set
 * [SMISMEMBER](https://redis.io/commands/smismember/)
   Returns the membership associated with the given elements for a set
 * [SMOVE](https://redis.io/commands/smove/)
   Move a member from one set to another
 * [SPOP](https://redis.io/commands/spop/)
   Remove and return one or multiple random members from a set
 * [SRANDMEMBER](https://redis.io/commands/srandmember/)
   Get one or multiple random members from a set
 * [SREM](https://redis.io/commands/srem/)
   Remove one or more members from a set
 * [SSCAN](https://redis.io/commands/sscan/)
   Incrementally iterate Set elements
 * [SUNION](https://redis.io/commands/sunion/)
   Add multiple sets
 * [SUNIONSTORE](https://redis.io/commands/sunionstore/)
   Add multiple sets and store the resulting set in a key

### json
 * [JSON.DEL](https://redis.io/commands/json.del/)
   Deletes a value
 * [JSON.FORGET](https://redis.io/commands/json.forget/)
   Deletes a value
 * [JSON.GET](https://redis.io/commands/json.get/)
   Gets the value at one or more paths in JSON serialized form
 * [JSON.TOGGLE](https://redis.io/commands/json.toggle/)
   Toggles a boolean value
 * [JSON.CLEAR](https://redis.io/commands/json.clear/)
   Clears all values from an array or an object and sets numeric values to `0`
 * [JSON.SET](https://redis.io/commands/json.set/)
   Sets or updates the JSON value at a path
 * [JSON.MGET](https://redis.io/commands/json.mget/)
   Returns the values at a path from one or more keys
 * [JSON.STRLEN](https://redis.io/commands/json.strlen/)
   Returns the length of the JSON String at path in key

# Unimplemented Commands
All the redis commands are implemented in fakeredis with these exceptions:
    
### server
 * [ACL](https://redis.io/commands/acl/)
   A container for Access List Control commands 
 * [ACL CAT](https://redis.io/commands/acl-cat/)
   List the ACL categories or the commands inside a category
 * [ACL DELUSER](https://redis.io/commands/acl-deluser/)
   Remove the specified ACL users and the associated rules
 * [ACL DRYRUN](https://redis.io/commands/acl-dryrun/)
   Returns whether the user can execute the given command without executing the command.
 * [ACL GENPASS](https://redis.io/commands/acl-genpass/)
   Generate a pseudorandom secure password to use for ACL users
 * [ACL GETUSER](https://redis.io/commands/acl-getuser/)
   Get the rules for a specific ACL user
 * [ACL HELP](https://redis.io/commands/acl-help/)
   Show helpful text about the different subcommands
 * [ACL LIST](https://redis.io/commands/acl-list/)
   List the current ACL rules in ACL config file format
 * [ACL LOAD](https://redis.io/commands/acl-load/)
   Reload the ACLs from the configured ACL file
 * [ACL LOG](https://redis.io/commands/acl-log/)
   List latest events denied because of ACLs in place
 * [ACL SAVE](https://redis.io/commands/acl-save/)
   Save the current ACL rules in the configured ACL file
 * [ACL SETUSER](https://redis.io/commands/acl-setuser/)
   Modify or create the rules for a specific ACL user
 * [ACL USERS](https://redis.io/commands/acl-users/)
   List the username of all the configured ACL rules
 * [ACL WHOAMI](https://redis.io/commands/acl-whoami/)
   Return the name of the user associated to the current connection
 * [BGREWRITEAOF](https://redis.io/commands/bgrewriteaof/)
   Asynchronously rewrite the append-only file
 * [COMMAND](https://redis.io/commands/command/)
   Get array of Redis command details
 * [COMMAND COUNT](https://redis.io/commands/command-count/)
   Get total number of Redis commands
 * [COMMAND DOCS](https://redis.io/commands/command-docs/)
   Get array of specific Redis command documentation
 * [COMMAND GETKEYS](https://redis.io/commands/command-getkeys/)
   Extract keys given a full Redis command
 * [COMMAND GETKEYSANDFLAGS](https://redis.io/commands/command-getkeysandflags/)
   Extract keys and access flags given a full Redis command
 * [COMMAND HELP](https://redis.io/commands/command-help/)
   Show helpful text about the different subcommands
 * [COMMAND INFO](https://redis.io/commands/command-info/)
   Get array of specific Redis command details, or all when no argument is given.
 * [COMMAND LIST](https://redis.io/commands/command-list/)
   Get an array of Redis command names
 * [CONFIG](https://redis.io/commands/config/)
   A container for server configuration commands
 * [CONFIG GET](https://redis.io/commands/config-get/)
   Get the values of configuration parameters
 * [CONFIG HELP](https://redis.io/commands/config-help/)
   Show helpful text about the different subcommands
 * [CONFIG RESETSTAT](https://redis.io/commands/config-resetstat/)
   Reset the stats returned by INFO
 * [CONFIG REWRITE](https://redis.io/commands/config-rewrite/)
   Rewrite the configuration file with the in memory configuration
 * [CONFIG SET](https://redis.io/commands/config-set/)
   Set configuration parameters to the given values
 * [DEBUG](https://redis.io/commands/debug/)
   A container for debugging commands
 * [FAILOVER](https://redis.io/commands/failover/)
   Start a coordinated failover between this server and one of its replicas.
 * [INFO](https://redis.io/commands/info/)
   Get information and statistics about the server
 * [LATENCY](https://redis.io/commands/latency/)
   A container for latency diagnostics commands
 * [LATENCY DOCTOR](https://redis.io/commands/latency-doctor/)
   Return a human readable latency analysis report.
 * [LATENCY GRAPH](https://redis.io/commands/latency-graph/)
   Return a latency graph for the event.
 * [LATENCY HELP](https://redis.io/commands/latency-help/)
   Show helpful text about the different subcommands.
 * [LATENCY HISTOGRAM](https://redis.io/commands/latency-histogram/)
   Return the cumulative distribution of latencies of a subset of commands or all.
 * [LATENCY HISTORY](https://redis.io/commands/latency-history/)
   Return timestamp-latency samples for the event.
 * [LATENCY LATEST](https://redis.io/commands/latency-latest/)
   Return the latest latency samples for all events.
 * [LATENCY RESET](https://redis.io/commands/latency-reset/)
   Reset latency data for one or more events.
 * [LOLWUT](https://redis.io/commands/lolwut/)
   Display some computer art and the Redis version
 * [MEMORY](https://redis.io/commands/memory/)
   A container for memory diagnostics commands
 * [MEMORY DOCTOR](https://redis.io/commands/memory-doctor/)
   Outputs memory problems report
 * [MEMORY HELP](https://redis.io/commands/memory-help/)
   Show helpful text about the different subcommands
 * [MEMORY MALLOC-STATS](https://redis.io/commands/memory-malloc-stats/)
   Show allocator internal stats
 * [MEMORY PURGE](https://redis.io/commands/memory-purge/)
   Ask the allocator to release memory
 * [MEMORY STATS](https://redis.io/commands/memory-stats/)
   Show memory usage details
 * [MEMORY USAGE](https://redis.io/commands/memory-usage/)
   Estimate the memory usage of a key
 * [MODULE](https://redis.io/commands/module/)
   A container for module commands
 * [MODULE HELP](https://redis.io/commands/module-help/)
   Show helpful text about the different subcommands
 * [MODULE LIST](https://redis.io/commands/module-list/)
   List all modules loaded by the server
 * [MODULE LOAD](https://redis.io/commands/module-load/)
   Load a module
 * [MODULE LOADEX](https://redis.io/commands/module-loadex/)
   Load a module with extended parameters
 * [MODULE UNLOAD](https://redis.io/commands/module-unload/)
   Unload a module
 * [MONITOR](https://redis.io/commands/monitor/)
   Listen for all requests received by the server in real time
 * [PSYNC](https://redis.io/commands/psync/)
   Internal command used for replication
 * [REPLCONF](https://redis.io/commands/replconf/)
   An internal command for configuring the replication stream
 * [REPLICAOF](https://redis.io/commands/replicaof/)
   Make the server a replica of another instance, or promote it as master.
 * [RESTORE-ASKING](https://redis.io/commands/restore-asking/)
   An internal command for migrating keys in a cluster
 * [ROLE](https://redis.io/commands/role/)
   Return the role of the instance in the context of replication
 * [SHUTDOWN](https://redis.io/commands/shutdown/)
   Synchronously save the dataset to disk and then shut down the server
 * [SLAVEOF](https://redis.io/commands/slaveof/)
   Make the server a replica of another instance, or promote it as master.
 * [SLOWLOG](https://redis.io/commands/slowlog/)
   A container for slow log commands
 * [SLOWLOG GET](https://redis.io/commands/slowlog-get/)
   Get the slow log's entries
 * [SLOWLOG HELP](https://redis.io/commands/slowlog-help/)
   Show helpful text about the different subcommands
 * [SLOWLOG LEN](https://redis.io/commands/slowlog-len/)
   Get the slow log's length
 * [SLOWLOG RESET](https://redis.io/commands/slowlog-reset/)
   Clear all entries from the slow log
 * [SYNC](https://redis.io/commands/sync/)
   Internal command used for replication

### cluster
 * [ASKING](https://redis.io/commands/asking/)
   Sent by cluster clients after an -ASK redirect
 * [CLUSTER](https://redis.io/commands/cluster/)
   A container for cluster commands
 * [CLUSTER ADDSLOTS](https://redis.io/commands/cluster-addslots/)
   Assign new hash slots to receiving node
 * [CLUSTER ADDSLOTSRANGE](https://redis.io/commands/cluster-addslotsrange/)
   Assign new hash slots to receiving node
 * [CLUSTER BUMPEPOCH](https://redis.io/commands/cluster-bumpepoch/)
   Advance the cluster config epoch
 * [CLUSTER COUNT-FAILURE-REPORTS](https://redis.io/commands/cluster-count-failure-reports/)
   Return the number of failure reports active for a given node
 * [CLUSTER COUNTKEYSINSLOT](https://redis.io/commands/cluster-countkeysinslot/)
   Return the number of local keys in the specified hash slot
 * [CLUSTER DELSLOTS](https://redis.io/commands/cluster-delslots/)
   Set hash slots as unbound in receiving node
 * [CLUSTER DELSLOTSRANGE](https://redis.io/commands/cluster-delslotsrange/)
   Set hash slots as unbound in receiving node
 * [CLUSTER FAILOVER](https://redis.io/commands/cluster-failover/)
   Forces a replica to perform a manual failover of its master.
 * [CLUSTER FLUSHSLOTS](https://redis.io/commands/cluster-flushslots/)
   Delete a node's own slots information
 * [CLUSTER FORGET](https://redis.io/commands/cluster-forget/)
   Remove a node from the nodes table
 * [CLUSTER GETKEYSINSLOT](https://redis.io/commands/cluster-getkeysinslot/)
   Return local key names in the specified hash slot
 * [CLUSTER HELP](https://redis.io/commands/cluster-help/)
   Show helpful text about the different subcommands
 * [CLUSTER INFO](https://redis.io/commands/cluster-info/)
   Provides info about Redis Cluster node state
 * [CLUSTER KEYSLOT](https://redis.io/commands/cluster-keyslot/)
   Returns the hash slot of the specified key
 * [CLUSTER LINKS](https://redis.io/commands/cluster-links/)
   Returns a list of all TCP links to and from peer nodes in cluster
 * [CLUSTER MEET](https://redis.io/commands/cluster-meet/)
   Force a node cluster to handshake with another node
 * [CLUSTER MYID](https://redis.io/commands/cluster-myid/)
   Return the node id
 * [CLUSTER NODES](https://redis.io/commands/cluster-nodes/)
   Get Cluster config for the node
 * [CLUSTER REPLICAS](https://redis.io/commands/cluster-replicas/)
   List replica nodes of the specified master node
 * [CLUSTER REPLICATE](https://redis.io/commands/cluster-replicate/)
   Reconfigure a node as a replica of the specified master node
 * [CLUSTER RESET](https://redis.io/commands/cluster-reset/)
   Reset a Redis Cluster node
 * [CLUSTER SAVECONFIG](https://redis.io/commands/cluster-saveconfig/)
   Forces the node to save cluster state on disk
 * [CLUSTER SET-CONFIG-EPOCH](https://redis.io/commands/cluster-set-config-epoch/)
   Set the configuration epoch in a new node
 * [CLUSTER SETSLOT](https://redis.io/commands/cluster-setslot/)
   Bind a hash slot to a specific node
 * [CLUSTER SHARDS](https://redis.io/commands/cluster-shards/)
   Get array of cluster slots to node mappings
 * [CLUSTER SLAVES](https://redis.io/commands/cluster-slaves/)
   List replica nodes of the specified master node
 * [CLUSTER SLOTS](https://redis.io/commands/cluster-slots/)
   Get array of Cluster slot to node mappings
 * [READONLY](https://redis.io/commands/readonly/)
   Enables read queries for a connection to a cluster replica node
 * [READWRITE](https://redis.io/commands/readwrite/)
   Disables read queries for a connection to a cluster replica node

### connection
 * [AUTH](https://redis.io/commands/auth/)
   Authenticate to the server
 * [CLIENT](https://redis.io/commands/client/)
   A container for client connection commands
 * [CLIENT CACHING](https://redis.io/commands/client-caching/)
   Instruct the server about tracking or not keys in the next request
 * [CLIENT GETNAME](https://redis.io/commands/client-getname/)
   Get the current connection name
 * [CLIENT GETREDIR](https://redis.io/commands/client-getredir/)
   Get tracking notifications redirection client ID if any
 * [CLIENT HELP](https://redis.io/commands/client-help/)
   Show helpful text about the different subcommands
 * [CLIENT ID](https://redis.io/commands/client-id/)
   Returns the client ID for the current connection
 * [CLIENT INFO](https://redis.io/commands/client-info/)
   Returns information about the current client connection.
 * [CLIENT KILL](https://redis.io/commands/client-kill/)
   Kill the connection of a client
 * [CLIENT LIST](https://redis.io/commands/client-list/)
   Get the list of client connections
 * [CLIENT NO-EVICT](https://redis.io/commands/client-no-evict/)
   Set client eviction mode for the current connection
 * [CLIENT PAUSE](https://redis.io/commands/client-pause/)
   Stop processing commands from clients for some time
 * [CLIENT REPLY](https://redis.io/commands/client-reply/)
   Instruct the server whether to reply to commands
 * [CLIENT SETNAME](https://redis.io/commands/client-setname/)
   Set the current connection name
 * [CLIENT TRACKING](https://redis.io/commands/client-tracking/)
   Enable or disable server assisted client side caching support
 * [CLIENT TRACKINGINFO](https://redis.io/commands/client-trackinginfo/)
   Return information about server assisted client side caching for the current connection
 * [CLIENT UNBLOCK](https://redis.io/commands/client-unblock/)
   Unblock a client blocked in a blocking command from a different connection
 * [CLIENT UNPAUSE](https://redis.io/commands/client-unpause/)
   Resume processing of clients that were paused
 * [HELLO](https://redis.io/commands/hello/)
   Handshake with Redis
 * [QUIT](https://redis.io/commands/quit/)
   Close the connection
 * [RESET](https://redis.io/commands/reset/)
   Reset the connection

### bitmap
 * [BITFIELD](https://redis.io/commands/bitfield/)
   Perform arbitrary bitfield integer operations on strings
 * [BITFIELD_RO](https://redis.io/commands/bitfield_ro/)
   Perform arbitrary bitfield integer operations on strings. Read-only variant of BITFIELD
 * [BITOP](https://redis.io/commands/bitop/)
   Perform bitwise operations between strings
 * [BITPOS](https://redis.io/commands/bitpos/)
   Find first bit set or clear in a string

### list
 * [BLMOVE](https://redis.io/commands/blmove/)
   Pop an element from a list, push it to another list and return it; or block until one is available
 * [BLMPOP](https://redis.io/commands/blmpop/)
   Pop elements from a list, or block until one is available
 * [LMPOP](https://redis.io/commands/lmpop/)
   Pop elements from a list
 * [LPOS](https://redis.io/commands/lpos/)
   Return the index of matching elements on a list

### sorted-set
 * [BZMPOP](https://redis.io/commands/bzmpop/)
   Remove and return members with scores in a sorted set or block until one is available
 * [ZDIFF](https://redis.io/commands/zdiff/)
   Subtract multiple sorted sets
 * [ZDIFFSTORE](https://redis.io/commands/zdiffstore/)
   Subtract multiple sorted sets and store the resulting sorted set in a new key
 * [ZINTER](https://redis.io/commands/zinter/)
   Intersect multiple sorted sets
 * [ZINTERCARD](https://redis.io/commands/zintercard/)
   Intersect multiple sorted sets and return the cardinality of the result
 * [ZMPOP](https://redis.io/commands/zmpop/)
   Remove and return members with scores in a sorted set
 * [ZRANDMEMBER](https://redis.io/commands/zrandmember/)
   Get one or multiple random elements from a sorted set
 * [ZRANGESTORE](https://redis.io/commands/zrangestore/)
   Store a range of members from sorted set into another key
 * [ZUNION](https://redis.io/commands/zunion/)
   Add multiple sorted sets

### generic
 * [COPY](https://redis.io/commands/copy/)
   Copy a key
 * [EXPIRETIME](https://redis.io/commands/expiretime/)
   Get the expiration Unix timestamp for a key
 * [MIGRATE](https://redis.io/commands/migrate/)
   Atomically transfer a key from a Redis instance to another one.
 * [OBJECT](https://redis.io/commands/object/)
   A container for object introspection commands
 * [OBJECT ENCODING](https://redis.io/commands/object-encoding/)
   Inspect the internal encoding of a Redis object
 * [OBJECT FREQ](https://redis.io/commands/object-freq/)
   Get the logarithmic access frequency counter of a Redis object
 * [OBJECT HELP](https://redis.io/commands/object-help/)
   Show helpful text about the different subcommands
 * [OBJECT IDLETIME](https://redis.io/commands/object-idletime/)
   Get the time since a Redis object was last accessed
 * [OBJECT REFCOUNT](https://redis.io/commands/object-refcount/)
   Get the number of references to the value of the key
 * [PEXPIRETIME](https://redis.io/commands/pexpiretime/)
   Get the expiration Unix timestamp for a key in milliseconds
 * [SORT_RO](https://redis.io/commands/sort_ro/)
   Sort the elements in a list, set or sorted set. Read-only variant of SORT.
 * [TOUCH](https://redis.io/commands/touch/)
   Alters the last access time of a key(s). Returns the number of existing keys specified.
 * [WAIT](https://redis.io/commands/wait/)
   Wait for the synchronous replication of all the write commands sent in the context of the current connection

### scripting
 * [EVALSHA_RO](https://redis.io/commands/evalsha_ro/)
   Execute a read-only Lua script server side
 * [EVAL_RO](https://redis.io/commands/eval_ro/)
   Execute a read-only Lua script server side
 * [FCALL](https://redis.io/commands/fcall/)
   Invoke a function
 * [FCALL_RO](https://redis.io/commands/fcall_ro/)
   Invoke a read-only function
 * [FUNCTION](https://redis.io/commands/function/)
   A container for function commands
 * [FUNCTION DELETE](https://redis.io/commands/function-delete/)
   Delete a function by name
 * [FUNCTION DUMP](https://redis.io/commands/function-dump/)
   Dump all functions into a serialized binary payload
 * [FUNCTION FLUSH](https://redis.io/commands/function-flush/)
   Deleting all functions
 * [FUNCTION HELP](https://redis.io/commands/function-help/)
   Show helpful text about the different subcommands
 * [FUNCTION KILL](https://redis.io/commands/function-kill/)
   Kill the function currently in execution.
 * [FUNCTION LIST](https://redis.io/commands/function-list/)
   List information about all the functions
 * [FUNCTION LOAD](https://redis.io/commands/function-load/)
   Create a function with the given arguments (name, code, description)
 * [FUNCTION RESTORE](https://redis.io/commands/function-restore/)
   Restore all the functions on the given payload
 * [FUNCTION STATS](https://redis.io/commands/function-stats/)
   Return information about the function currently running (name, description, duration)
 * [SCRIPT DEBUG](https://redis.io/commands/script-debug/)
   Set the debug mode for executed scripts.
 * [SCRIPT HELP](https://redis.io/commands/script-help/)
   Show helpful text about the different subcommands
 * [SCRIPT KILL](https://redis.io/commands/script-kill/)
   Kill the script currently in execution.

### geo
 * [GEOADD](https://redis.io/commands/geoadd/)
   Add one or more geospatial items in the geospatial index represented using a sorted set
 * [GEODIST](https://redis.io/commands/geodist/)
   Returns the distance between two members of a geospatial index
 * [GEOHASH](https://redis.io/commands/geohash/)
   Returns members of a geospatial index as standard geohash strings
 * [GEOPOS](https://redis.io/commands/geopos/)
   Returns longitude and latitude of members of a geospatial index
 * [GEORADIUS](https://redis.io/commands/georadius/)
   Query a sorted set representing a geospatial index to fetch members matching a given maximum distance from a point
 * [GEORADIUSBYMEMBER](https://redis.io/commands/georadiusbymember/)
   Query a sorted set representing a geospatial index to fetch members matching a given maximum distance from a member
 * [GEORADIUSBYMEMBER_RO](https://redis.io/commands/georadiusbymember_ro/)
   A read-only variant for GEORADIUSBYMEMBER
 * [GEORADIUS_RO](https://redis.io/commands/georadius_ro/)
   A read-only variant for GEORADIUS
 * [GEOSEARCH](https://redis.io/commands/geosearch/)
   Query a sorted set representing a geospatial index to fetch members inside an area of a box or a circle.
 * [GEOSEARCHSTORE](https://redis.io/commands/geosearchstore/)
   Query a sorted set representing a geospatial index to fetch members inside an area of a box or a circle, and store the result in another key.

### string
 * [GETEX](https://redis.io/commands/getex/)
   Get the value of a key and optionally set its expiration
 * [LCS](https://redis.io/commands/lcs/)
   Find longest common substring

### hash
 * [HRANDFIELD](https://redis.io/commands/hrandfield/)
   Get one or multiple random fields from a hash

### hyperloglog
 * [PFDEBUG](https://redis.io/commands/pfdebug/)
   Internal commands for debugging HyperLogLog values
 * [PFSELFTEST](https://redis.io/commands/pfselftest/)
   An internal command for testing HyperLogLog values

### pubsub
 * [PUBSUB](https://redis.io/commands/pubsub/)
   A container for Pub/Sub commands
 * [PUBSUB CHANNELS](https://redis.io/commands/pubsub-channels/)
   List active channels
 * [PUBSUB HELP](https://redis.io/commands/pubsub-help/)
   Show helpful text about the different subcommands
 * [PUBSUB NUMPAT](https://redis.io/commands/pubsub-numpat/)
   Get the count of unique patterns pattern subscriptions
 * [PUBSUB NUMSUB](https://redis.io/commands/pubsub-numsub/)
   Get the count of subscribers for channels
 * [PUBSUB SHARDCHANNELS](https://redis.io/commands/pubsub-shardchannels/)
   List active shard channels
 * [PUBSUB SHARDNUMSUB](https://redis.io/commands/pubsub-shardnumsub/)
   Get the count of subscribers for shard channels
 * [SPUBLISH](https://redis.io/commands/spublish/)
   Post a message to a shard channel
 * [SSUBSCRIBE](https://redis.io/commands/ssubscribe/)
   Listen for messages published to the given shard channels
 * [SUNSUBSCRIBE](https://redis.io/commands/sunsubscribe/)
   Stop listening for messages posted to the given shard channels

### stream
 * [XACK](https://redis.io/commands/xack/)
   Marks a pending message as correctly processed, effectively removing it from the pending entries list of the consumer group. Return value of the command is the number of messages successfully acknowledged, that is, the IDs we were actually able to resolve in the PEL.
 * [XADD](https://redis.io/commands/xadd/)
   Appends a new entry to a stream
 * [XAUTOCLAIM](https://redis.io/commands/xautoclaim/)
   Changes (or acquires) ownership of messages in a consumer group, as if the messages were delivered to the specified consumer.
 * [XCLAIM](https://redis.io/commands/xclaim/)
   Changes (or acquires) ownership of a message in a consumer group, as if the message was delivered to the specified consumer.
 * [XDEL](https://redis.io/commands/xdel/)
   Removes the specified entries from the stream. Returns the number of items actually deleted, that may be different from the number of IDs passed in case certain IDs do not exist.
 * [XGROUP](https://redis.io/commands/xgroup/)
   A container for consumer groups commands
 * [XGROUP CREATE](https://redis.io/commands/xgroup-create/)
   Create a consumer group.
 * [XGROUP CREATECONSUMER](https://redis.io/commands/xgroup-createconsumer/)
   Create a consumer in a consumer group.
 * [XGROUP DELCONSUMER](https://redis.io/commands/xgroup-delconsumer/)
   Delete a consumer from a consumer group.
 * [XGROUP DESTROY](https://redis.io/commands/xgroup-destroy/)
   Destroy a consumer group.
 * [XGROUP HELP](https://redis.io/commands/xgroup-help/)
   Show helpful text about the different subcommands
 * [XGROUP SETID](https://redis.io/commands/xgroup-setid/)
   Set a consumer group to an arbitrary last delivered ID value.
 * [XINFO](https://redis.io/commands/xinfo/)
   A container for stream introspection commands
 * [XINFO CONSUMERS](https://redis.io/commands/xinfo-consumers/)
   List the consumers in a consumer group
 * [XINFO GROUPS](https://redis.io/commands/xinfo-groups/)
   List the consumer groups of a stream
 * [XINFO HELP](https://redis.io/commands/xinfo-help/)
   Show helpful text about the different subcommands
 * [XINFO STREAM](https://redis.io/commands/xinfo-stream/)
   Get information about a stream
 * [XLEN](https://redis.io/commands/xlen/)
   Return the number of entries in a stream
 * [XPENDING](https://redis.io/commands/xpending/)
   Return information and entries from a stream consumer group pending entries list, that are messages fetched but never acknowledged.
 * [XRANGE](https://redis.io/commands/xrange/)
   Return a range of elements in a stream, with IDs matching the specified IDs interval
 * [XREAD](https://redis.io/commands/xread/)
   Return never seen elements in multiple streams, with IDs greater than the ones reported by the caller for each stream. Can block.
 * [XREADGROUP](https://redis.io/commands/xreadgroup/)
   Return new entries from a stream using a consumer group, or access the history of the pending entries for a given consumer. Can block.
 * [XREVRANGE](https://redis.io/commands/xrevrange/)
   Return a range of elements in a stream, with IDs matching the specified IDs interval, in reverse order (from greater to smaller IDs) compared to XRANGE
 * [XSETID](https://redis.io/commands/xsetid/)
   An internal command for replicating stream values
 * [XTRIM](https://redis.io/commands/xtrim/)
   Trims the stream to (approximately if '~' is passed) a certain size

### json
 * [JSON.NUMINCRBY](https://redis.io/commands/json.numincrby/)
   Increments the numeric value at path by a value
 * [JSON.NUMMULTBY](https://redis.io/commands/json.nummultby/)
   Multiplies the numeric value at path by a value
 * [JSON.STRAPPEND](https://redis.io/commands/json.strappend/)
   Appends a string to a JSON string value at path
 * [JSON.ARRAPPEND](https://redis.io/commands/json.arrappend/)
   Append one or more json values into the array at path after the last element in it.
 * [JSON.ARRINDEX](https://redis.io/commands/json.arrindex/)
   Returns the index of the first occurrence of a JSON scalar value in the array at path
 * [JSON.ARRINSERT](https://redis.io/commands/json.arrinsert/)
   Inserts the JSON scalar(s) value at the specified index in the array at path
 * [JSON.ARRLEN](https://redis.io/commands/json.arrlen/)
   Returns the length of the array at path
 * [JSON.ARRPOP](https://redis.io/commands/json.arrpop/)
   Removes and returns the element at the specified index in the array at path
 * [JSON.ARRTRIM](https://redis.io/commands/json.arrtrim/)
   Trims the array at path to contain only the specified inclusive range of indices from start to stop
 * [JSON.OBJKEYS](https://redis.io/commands/json.objkeys/)
   Returns the JSON keys of the object at path
 * [JSON.OBJLEN](https://redis.io/commands/json.objlen/)
   Returns the number of keys of the object at path
 * [JSON.TYPE](https://redis.io/commands/json.type/)
   Returns the type of the JSON value at path
 * [JSON.RESP](https://redis.io/commands/json.resp/)
   Returns the JSON value at path in Redis Serialization Protocol (RESP)
 * [JSON.DEBUG](https://redis.io/commands/json.debug/)
   Debugging container command
 * [JSON.DEBUG HELP](https://redis.io/commands/json.debug-help/)
   Shows helpful information
 * [JSON.DEBUG MEMORY](https://redis.io/commands/json.debug-memory/)
   Reports the size in bytes of a key

### graph
 * [GRAPH.QUERY](https://redis.io/commands/graph.query/)
   Executes the given query against a specified graph
 * [GRAPH.RO_QUERY](https://redis.io/commands/graph.ro_query/)
   Executes a given read only query against a specified graph
 * [GRAPH.DELETE](https://redis.io/commands/graph.delete/)
   Completely removes the graph and all of its entities
 * [GRAPH.EXPLAIN](https://redis.io/commands/graph.explain/)
   Returns a query execution plan without running the query
 * [GRAPH.PROFILE](https://redis.io/commands/graph.profile/)
   Executes a query and returns an execution plan augmented with metrics for each operation's execution
 * [GRAPH.SLOWLOG](https://redis.io/commands/graph.slowlog/)
   Returns a list containing up to 10 of the slowest queries issued against the given graph
 * [GRAPH.CONFIG GET](https://redis.io/commands/graph.config-get/)
   Retrieves a RedisGraph configuration
 * [GRAPH.CONFIG SET](https://redis.io/commands/graph.config-set/)
   Updates a RedisGraph configuration
 * [GRAPH.LIST](https://redis.io/commands/graph.list/)
   Lists all graph keys in the keyspace

### timeseries
 * [TS.CREATE](https://redis.io/commands/ts.create/)
   Create a new time series
 * [TS.DEL](https://redis.io/commands/ts.del/)
   Delete all samples between two timestamps for a given time series
 * [TS.ALTER](https://redis.io/commands/ts.alter/)
   Update the retention, chunk size, duplicate policy, and labels of an existing time series
 * [TS.ADD](https://redis.io/commands/ts.add/)
   Append a sample to a time series
 * [TS.MADD](https://redis.io/commands/ts.madd/)
   Append new samples to one or more time series
 * [TS.INCRBY](https://redis.io/commands/ts.incrby/)
   Increase the value of the sample with the maximal existing timestamp, or create a new sample with a value equal to the value of the sample with the maximal existing timestamp with a given increment
 * [TS.DECRBY](https://redis.io/commands/ts.decrby/)
   Decrease the value of the sample with the maximal existing timestamp, or create a new sample with a value equal to the value of the sample with the maximal existing timestamp with a given decrement
 * [TS.CREATERULE](https://redis.io/commands/ts.createrule/)
   Create a compaction rule
 * [TS.DELETERULE](https://redis.io/commands/ts.deleterule/)
   Delete a compaction rule
 * [TS.RANGE](https://redis.io/commands/ts.range/)
   Query a range in forward direction
 * [TS.REVRANGE](https://redis.io/commands/ts.revrange/)
   Query a range in reverse direction
 * [TS.MRANGE](https://redis.io/commands/ts.mrange/)
   Query a range across multiple time series by filters in forward direction
 * [TS.MREVRANGE](https://redis.io/commands/ts.mrevrange/)
   Query a range across multiple time-series by filters in reverse direction
 * [TS.GET](https://redis.io/commands/ts.get/)
   Get the last sample
 * [TS.MGET](https://redis.io/commands/ts.mget/)
   Get the last samples matching a specific filter
 * [TS.INFO](https://redis.io/commands/ts.info/)
   Returns information and statistics for a time series
 * [TS.QUERYINDEX](https://redis.io/commands/ts.queryindex/)
   Get all time series keys matching a filter list

### search
 * [FT.CREATE](https://redis.io/commands/ft.create/)
   Creates an index with the given spec
 * [FT.INFO](https://redis.io/commands/ft.info/)
   Returns information and statistics on the index
 * [FT.EXPLAIN](https://redis.io/commands/ft.explain/)
   Returns the execution plan for a complex query
 * [FT.EXPLAINCLI](https://redis.io/commands/ft.explaincli/)
   Returns the execution plan for a complex query
 * [FT.ALTER](https://redis.io/commands/ft.alter/)
   Adds a new field to the index
 * [FT.DROPINDEX](https://redis.io/commands/ft.dropindex/)
   Deletes the index
 * [FT.ALIASADD](https://redis.io/commands/ft.aliasadd/)
   Adds an alias to the index
 * [FT.ALIASUPDATE](https://redis.io/commands/ft.aliasupdate/)
   Adds or updates an alias to the index
 * [FT.ALIASDEL](https://redis.io/commands/ft.aliasdel/)
   Deletes an alias from the index
 * [FT.TAGVALS](https://redis.io/commands/ft.tagvals/)
   Returns the distinct tags indexed in a Tag field
 * [FT.SYNUPDATE](https://redis.io/commands/ft.synupdate/)
   Creates or updates a synonym group with additional terms
 * [FT.SYNDUMP](https://redis.io/commands/ft.syndump/)
   Dumps the contents of a synonym group
 * [FT.SPELLCHECK](https://redis.io/commands/ft.spellcheck/)
   Performs spelling correction on a query, returning suggestions for misspelled terms
 * [FT.DICTADD](https://redis.io/commands/ft.dictadd/)
   Adds terms to a dictionary
 * [FT.DICTDEL](https://redis.io/commands/ft.dictdel/)
   Deletes terms from a dictionary
 * [FT.DICTDUMP](https://redis.io/commands/ft.dictdump/)
   Dumps all terms in the given dictionary
 * [FT._LIST](https://redis.io/commands/ft._list/)
   Returns a list of all existing indexes
 * [FT.CONFIG SET](https://redis.io/commands/ft.config-set/)
   Sets runtime configuration options
 * [FT.CONFIG GET](https://redis.io/commands/ft.config-get/)
   Retrieves runtime configuration options
 * [FT.CONFIG HELP](https://redis.io/commands/ft.config-help/)
   Help description of runtime configuration options
 * [FT.SEARCH](https://redis.io/commands/ft.search/)
   Searches the index with a textual query, returning either documents or just ids
 * [FT.AGGREGATE](https://redis.io/commands/ft.aggregate/)
   Adds terms to a dictionary
 * [FT.PROFILE](https://redis.io/commands/ft.profile/)
   Performs a `FT.SEARCH` or `FT.AGGREGATE` command and collects performance information
 * [FT.CURSOR READ](https://redis.io/commands/ft.cursor-read/)
   Reads from a cursor
 * [FT.CURSOR DEL](https://redis.io/commands/ft.cursor-del/)
   Deletes a cursor

### suggestion
 * [FT.SUGADD](https://redis.io/commands/ft.sugadd/)
   Adds a suggestion string to an auto-complete suggestion dictionary
 * [FT.SUGGET](https://redis.io/commands/ft.sugget/)
   Gets completion suggestions for a prefix
 * [FT.SUGDEL](https://redis.io/commands/ft.sugdel/)
   Deletes a string from a suggestion index
 * [FT.SUGLEN](https://redis.io/commands/ft.suglen/)
   Gets the size of an auto-complete suggestion dictionary

### bf
 * [BF.RESERVE](https://redis.io/commands/bf.reserve/)
   Creates a new Bloom Filter
 * [BF.ADD](https://redis.io/commands/bf.add/)
   Adds an item to a Bloom Filter
 * [BF.MADD](https://redis.io/commands/bf.madd/)
   Adds one or more items to a Bloom Filter. A filter will be created if it does not exist
 * [BF.INSERT](https://redis.io/commands/bf.insert/)
   Adds one or more items to a Bloom Filter. A filter will be created if it does not exist
 * [BF.EXISTS](https://redis.io/commands/bf.exists/)
   Checks whether an item exists in a Bloom Filter
 * [BF.MEXISTS](https://redis.io/commands/bf.mexists/)
   Checks whether one or more items exist in a Bloom Filter
 * [BF.SCANDUMP](https://redis.io/commands/bf.scandump/)
   Begins an incremental save of the bloom filter
 * [BF.LOADCHUNK](https://redis.io/commands/bf.loadchunk/)
   Restores a filter previously saved using SCANDUMP
 * [BF.INFO](https://redis.io/commands/bf.info/)
   Returns information about a Bloom Filter

### cf
 * [CF.RESERVE](https://redis.io/commands/cf.reserve/)
   Creates a new Cuckoo Filter
 * [CF.ADD](https://redis.io/commands/cf.add/)
   Adds an item to a Cuckoo Filter
 * [CF.ADDNX](https://redis.io/commands/cf.addnx/)
   Adds an item to a Cuckoo Filter if the item did not exist previously.
 * [CF.INSERT](https://redis.io/commands/cf.insert/)
   Adds one or more items to a Cuckoo Filter. A filter will be created if it does not exist
 * [CF.INSERTNX](https://redis.io/commands/cf.insertnx/)
   Adds one or more items to a Cuckoo Filter if the items did not exist previously. A filter will be created if it does not exist
 * [CF.EXISTS](https://redis.io/commands/cf.exists/)
   Checks whether one or more items exist in a Cuckoo Filter
 * [CF.MEXISTS](https://redis.io/commands/cf.mexists/)
   Checks whether one or more items exist in a Cuckoo Filter
 * [CF.DEL](https://redis.io/commands/cf.del/)
   Deletes an item from a Cuckoo Filter
 * [CF.COUNT](https://redis.io/commands/cf.count/)
   Return the number of times an item might be in a Cuckoo Filter
 * [CF.SCANDUMP](https://redis.io/commands/cf.scandump/)
   Begins an incremental save of the bloom filter
 * [CF.LOADCHUNK](https://redis.io/commands/cf.loadchunk/)
   Restores a filter previously saved using SCANDUMP
 * [CF.INFO](https://redis.io/commands/cf.info/)
   Returns information about a Cuckoo Filter

### cms
 * [CMS.INITBYDIM](https://redis.io/commands/cms.initbydim/)
   Initializes a Count-Min Sketch to dimensions specified by user
 * [CMS.INITBYPROB](https://redis.io/commands/cms.initbyprob/)
   Initializes a Count-Min Sketch to accommodate requested tolerances.
 * [CMS.INCRBY](https://redis.io/commands/cms.incrby/)
   Increases the count of one or more items by increment
 * [CMS.QUERY](https://redis.io/commands/cms.query/)
   Returns the count for one or more items in a sketch
 * [CMS.MERGE](https://redis.io/commands/cms.merge/)
   Merges several sketches into one sketch
 * [CMS.INFO](https://redis.io/commands/cms.info/)
   Returns information about a sketch

### topk
 * [TOPK.RESERVE](https://redis.io/commands/topk.reserve/)
   Initializes a TopK with specified parameters
 * [TOPK.ADD](https://redis.io/commands/topk.add/)
   Increases the count of one or more items by increment
 * [TOPK.INCRBY](https://redis.io/commands/topk.incrby/)
   Increases the count of one or more items by increment
 * [TOPK.QUERY](https://redis.io/commands/topk.query/)
   Checks whether one or more items are in a sketch
 * [TOPK.COUNT](https://redis.io/commands/topk.count/)
   Return the count for one or more items are in a sketch
 * [TOPK.LIST](https://redis.io/commands/topk.list/)
   Return full list of items in Top K list
 * [TOPK.INFO](https://redis.io/commands/topk.info/)
   Returns information about a sketch

### tdigest
 * [TDIGEST.CREATE](https://redis.io/commands/tdigest.create/)
   Allocates memory and initializes a new t-digest sketch
 * [TDIGEST.RESET](https://redis.io/commands/tdigest.reset/)
   Resets a t-digest sketch: empty the sketch and re-initializes it.
 * [TDIGEST.ADD](https://redis.io/commands/tdigest.add/)
   Adds one or more observations to a t-digest sketch
 * [TDIGEST.MERGE](https://redis.io/commands/tdigest.merge/)
   Merges multiple t-digest sketches into a single sketch
 * [TDIGEST.MIN](https://redis.io/commands/tdigest.min/)
   Returns the minimum observation value from a t-digest sketch
 * [TDIGEST.MAX](https://redis.io/commands/tdigest.max/)
   Returns the maximum observation value from a t-digest sketch
 * [TDIGEST.QUANTILE](https://redis.io/commands/tdigest.quantile/)
   Returns, for each input fraction, an estimation of the value (floating point) that is smaller than the given fraction of observations
 * [TDIGEST.CDF](https://redis.io/commands/tdigest.cdf/)
   Returns, for each input value, an estimation of the fraction (floating-point) of (observations smaller than the given value + half the observations equal to the given value)
 * [TDIGEST.TRIMMED_MEAN](https://redis.io/commands/tdigest.trimmed_mean/)
   Returns an estimation of the mean value from the sketch, excluding observation values outside the low and high cutoff quantiles
 * [TDIGEST.RANK](https://redis.io/commands/tdigest.rank/)
   Returns, for each input value (floating-point), the estimated rank of the value (the number of observations in the sketch that are smaller than the value + half the number of observations that are equal to the value)
 * [TDIGEST.REVRANK](https://redis.io/commands/tdigest.revrank/)
   Returns, for each input value (floating-point), the estimated reverse rank of the value (the number of observations in the sketch that are larger than the value + half the number of observations that are equal to the value)
 * [TDIGEST.BYRANK](https://redis.io/commands/tdigest.byrank/)
   Returns, for each input rank, an estimation of the value (floating-point) with that rank
 * [TDIGEST.BYREVRANK](https://redis.io/commands/tdigest.byrevrank/)
   Returns, for each input reverse rank, an estimation of the value (floating-point) with that reverse rank
 * [TDIGEST.INFO](https://redis.io/commands/tdigest.info/)
   Returns information and statistics about a t-digest sketch

