# Redis commands

## server commands

### [BGSAVE](https://redis.io/commands/bgsave/)

Asynchronously saves the database(s) to disk.

### [DBSIZE](https://redis.io/commands/dbsize/)

Returns the number of keys in the database.

### [FLUSHALL](https://redis.io/commands/flushall/)

Removes all keys from all databases.

### [FLUSHDB](https://redis.io/commands/flushdb/)

Remove all keys from the current database.

### [LASTSAVE](https://redis.io/commands/lastsave/)

Returns the Unix timestamp of the last successful save to disk.

### [SAVE](https://redis.io/commands/save/)

Synchronously saves the database(s) to disk.

### [SWAPDB](https://redis.io/commands/swapdb/)

Swaps two Redis databases.

### [TIME](https://redis.io/commands/time/)

Returns the server time.


### Unsupported server commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [ACL](https://redis.io/commands/acl/) <small>(not implemented)</small>

A container for Access List Control commands.

#### [ACL CAT](https://redis.io/commands/acl-cat/) <small>(not implemented)</small>

Lists the ACL categories, or the commands inside a category.

#### [ACL DELUSER](https://redis.io/commands/acl-deluser/) <small>(not implemented)</small>

Deletes ACL users, and terminates their connections.

#### [ACL DRYRUN](https://redis.io/commands/acl-dryrun/) <small>(not implemented)</small>

Simulates the execution of a command by a user, without executing the command.

#### [ACL GENPASS](https://redis.io/commands/acl-genpass/) <small>(not implemented)</small>

Generates a pseudorandom, secure password that can be used to identify ACL users.

#### [ACL GETUSER](https://redis.io/commands/acl-getuser/) <small>(not implemented)</small>

Lists the ACL rules of a user.

#### [ACL HELP](https://redis.io/commands/acl-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [ACL LIST](https://redis.io/commands/acl-list/) <small>(not implemented)</small>

Dumps the effective rules in ACL file format.

#### [ACL LOAD](https://redis.io/commands/acl-load/) <small>(not implemented)</small>

Reloads the rules from the configured ACL file.

#### [ACL LOG](https://redis.io/commands/acl-log/) <small>(not implemented)</small>

Lists recent security events generated due to ACL rules.

#### [ACL SAVE](https://redis.io/commands/acl-save/) <small>(not implemented)</small>

Saves the effective ACL rules in the configured ACL file.

#### [ACL SETUSER](https://redis.io/commands/acl-setuser/) <small>(not implemented)</small>

Creates and modifies an ACL user and its rules.

#### [ACL USERS](https://redis.io/commands/acl-users/) <small>(not implemented)</small>

Lists all ACL users.

#### [ACL WHOAMI](https://redis.io/commands/acl-whoami/) <small>(not implemented)</small>

Returns the authenticated username of the current connection.

#### [BGREWRITEAOF](https://redis.io/commands/bgrewriteaof/) <small>(not implemented)</small>

Asynchronously rewrites the append-only file to disk.

#### [COMMAND](https://redis.io/commands/command/) <small>(not implemented)</small>

Returns detailed information about all commands.

#### [COMMAND COUNT](https://redis.io/commands/command-count/) <small>(not implemented)</small>

Returns a count of commands.

#### [COMMAND DOCS](https://redis.io/commands/command-docs/) <small>(not implemented)</small>

Returns documentary information about one, multiple or all commands.

#### [COMMAND GETKEYS](https://redis.io/commands/command-getkeys/) <small>(not implemented)</small>

Extracts the key names from an arbitrary command.

#### [COMMAND GETKEYSANDFLAGS](https://redis.io/commands/command-getkeysandflags/) <small>(not implemented)</small>

Extracts the key names and access flags for an arbitrary command.

#### [COMMAND HELP](https://redis.io/commands/command-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [COMMAND INFO](https://redis.io/commands/command-info/) <small>(not implemented)</small>

Returns information about one, multiple or all commands.

#### [COMMAND LIST](https://redis.io/commands/command-list/) <small>(not implemented)</small>

Returns a list of command names.

#### [CONFIG](https://redis.io/commands/config/) <small>(not implemented)</small>

A container for server configuration commands.

#### [CONFIG GET](https://redis.io/commands/config-get/) <small>(not implemented)</small>

Returns the effective values of configuration parameters.

#### [CONFIG HELP](https://redis.io/commands/config-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [CONFIG RESETSTAT](https://redis.io/commands/config-resetstat/) <small>(not implemented)</small>

Resets the server's statistics.

#### [CONFIG REWRITE](https://redis.io/commands/config-rewrite/) <small>(not implemented)</small>

Persists the effective configuration to file.

#### [CONFIG SET](https://redis.io/commands/config-set/) <small>(not implemented)</small>

Sets configuration parameters in-flight.

#### [DEBUG](https://redis.io/commands/debug/) <small>(not implemented)</small>

A container for debugging commands.

#### [FAILOVER](https://redis.io/commands/failover/) <small>(not implemented)</small>

Starts a coordinated failover from a server to one of its replicas.

#### [INFO](https://redis.io/commands/info/) <small>(not implemented)</small>

Returns information and statistics about the server.

#### [LATENCY](https://redis.io/commands/latency/) <small>(not implemented)</small>

A container for latency diagnostics commands.

#### [LATENCY DOCTOR](https://redis.io/commands/latency-doctor/) <small>(not implemented)</small>

Returns a human-readable latency analysis report.

#### [LATENCY GRAPH](https://redis.io/commands/latency-graph/) <small>(not implemented)</small>

Returns a latency graph for an event.

#### [LATENCY HELP](https://redis.io/commands/latency-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [LATENCY HISTOGRAM](https://redis.io/commands/latency-histogram/) <small>(not implemented)</small>

Returns the cumulative distribution of latencies of a subset or all commands.

#### [LATENCY HISTORY](https://redis.io/commands/latency-history/) <small>(not implemented)</small>

Returns timestamp-latency samples for an event.

#### [LATENCY LATEST](https://redis.io/commands/latency-latest/) <small>(not implemented)</small>

Returns the latest latency samples for all events.

#### [LATENCY RESET](https://redis.io/commands/latency-reset/) <small>(not implemented)</small>

Resets the latency data for one or more events.

#### [LOLWUT](https://redis.io/commands/lolwut/) <small>(not implemented)</small>

Displays computer art and the Redis version

#### [MEMORY](https://redis.io/commands/memory/) <small>(not implemented)</small>

A container for memory diagnostics commands.

#### [MEMORY DOCTOR](https://redis.io/commands/memory-doctor/) <small>(not implemented)</small>

Outputs a memory problems report.

#### [MEMORY HELP](https://redis.io/commands/memory-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [MEMORY MALLOC-STATS](https://redis.io/commands/memory-malloc-stats/) <small>(not implemented)</small>

Returns the allocator statistics.

#### [MEMORY PURGE](https://redis.io/commands/memory-purge/) <small>(not implemented)</small>

Asks the allocator to release memory.

#### [MEMORY STATS](https://redis.io/commands/memory-stats/) <small>(not implemented)</small>

Returns details about memory usage.

#### [MEMORY USAGE](https://redis.io/commands/memory-usage/) <small>(not implemented)</small>

Estimates the memory usage of a key.

#### [MODULE](https://redis.io/commands/module/) <small>(not implemented)</small>

A container for module commands.

#### [MODULE HELP](https://redis.io/commands/module-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [MODULE LIST](https://redis.io/commands/module-list/) <small>(not implemented)</small>

Returns all loaded modules.

#### [MODULE LOAD](https://redis.io/commands/module-load/) <small>(not implemented)</small>

Loads a module.

#### [MODULE LOADEX](https://redis.io/commands/module-loadex/) <small>(not implemented)</small>

Loads a module using extended parameters.

#### [MODULE UNLOAD](https://redis.io/commands/module-unload/) <small>(not implemented)</small>

Unloads a module.

#### [MONITOR](https://redis.io/commands/monitor/) <small>(not implemented)</small>

Listens for all requests received by the server in real-time.

#### [PSYNC](https://redis.io/commands/psync/) <small>(not implemented)</small>

An internal command used in replication.

#### [REPLCONF](https://redis.io/commands/replconf/) <small>(not implemented)</small>

An internal command for configuring the replication stream.

#### [REPLICAOF](https://redis.io/commands/replicaof/) <small>(not implemented)</small>

Configures a server as replica of another, or promotes it to a master.

#### [RESTORE-ASKING](https://redis.io/commands/restore-asking/) <small>(not implemented)</small>

An internal command for migrating keys in a cluster.

#### [ROLE](https://redis.io/commands/role/) <small>(not implemented)</small>

Returns the replication role.

#### [SHUTDOWN](https://redis.io/commands/shutdown/) <small>(not implemented)</small>

Synchronously saves the database(s) to disk and shuts down the Redis server.

#### [SLAVEOF](https://redis.io/commands/slaveof/) <small>(not implemented)</small>

Sets a Redis server as a replica of another, or promotes it to being a master.

#### [SLOWLOG](https://redis.io/commands/slowlog/) <small>(not implemented)</small>

A container for slow log commands.

#### [SLOWLOG GET](https://redis.io/commands/slowlog-get/) <small>(not implemented)</small>

Returns the slow log's entries.

#### [SLOWLOG HELP](https://redis.io/commands/slowlog-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [SLOWLOG LEN](https://redis.io/commands/slowlog-len/) <small>(not implemented)</small>

Returns the number of entries in the slow log.

#### [SLOWLOG RESET](https://redis.io/commands/slowlog-reset/) <small>(not implemented)</small>

Clears all entries from the slow log.

#### [SYNC](https://redis.io/commands/sync/) <small>(not implemented)</small>

An internal command used in replication.


## string commands

### [APPEND](https://redis.io/commands/append/)

Appends a string to the value of a key. Creates the key if it doesn't exist.

### [DECR](https://redis.io/commands/decr/)

Decrements the integer value of a key by one. Uses 0 as initial value if the key doesn't exist.

### [DECRBY](https://redis.io/commands/decrby/)

Decrements a number from the integer value of a key. Uses 0 as initial value if the key doesn't exist.

### [GET](https://redis.io/commands/get/)

Returns the string value of a key.

### [GETDEL](https://redis.io/commands/getdel/)

Returns the string value of a key after deleting the key.

### [GETEX](https://redis.io/commands/getex/)

Returns the string value of a key after setting its expiration time.

### [GETRANGE](https://redis.io/commands/getrange/)

Returns a substring of the string stored at a key.

### [GETSET](https://redis.io/commands/getset/)

Returns the previous string value of a key after setting it to a new value.

### [INCR](https://redis.io/commands/incr/)

Increments the integer value of a key by one. Uses 0 as initial value if the key doesn't exist.

### [INCRBY](https://redis.io/commands/incrby/)

Increments the integer value of a key by a number. Uses 0 as initial value if the key doesn't exist.

### [INCRBYFLOAT](https://redis.io/commands/incrbyfloat/)

Increment the floating point value of a key by a number. Uses 0 as initial value if the key doesn't exist.

### [LCS](https://redis.io/commands/lcs/)

Finds the longest common substring.

### [MGET](https://redis.io/commands/mget/)

Atomically returns the string values of one or more keys.

### [MSET](https://redis.io/commands/mset/)

Atomically creates or modifies the string values of one or more keys.

### [MSETNX](https://redis.io/commands/msetnx/)

Atomically modifies the string values of one or more keys only when all keys don't exist.

### [PSETEX](https://redis.io/commands/psetex/)

Sets both string value and expiration time in milliseconds of a key. The key is created if it doesn't exist.

### [SET](https://redis.io/commands/set/)

Sets the string value of a key, ignoring its type. The key is created if it doesn't exist.

### [SETEX](https://redis.io/commands/setex/)

Sets the string value and expiration time of a key. Creates the key if it doesn't exist.

### [SETNX](https://redis.io/commands/setnx/)

Set the string value of a key only when the key doesn't exist.

### [SETRANGE](https://redis.io/commands/setrange/)

Overwrites a part of a string value with another by an offset. Creates the key if it doesn't exist.

### [STRLEN](https://redis.io/commands/strlen/)

Returns the length of a string value.

### [SUBSTR](https://redis.io/commands/substr/)

Returns a substring from a string value.




### Unsupported cluster commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [ASKING](https://redis.io/commands/asking/) <small>(not implemented)</small>

Signals that a cluster client is following an -ASK redirect.

#### [CLUSTER](https://redis.io/commands/cluster/) <small>(not implemented)</small>

A container for Redis Cluster commands.

#### [CLUSTER ADDSLOTS](https://redis.io/commands/cluster-addslots/) <small>(not implemented)</small>

Assigns new hash slots to a node.

#### [CLUSTER ADDSLOTSRANGE](https://redis.io/commands/cluster-addslotsrange/) <small>(not implemented)</small>

Assigns new hash slot ranges to a node.

#### [CLUSTER BUMPEPOCH](https://redis.io/commands/cluster-bumpepoch/) <small>(not implemented)</small>

Advances the cluster config epoch.

#### [CLUSTER COUNT-FAILURE-REPORTS](https://redis.io/commands/cluster-count-failure-reports/) <small>(not implemented)</small>

Returns the number of active failure reports active for a node.

#### [CLUSTER COUNTKEYSINSLOT](https://redis.io/commands/cluster-countkeysinslot/) <small>(not implemented)</small>

Returns the number of keys in a hash slot.

#### [CLUSTER DELSLOTS](https://redis.io/commands/cluster-delslots/) <small>(not implemented)</small>

Sets hash slots as unbound for a node.

#### [CLUSTER DELSLOTSRANGE](https://redis.io/commands/cluster-delslotsrange/) <small>(not implemented)</small>

Sets hash slot ranges as unbound for a node.

#### [CLUSTER FAILOVER](https://redis.io/commands/cluster-failover/) <small>(not implemented)</small>

Forces a replica to perform a manual failover of its master.

#### [CLUSTER FLUSHSLOTS](https://redis.io/commands/cluster-flushslots/) <small>(not implemented)</small>

Deletes all slots information from a node.

#### [CLUSTER FORGET](https://redis.io/commands/cluster-forget/) <small>(not implemented)</small>

Removes a node from the nodes table.

#### [CLUSTER GETKEYSINSLOT](https://redis.io/commands/cluster-getkeysinslot/) <small>(not implemented)</small>

Returns the key names in a hash slot.

#### [CLUSTER HELP](https://redis.io/commands/cluster-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [CLUSTER INFO](https://redis.io/commands/cluster-info/) <small>(not implemented)</small>

Returns information about the state of a node.

#### [CLUSTER KEYSLOT](https://redis.io/commands/cluster-keyslot/) <small>(not implemented)</small>

Returns the hash slot for a key.

#### [CLUSTER LINKS](https://redis.io/commands/cluster-links/) <small>(not implemented)</small>

Returns a list of all TCP links to and from peer nodes.

#### [CLUSTER MEET](https://redis.io/commands/cluster-meet/) <small>(not implemented)</small>

Forces a node to handshake with another node.

#### [CLUSTER MYID](https://redis.io/commands/cluster-myid/) <small>(not implemented)</small>

Returns the ID of a node.

#### [CLUSTER MYSHARDID](https://redis.io/commands/cluster-myshardid/) <small>(not implemented)</small>

Returns the shard ID of a node.

#### [CLUSTER NODES](https://redis.io/commands/cluster-nodes/) <small>(not implemented)</small>

Returns the cluster configuration for a node.

#### [CLUSTER REPLICAS](https://redis.io/commands/cluster-replicas/) <small>(not implemented)</small>

Lists the replica nodes of a master node.

#### [CLUSTER REPLICATE](https://redis.io/commands/cluster-replicate/) <small>(not implemented)</small>

Configure a node as replica of a master node.

#### [CLUSTER RESET](https://redis.io/commands/cluster-reset/) <small>(not implemented)</small>

Resets a node.

#### [CLUSTER SAVECONFIG](https://redis.io/commands/cluster-saveconfig/) <small>(not implemented)</small>

Forces a node to save the cluster configuration to disk.

#### [CLUSTER SET-CONFIG-EPOCH](https://redis.io/commands/cluster-set-config-epoch/) <small>(not implemented)</small>

Sets the configuration epoch for a new node.

#### [CLUSTER SETSLOT](https://redis.io/commands/cluster-setslot/) <small>(not implemented)</small>

Binds a hash slot to a node.

#### [CLUSTER SHARDS](https://redis.io/commands/cluster-shards/) <small>(not implemented)</small>

Returns the mapping of cluster slots to shards.

#### [CLUSTER SLAVES](https://redis.io/commands/cluster-slaves/) <small>(not implemented)</small>

Lists the replica nodes of a master node.

#### [CLUSTER SLOTS](https://redis.io/commands/cluster-slots/) <small>(not implemented)</small>

Returns the mapping of cluster slots to nodes.

#### [READONLY](https://redis.io/commands/readonly/) <small>(not implemented)</small>

Enables read-only queries for a connection to a Redis Cluster replica node.

#### [READWRITE](https://redis.io/commands/readwrite/) <small>(not implemented)</small>

Enables read-write queries for a connection to a Reids Cluster replica node.


## connection commands

### [ECHO](https://redis.io/commands/echo/)

Returns the given string.

### [PING](https://redis.io/commands/ping/)

Returns the server's liveliness response.

### [SELECT](https://redis.io/commands/select/)

Changes the selected database.


### Unsupported connection commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [AUTH](https://redis.io/commands/auth/) <small>(not implemented)</small>

Authenticates the connection.

#### [CLIENT](https://redis.io/commands/client/) <small>(not implemented)</small>

A container for client connection commands.

#### [CLIENT CACHING](https://redis.io/commands/client-caching/) <small>(not implemented)</small>

Instructs the server whether to track the keys in the next request.

#### [CLIENT GETNAME](https://redis.io/commands/client-getname/) <small>(not implemented)</small>

Returns the name of the connection.

#### [CLIENT GETREDIR](https://redis.io/commands/client-getredir/) <small>(not implemented)</small>

Returns the client ID to which the connection's tracking notifications are redirected.

#### [CLIENT HELP](https://redis.io/commands/client-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [CLIENT ID](https://redis.io/commands/client-id/) <small>(not implemented)</small>

Returns the unique client ID of the connection.

#### [CLIENT INFO](https://redis.io/commands/client-info/) <small>(not implemented)</small>

Returns information about the connection.

#### [CLIENT KILL](https://redis.io/commands/client-kill/) <small>(not implemented)</small>

Terminates open connections.

#### [CLIENT LIST](https://redis.io/commands/client-list/) <small>(not implemented)</small>

Lists open connections.

#### [CLIENT NO-EVICT](https://redis.io/commands/client-no-evict/) <small>(not implemented)</small>

Sets the client eviction mode of the connection.

#### [CLIENT NO-TOUCH](https://redis.io/commands/client-no-touch/) <small>(not implemented)</small>

Controls whether commands sent by the client affect the LRU/LFU of accessed keys.

#### [CLIENT PAUSE](https://redis.io/commands/client-pause/) <small>(not implemented)</small>

Suspends commands processing.

#### [CLIENT REPLY](https://redis.io/commands/client-reply/) <small>(not implemented)</small>

Instructs the server whether to reply to commands.

#### [CLIENT SETINFO](https://redis.io/commands/client-setinfo/) <small>(not implemented)</small>

Sets information specific to the client or connection.

#### [CLIENT SETNAME](https://redis.io/commands/client-setname/) <small>(not implemented)</small>

Sets the connection name.

#### [CLIENT TRACKING](https://redis.io/commands/client-tracking/) <small>(not implemented)</small>

Controls server-assisted client-side caching for the connection.

#### [CLIENT TRACKINGINFO](https://redis.io/commands/client-trackinginfo/) <small>(not implemented)</small>

Returns information about server-assisted client-side caching for the connection.

#### [CLIENT UNBLOCK](https://redis.io/commands/client-unblock/) <small>(not implemented)</small>

Unblocks a client blocked by a blocking command from a different connection.

#### [CLIENT UNPAUSE](https://redis.io/commands/client-unpause/) <small>(not implemented)</small>

Resumes processing commands from paused clients.

#### [HELLO](https://redis.io/commands/hello/) <small>(not implemented)</small>

Handshakes with the Redis server.

#### [QUIT](https://redis.io/commands/quit/) <small>(not implemented)</small>

Closes the connection.

#### [RESET](https://redis.io/commands/reset/) <small>(not implemented)</small>

Resets the connection.


## bitmap commands

### [BITCOUNT](https://redis.io/commands/bitcount/)

Counts the number of set bits (population counting) in a string.

### [BITOP](https://redis.io/commands/bitop/)

Performs bitwise operations on multiple strings, and stores the result.

### [BITPOS](https://redis.io/commands/bitpos/)

Finds the first set (1) or clear (0) bit in a string.

### [GETBIT](https://redis.io/commands/getbit/)

Returns a bit value by offset.

### [SETBIT](https://redis.io/commands/setbit/)

Sets or clears the bit at offset of the string value. Creates the key if it doesn't exist.


### Unsupported bitmap commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [BITFIELD](https://redis.io/commands/bitfield/) <small>(not implemented)</small>

Performs arbitrary bitfield integer operations on strings.

#### [BITFIELD_RO](https://redis.io/commands/bitfield_ro/) <small>(not implemented)</small>

Performs arbitrary read-only bitfield integer operations on strings.


## list commands

### [BLPOP](https://redis.io/commands/blpop/)

Removes and returns the first element in a list. Blocks until an element is available otherwise. Deletes the list if the last element was popped.

### [BRPOP](https://redis.io/commands/brpop/)

Removes and returns the last element in a list. Blocks until an element is available otherwise. Deletes the list if the last element was popped.

### [BRPOPLPUSH](https://redis.io/commands/brpoplpush/)

Pops an element from a list, pushes it to another list and returns it. Block until an element is available otherwise. Deletes the list if the last element was popped.

### [LINDEX](https://redis.io/commands/lindex/)

Returns an element from a list by its index.

### [LINSERT](https://redis.io/commands/linsert/)

Inserts an element before or after another element in a list.

### [LLEN](https://redis.io/commands/llen/)

Returns the length of a list.

### [LMOVE](https://redis.io/commands/lmove/)

Returns an element after popping it from one list and pushing it to another. Deletes the list if the last element was moved.

### [LPOP](https://redis.io/commands/lpop/)

Returns the first elements in a list after removing it. Deletes the list if the last element was popped.

### [LPUSH](https://redis.io/commands/lpush/)

Prepends one or more elements to a list. Creates the key if it doesn't exist.

### [LPUSHX](https://redis.io/commands/lpushx/)

Prepends one or more elements to a list only when the list exists.

### [LRANGE](https://redis.io/commands/lrange/)

Returns a range of elements from a list.

### [LREM](https://redis.io/commands/lrem/)

Removes elements from a list. Deletes the list if the last element was removed.

### [LSET](https://redis.io/commands/lset/)

Sets the value of an element in a list by its index.

### [LTRIM](https://redis.io/commands/ltrim/)

Removes elements from both ends a list. Deletes the list if all elements were trimmed.

### [RPOP](https://redis.io/commands/rpop/)

Returns and removes the last elements of a list. Deletes the list if the last element was popped.

### [RPOPLPUSH](https://redis.io/commands/rpoplpush/)

Returns the last element of a list after removing and pushing it to another list. Deletes the list if the last element was popped.

### [RPUSH](https://redis.io/commands/rpush/)

Appends one or more elements to a list. Creates the key if it doesn't exist.

### [RPUSHX](https://redis.io/commands/rpushx/)

Appends an element to a list only when the list exists.


### Unsupported list commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [BLMOVE](https://redis.io/commands/blmove/) <small>(not implemented)</small>

Pops an element from a list, pushes it to another list and returns it. Blocks until an element is available otherwise. Deletes the list if the last element was moved.

#### [BLMPOP](https://redis.io/commands/blmpop/) <small>(not implemented)</small>

Pops the first element from one of multiple lists. Blocks until an element is available otherwise. Deletes the list if the last element was popped.

#### [LMPOP](https://redis.io/commands/lmpop/) <small>(not implemented)</small>

Returns multiple elements from a list after removing them. Deletes the list if the last element was popped.

#### [LPOS](https://redis.io/commands/lpos/) <small>(not implemented)</small>

Returns the index of matching elements in a list.


## sorted-set commands

### [BZPOPMAX](https://redis.io/commands/bzpopmax/)

Removes and returns the member with the highest score from one or more sorted sets. Blocks until a member available otherwise.  Deletes the sorted set if the last element was popped.

### [BZPOPMIN](https://redis.io/commands/bzpopmin/)

Removes and returns the member with the lowest score from one or more sorted sets. Blocks until a member is available otherwise. Deletes the sorted set if the last element was popped.

### [ZADD](https://redis.io/commands/zadd/)

Adds one or more members to a sorted set, or updates their scores. Creates the key if it doesn't exist.

### [ZCARD](https://redis.io/commands/zcard/)

Returns the number of members in a sorted set.

### [ZCOUNT](https://redis.io/commands/zcount/)

Returns the count of members in a sorted set that have scores within a range.

### [ZINCRBY](https://redis.io/commands/zincrby/)

Increments the score of a member in a sorted set.

### [ZINTERSTORE](https://redis.io/commands/zinterstore/)

Stores the intersect of multiple sorted sets in a key.

### [ZLEXCOUNT](https://redis.io/commands/zlexcount/)

Returns the number of members in a sorted set within a lexicographical range.

### [ZMSCORE](https://redis.io/commands/zmscore/)

Returns the score of one or more members in a sorted set.

### [ZPOPMAX](https://redis.io/commands/zpopmax/)

Returns the highest-scoring members from a sorted set after removing them. Deletes the sorted set if the last member was popped.

### [ZPOPMIN](https://redis.io/commands/zpopmin/)

Returns the lowest-scoring members from a sorted set after removing them. Deletes the sorted set if the last member was popped.

### [ZRANGE](https://redis.io/commands/zrange/)

Returns members in a sorted set within a range of indexes.

### [ZRANGEBYLEX](https://redis.io/commands/zrangebylex/)

Returns members in a sorted set within a lexicographical range.

### [ZRANGEBYSCORE](https://redis.io/commands/zrangebyscore/)

Returns members in a sorted set within a range of scores.

### [ZRANK](https://redis.io/commands/zrank/)

Returns the index of a member in a sorted set ordered by ascending scores.

### [ZREM](https://redis.io/commands/zrem/)

Removes one or more members from a sorted set. Deletes the sorted set if all members were removed.

### [ZREMRANGEBYLEX](https://redis.io/commands/zremrangebylex/)

Removes members in a sorted set within a lexicographical range. Deletes the sorted set if all members were removed.

### [ZREMRANGEBYRANK](https://redis.io/commands/zremrangebyrank/)

Removes members in a sorted set within a range of indexes. Deletes the sorted set if all members were removed.

### [ZREMRANGEBYSCORE](https://redis.io/commands/zremrangebyscore/)

Removes members in a sorted set within a range of scores. Deletes the sorted set if all members were removed.

### [ZREVRANGE](https://redis.io/commands/zrevrange/)

Returns members in a sorted set within a range of indexes in reverse order.

### [ZREVRANGEBYLEX](https://redis.io/commands/zrevrangebylex/)

Returns members in a sorted set within a lexicographical range in reverse order.

### [ZREVRANGEBYSCORE](https://redis.io/commands/zrevrangebyscore/)

Returns members in a sorted set within a range of scores in reverse order.

### [ZREVRANK](https://redis.io/commands/zrevrank/)

Returns the index of a member in a sorted set ordered by descending scores.

### [ZSCAN](https://redis.io/commands/zscan/)

Iterates over members and scores of a sorted set.

### [ZSCORE](https://redis.io/commands/zscore/)

Returns the score of a member in a sorted set.

### [ZUNIONSTORE](https://redis.io/commands/zunionstore/)

Stores the union of multiple sorted sets in a key.


### Unsupported sorted-set commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [BZMPOP](https://redis.io/commands/bzmpop/) <small>(not implemented)</small>

Removes and returns a member by score from one or more sorted sets. Blocks until a member is available otherwise. Deletes the sorted set if the last element was popped.

#### [ZDIFF](https://redis.io/commands/zdiff/) <small>(not implemented)</small>

Returns the difference between multiple sorted sets.

#### [ZDIFFSTORE](https://redis.io/commands/zdiffstore/) <small>(not implemented)</small>

Stores the difference of multiple sorted sets in a key.

#### [ZINTER](https://redis.io/commands/zinter/) <small>(not implemented)</small>

Returns the intersect of multiple sorted sets.

#### [ZINTERCARD](https://redis.io/commands/zintercard/) <small>(not implemented)</small>

Returns the number of members of the intersect of multiple sorted sets.

#### [ZMPOP](https://redis.io/commands/zmpop/) <small>(not implemented)</small>

Returns the highest- or lowest-scoring members from one or more sorted sets after removing them. Deletes the sorted set if the last member was popped.

#### [ZRANDMEMBER](https://redis.io/commands/zrandmember/) <small>(not implemented)</small>

Returns one or more random members from a sorted set.

#### [ZRANGESTORE](https://redis.io/commands/zrangestore/) <small>(not implemented)</small>

Stores a range of members from sorted set in a key.

#### [ZUNION](https://redis.io/commands/zunion/) <small>(not implemented)</small>

Returns the union of multiple sorted sets.


## generic commands

### [DEL](https://redis.io/commands/del/)

Deletes one or more keys.

### [DUMP](https://redis.io/commands/dump/)

Returns a serialized representation of the value stored at a key.

### [EXISTS](https://redis.io/commands/exists/)

Determines whether one or more keys exist.

### [EXPIRE](https://redis.io/commands/expire/)

Sets the expiration time of a key in seconds.

### [EXPIREAT](https://redis.io/commands/expireat/)

Sets the expiration time of a key to a Unix timestamp.

### [KEYS](https://redis.io/commands/keys/)

Returns all key names that match a pattern.

### [MOVE](https://redis.io/commands/move/)

Moves a key to another database.

### [PERSIST](https://redis.io/commands/persist/)

Removes the expiration time of a key.

### [PEXPIRE](https://redis.io/commands/pexpire/)

Sets the expiration time of a key in milliseconds.

### [PEXPIREAT](https://redis.io/commands/pexpireat/)

Sets the expiration time of a key to a Unix milliseconds timestamp.

### [PTTL](https://redis.io/commands/pttl/)

Returns the expiration time in milliseconds of a key.

### [RANDOMKEY](https://redis.io/commands/randomkey/)

Returns a random key name from the database.

### [RENAME](https://redis.io/commands/rename/)

Renames a key and overwrites the destination.

### [RENAMENX](https://redis.io/commands/renamenx/)

Renames a key only when the target key name doesn't exist.

### [RESTORE](https://redis.io/commands/restore/)

Creates a key from the serialized representation of a value.

### [SCAN](https://redis.io/commands/scan/)

Iterates over the key names in the database.

### [SORT](https://redis.io/commands/sort/)

Sorts the elements in a list, a set, or a sorted set, optionally storing the result.

### [TTL](https://redis.io/commands/ttl/)

Returns the expiration time in seconds of a key.

### [TYPE](https://redis.io/commands/type/)

Determines the type of value stored at a key.

### [UNLINK](https://redis.io/commands/unlink/)

Asynchronously deletes one or more keys.


### Unsupported generic commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [COPY](https://redis.io/commands/copy/) <small>(not implemented)</small>

Copies the value of a key to a new key.

#### [EXPIRETIME](https://redis.io/commands/expiretime/) <small>(not implemented)</small>

Returns the expiration time of a key as a Unix timestamp.

#### [MIGRATE](https://redis.io/commands/migrate/) <small>(not implemented)</small>

Atomically transfers a key from one Redis instance to another.

#### [OBJECT](https://redis.io/commands/object/) <small>(not implemented)</small>

A container for object introspection commands.

#### [OBJECT ENCODING](https://redis.io/commands/object-encoding/) <small>(not implemented)</small>

Returns the internal encoding of a Redis object.

#### [OBJECT FREQ](https://redis.io/commands/object-freq/) <small>(not implemented)</small>

Returns the logarithmic access frequency counter of a Redis object.

#### [OBJECT HELP](https://redis.io/commands/object-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [OBJECT IDLETIME](https://redis.io/commands/object-idletime/) <small>(not implemented)</small>

Returns the time since the last access to a Redis object.

#### [OBJECT REFCOUNT](https://redis.io/commands/object-refcount/) <small>(not implemented)</small>

Returns the reference count of a value of a key.

#### [PEXPIRETIME](https://redis.io/commands/pexpiretime/) <small>(not implemented)</small>

Returns the expiration time of a key as a Unix milliseconds timestamp.

#### [SORT_RO](https://redis.io/commands/sort_ro/) <small>(not implemented)</small>

Returns the sorted elements of a list, a set, or a sorted set.

#### [TOUCH](https://redis.io/commands/touch/) <small>(not implemented)</small>

Returns the number of existing keys out of those specified after updating the time they were last accessed.

#### [WAIT](https://redis.io/commands/wait/) <small>(not implemented)</small>

Blocks until the asynchronous replication of all preceding write commands sent by the connection is completed.

#### [WAITAOF](https://redis.io/commands/waitaof/) <small>(not implemented)</small>

Blocks until all of the preceding write commands sent by the connection are written to the append-only file of the master and/or replicas.


## transactions commands

### [DISCARD](https://redis.io/commands/discard/)

Discards a transaction.

### [EXEC](https://redis.io/commands/exec/)

Executes all commands in a transaction.

### [MULTI](https://redis.io/commands/multi/)

Starts a transaction.

### [UNWATCH](https://redis.io/commands/unwatch/)

Forgets about watched keys of a transaction.

### [WATCH](https://redis.io/commands/watch/)

Monitors changes to keys to determine the execution of a transaction.



## scripting commands

### [EVAL](https://redis.io/commands/eval/)

Executes a server-side Lua script.

### [EVALSHA](https://redis.io/commands/evalsha/)

Executes a server-side Lua script by SHA1 digest.

### [SCRIPT](https://redis.io/commands/script/)

A container for Lua scripts management commands.

### [SCRIPT EXISTS](https://redis.io/commands/script-exists/)

Determines whether server-side Lua scripts exist in the script cache.

### [SCRIPT FLUSH](https://redis.io/commands/script-flush/)

Removes all server-side Lua scripts from the script cache.

### [SCRIPT HELP](https://redis.io/commands/script-help/)

Returns helpful text about the different subcommands.

### [SCRIPT LOAD](https://redis.io/commands/script-load/)

Loads a server-side Lua script to the script cache.


### Unsupported scripting commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [EVALSHA_RO](https://redis.io/commands/evalsha_ro/) <small>(not implemented)</small>

Executes a read-only server-side Lua script by SHA1 digest.

#### [EVAL_RO](https://redis.io/commands/eval_ro/) <small>(not implemented)</small>

Executes a read-only server-side Lua script.

#### [FCALL](https://redis.io/commands/fcall/) <small>(not implemented)</small>

Invokes a function.

#### [FCALL_RO](https://redis.io/commands/fcall_ro/) <small>(not implemented)</small>

Invokes a read-only function.

#### [FUNCTION](https://redis.io/commands/function/) <small>(not implemented)</small>

A container for function commands.

#### [FUNCTION DELETE](https://redis.io/commands/function-delete/) <small>(not implemented)</small>

Deletes a library and its functions.

#### [FUNCTION DUMP](https://redis.io/commands/function-dump/) <small>(not implemented)</small>

Dumps all libraries into a serialized binary payload.

#### [FUNCTION FLUSH](https://redis.io/commands/function-flush/) <small>(not implemented)</small>

Deletes all libraries and functions.

#### [FUNCTION HELP](https://redis.io/commands/function-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [FUNCTION KILL](https://redis.io/commands/function-kill/) <small>(not implemented)</small>

Terminates a function during execution.

#### [FUNCTION LIST](https://redis.io/commands/function-list/) <small>(not implemented)</small>

Returns information about all libraries.

#### [FUNCTION LOAD](https://redis.io/commands/function-load/) <small>(not implemented)</small>

Creates a library.

#### [FUNCTION RESTORE](https://redis.io/commands/function-restore/) <small>(not implemented)</small>

Restores all libraries from a payload.

#### [FUNCTION STATS](https://redis.io/commands/function-stats/) <small>(not implemented)</small>

Returns information about a function during execution.

#### [SCRIPT DEBUG](https://redis.io/commands/script-debug/) <small>(not implemented)</small>

Sets the debug mode of server-side Lua scripts.

#### [SCRIPT KILL](https://redis.io/commands/script-kill/) <small>(not implemented)</small>

Terminates a server-side Lua script during execution.


## geo commands

### [GEOADD](https://redis.io/commands/geoadd/)

Adds one or more members to a geospatial index. The key is created if it doesn't exist.

### [GEODIST](https://redis.io/commands/geodist/)

Returns the distance between two members of a geospatial index.

### [GEOHASH](https://redis.io/commands/geohash/)

Returns members from a geospatial index as geohash strings.

### [GEOPOS](https://redis.io/commands/geopos/)

Returns the longitude and latitude of members from a geospatial index.

### [GEORADIUS](https://redis.io/commands/georadius/)

Queries a geospatial index for members within a distance from a coordinate, optionally stores the result.

### [GEORADIUSBYMEMBER](https://redis.io/commands/georadiusbymember/)

Queries a geospatial index for members within a distance from a member, optionally stores the result.

### [GEORADIUSBYMEMBER_RO](https://redis.io/commands/georadiusbymember_ro/)

Returns members from a geospatial index that are within a distance from a member.

### [GEORADIUS_RO](https://redis.io/commands/georadius_ro/)

Returns members from a geospatial index that are within a distance from a coordinate.

### [GEOSEARCH](https://redis.io/commands/geosearch/)

Queries a geospatial index for members inside an area of a box or a circle.

### [GEOSEARCHSTORE](https://redis.io/commands/geosearchstore/)

Queries a geospatial index for members inside an area of a box or a circle, optionally stores the result.



## hash commands

### [HDEL](https://redis.io/commands/hdel/)

Deletes one or more fields and their values from a hash. Deletes the hash if no fields remain.

### [HEXISTS](https://redis.io/commands/hexists/)

Determines whether a field exists in a hash.

### [HGET](https://redis.io/commands/hget/)

Returns the value of a field in a hash.

### [HGETALL](https://redis.io/commands/hgetall/)

Returns all fields and values in a hash.

### [HINCRBY](https://redis.io/commands/hincrby/)

Increments the integer value of a field in a hash by a number. Uses 0 as initial value if the field doesn't exist.

### [HINCRBYFLOAT](https://redis.io/commands/hincrbyfloat/)

Increments the floating point value of a field by a number. Uses 0 as initial value if the field doesn't exist.

### [HKEYS](https://redis.io/commands/hkeys/)

Returns all fields in a hash.

### [HLEN](https://redis.io/commands/hlen/)

Returns the number of fields in a hash.

### [HMGET](https://redis.io/commands/hmget/)

Returns the values of all fields in a hash.

### [HMSET](https://redis.io/commands/hmset/)

Sets the values of multiple fields.

### [HRANDFIELD](https://redis.io/commands/hrandfield/)

Returns one or more random fields from a hash.

### [HSCAN](https://redis.io/commands/hscan/)

Iterates over fields and values of a hash.

### [HSET](https://redis.io/commands/hset/)

Creates or modifies the value of a field in a hash.

### [HSETNX](https://redis.io/commands/hsetnx/)

Sets the value of a field in a hash only when the field doesn't exist.

### [HSTRLEN](https://redis.io/commands/hstrlen/)

Returns the length of the value of a field.

### [HVALS](https://redis.io/commands/hvals/)

Returns all values in a hash.



## hyperloglog commands

### [PFADD](https://redis.io/commands/pfadd/)

Adds elements to a HyperLogLog key. Creates the key if it doesn't exist.

### [PFCOUNT](https://redis.io/commands/pfcount/)

Returns the approximated cardinality of the set(s) observed by the HyperLogLog key(s).

### [PFMERGE](https://redis.io/commands/pfmerge/)

Merges one or more HyperLogLog values into a single key.


### Unsupported hyperloglog commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [PFDEBUG](https://redis.io/commands/pfdebug/) <small>(not implemented)</small>

Internal commands for debugging HyperLogLog values.

#### [PFSELFTEST](https://redis.io/commands/pfselftest/) <small>(not implemented)</small>

An internal command for testing HyperLogLog values.


## pubsub commands

### [PSUBSCRIBE](https://redis.io/commands/psubscribe/)

Listens for messages published to channels that match one or more patterns.

### [PUBLISH](https://redis.io/commands/publish/)

Posts a message to a channel.

### [PUBSUB](https://redis.io/commands/pubsub/)

A container for Pub/Sub commands.

### [PUBSUB CHANNELS](https://redis.io/commands/pubsub-channels/)

Returns the active channels.

### [PUBSUB HELP](https://redis.io/commands/pubsub-help/)

Returns helpful text about the different subcommands.

### [PUBSUB NUMSUB](https://redis.io/commands/pubsub-numsub/)

Returns a count of subscribers to channels.

### [PUNSUBSCRIBE](https://redis.io/commands/punsubscribe/)

Stops listening to messages published to channels that match one or more patterns.

### [SUBSCRIBE](https://redis.io/commands/subscribe/)

Listens for messages published to channels.

### [UNSUBSCRIBE](https://redis.io/commands/unsubscribe/)

Stops listening to messages posted to channels.


### Unsupported pubsub commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [PUBSUB NUMPAT](https://redis.io/commands/pubsub-numpat/) <small>(not implemented)</small>

Returns a count of unique pattern subscriptions.

#### [PUBSUB SHARDCHANNELS](https://redis.io/commands/pubsub-shardchannels/) <small>(not implemented)</small>

Returns the active shard channels.

#### [PUBSUB SHARDNUMSUB](https://redis.io/commands/pubsub-shardnumsub/) <small>(not implemented)</small>

Returns the count of subscribers of shard channels.

#### [SPUBLISH](https://redis.io/commands/spublish/) <small>(not implemented)</small>

Post a message to a shard channel

#### [SSUBSCRIBE](https://redis.io/commands/ssubscribe/) <small>(not implemented)</small>

Listens for messages published to shard channels.

#### [SUNSUBSCRIBE](https://redis.io/commands/sunsubscribe/) <small>(not implemented)</small>

Stops listening to messages posted to shard channels.


## set commands

### [SADD](https://redis.io/commands/sadd/)

Adds one or more members to a set. Creates the key if it doesn't exist.

### [SCARD](https://redis.io/commands/scard/)

Returns the number of members in a set.

### [SDIFF](https://redis.io/commands/sdiff/)

Returns the difference of multiple sets.

### [SDIFFSTORE](https://redis.io/commands/sdiffstore/)

Stores the difference of multiple sets in a key.

### [SINTER](https://redis.io/commands/sinter/)

Returns the intersect of multiple sets.

### [SINTERCARD](https://redis.io/commands/sintercard/)

Returns the number of members of the intersect of multiple sets.

### [SINTERSTORE](https://redis.io/commands/sinterstore/)

Stores the intersect of multiple sets in a key.

### [SISMEMBER](https://redis.io/commands/sismember/)

Determines whether a member belongs to a set.

### [SMEMBERS](https://redis.io/commands/smembers/)

Returns all members of a set.

### [SMISMEMBER](https://redis.io/commands/smismember/)

Determines whether multiple members belong to a set.

### [SMOVE](https://redis.io/commands/smove/)

Moves a member from one set to another.

### [SPOP](https://redis.io/commands/spop/)

Returns one or more random members from a set after removing them. Deletes the set if the last member was popped.

### [SRANDMEMBER](https://redis.io/commands/srandmember/)

Get one or multiple random members from a set

### [SREM](https://redis.io/commands/srem/)

Removes one or more members from a set. Deletes the set if the last member was removed.

### [SSCAN](https://redis.io/commands/sscan/)

Iterates over members of a set.

### [SUNION](https://redis.io/commands/sunion/)

Returns the union of multiple sets.

### [SUNIONSTORE](https://redis.io/commands/sunionstore/)

Stores the union of multiple sets in a key.



## stream commands

### [XADD](https://redis.io/commands/xadd/)

Appends a new message to a stream. Creates the key if it doesn't exist.

### [XDEL](https://redis.io/commands/xdel/)

Returns the number of messages after removing them from a stream.

### [XGROUP CREATE](https://redis.io/commands/xgroup-create/)

Creates a consumer group.

### [XGROUP CREATECONSUMER](https://redis.io/commands/xgroup-createconsumer/)

Creates a consumer in a consumer group.

### [XGROUP DELCONSUMER](https://redis.io/commands/xgroup-delconsumer/)

Deletes a consumer from a consumer group.

### [XGROUP DESTROY](https://redis.io/commands/xgroup-destroy/)

Destroys a consumer group.

### [XGROUP SETID](https://redis.io/commands/xgroup-setid/)

Sets the last-delivered ID of a consumer group.

### [XINFO CONSUMERS](https://redis.io/commands/xinfo-consumers/)

Returns a list of the consumers in a consumer group.

### [XINFO GROUPS](https://redis.io/commands/xinfo-groups/)

Returns a list of the consumer groups of a stream.

### [XLEN](https://redis.io/commands/xlen/)

Return the number of messages in a stream.

### [XRANGE](https://redis.io/commands/xrange/)

Returns the messages from a stream within a range of IDs.

### [XREAD](https://redis.io/commands/xread/)

Returns messages from multiple streams with IDs greater than the ones requested. Blocks until a message is available otherwise.

### [XREVRANGE](https://redis.io/commands/xrevrange/)

Returns the messages from a stream within a range of IDs in reverse order.

### [XTRIM](https://redis.io/commands/xtrim/)

Deletes messages from the beginning of a stream.


### Unsupported stream commands 
> To implement support for a command, see [here](../../guides/implement-command/) 

#### [XACK](https://redis.io/commands/xack/) <small>(not implemented)</small>

Returns the number of messages that were successfully acknowledged by the consumer group member of a stream.

#### [XAUTOCLAIM](https://redis.io/commands/xautoclaim/) <small>(not implemented)</small>

Changes, or acquires, ownership of messages in a consumer group, as if the messages were delivered to as consumer group member.

#### [XCLAIM](https://redis.io/commands/xclaim/) <small>(not implemented)</small>

Changes, or acquires, ownership of a message in a consumer group, as if the message was delivered a consumer group member.

#### [XGROUP](https://redis.io/commands/xgroup/) <small>(not implemented)</small>

A container for consumer groups commands.

#### [XGROUP HELP](https://redis.io/commands/xgroup-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [XINFO](https://redis.io/commands/xinfo/) <small>(not implemented)</small>

A container for stream introspection commands.

#### [XINFO HELP](https://redis.io/commands/xinfo-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [XINFO STREAM](https://redis.io/commands/xinfo-stream/) <small>(not implemented)</small>

Returns information about a stream.

#### [XPENDING](https://redis.io/commands/xpending/) <small>(not implemented)</small>

Returns the information and entries from a stream consumer group's pending entries list.

#### [XREADGROUP](https://redis.io/commands/xreadgroup/) <small>(not implemented)</small>

Returns new or historical messages from a stream for a consumer in a group. Blocks until a message is available otherwise.

#### [XSETID](https://redis.io/commands/xsetid/) <small>(not implemented)</small>

An internal command for replicating stream values.


