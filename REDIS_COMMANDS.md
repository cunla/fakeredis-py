-----
Here is a list of all redis [implemented commands](#implemented-commands) and a
list of [unimplemented commands](#unimplemented-commands).

# Implemented Commands
### string
 * [append](https://redis.io/commands/append/)
   Append a value to a key
 * [decr](https://redis.io/commands/decr/)
   Decrement the integer value of a key by one
 * [decrby](https://redis.io/commands/decrby/)
   Decrement the integer value of a key by the given number
 * [get](https://redis.io/commands/get/)
   Get the value of a key
 * [getdel](https://redis.io/commands/getdel/)
   Get the value of a key and delete the key
 * [getrange](https://redis.io/commands/getrange/)
   Get a substring of the string stored at a key
 * [getset](https://redis.io/commands/getset/)
   Set the string value of a key and return its old value
 * [incr](https://redis.io/commands/incr/)
   Increment the integer value of a key by one
 * [incrby](https://redis.io/commands/incrby/)
   Increment the integer value of a key by the given amount
 * [incrbyfloat](https://redis.io/commands/incrbyfloat/)
   Increment the float value of a key by the given amount
 * [mget](https://redis.io/commands/mget/)
   Get the values of all the given keys
 * [mset](https://redis.io/commands/mset/)
   Set multiple keys to multiple values
 * [msetnx](https://redis.io/commands/msetnx/)
   Set multiple keys to multiple values, only if none of the keys exist
 * [psetex](https://redis.io/commands/psetex/)
   Set the value and expiration in milliseconds of a key
 * [set](https://redis.io/commands/set/)
   Set the string value of a key
 * [setex](https://redis.io/commands/setex/)
   Set the value and expiration of a key
 * [setnx](https://redis.io/commands/setnx/)
   Set the value of a key, only if the key does not exist
 * [setrange](https://redis.io/commands/setrange/)
   Overwrite part of a string at key starting at the specified offset
 * [strlen](https://redis.io/commands/strlen/)
   Get the length of the value stored in a key
 * [substr](https://redis.io/commands/substr/)
   Get a substring of the string stored at a key

### server
 * [bgsave](https://redis.io/commands/bgsave/)
   Asynchronously save the dataset to disk
 * [dbsize](https://redis.io/commands/dbsize/)
   Return the number of keys in the selected database
 * [flushall](https://redis.io/commands/flushall/)
   Remove all keys from all databases
 * [flushdb](https://redis.io/commands/flushdb/)
   Remove all keys from the current database
 * [lastsave](https://redis.io/commands/lastsave/)
   Get the UNIX time stamp of the last successful save to disk
 * [save](https://redis.io/commands/save/)
   Synchronously save the dataset to disk
 * [swapdb](https://redis.io/commands/swapdb/)
   Swaps two Redis databases
 * [time](https://redis.io/commands/time/)
   Return the current server time

### bitmap
 * [bitcount](https://redis.io/commands/bitcount/)
   Count set bits in a string
 * [getbit](https://redis.io/commands/getbit/)
   Returns the bit value at offset in the string value stored at key
 * [setbit](https://redis.io/commands/setbit/)
   Sets or clears the bit at offset in the string value stored at key

### list
 * [blpop](https://redis.io/commands/blpop/)
   Remove and get the first element in a list, or block until one is available
 * [brpop](https://redis.io/commands/brpop/)
   Remove and get the last element in a list, or block until one is available
 * [brpoplpush](https://redis.io/commands/brpoplpush/)
   Pop an element from a list, push it to another list and return it; or block until one is available
 * [lindex](https://redis.io/commands/lindex/)
   Get an element from a list by its index
 * [linsert](https://redis.io/commands/linsert/)
   Insert an element before or after another element in a list
 * [llen](https://redis.io/commands/llen/)
   Get the length of a list
 * [lmove](https://redis.io/commands/lmove/)
   Pop an element from a list, push it to another list and return it
 * [lpop](https://redis.io/commands/lpop/)
   Remove and get the first elements in a list
 * [lpush](https://redis.io/commands/lpush/)
   Prepend one or multiple elements to a list
 * [lpushx](https://redis.io/commands/lpushx/)
   Prepend an element to a list, only if the list exists
 * [lrange](https://redis.io/commands/lrange/)
   Get a range of elements from a list
 * [lrem](https://redis.io/commands/lrem/)
   Remove elements from a list
 * [lset](https://redis.io/commands/lset/)
   Set the value of an element in a list by its index
 * [ltrim](https://redis.io/commands/ltrim/)
   Trim a list to the specified range
 * [rpop](https://redis.io/commands/rpop/)
   Remove and get the last elements in a list
 * [rpoplpush](https://redis.io/commands/rpoplpush/)
   Remove the last element in a list, prepend it to another list and return it
 * [rpush](https://redis.io/commands/rpush/)
   Append one or multiple elements to a list
 * [rpushx](https://redis.io/commands/rpushx/)
   Append an element to a list, only if the list exists

### sorted-set
 * [bzpopmax](https://redis.io/commands/bzpopmax/)
   Remove and return the member with the highest score from one or more sorted sets, or block until one is available
 * [bzpopmin](https://redis.io/commands/bzpopmin/)
   Remove and return the member with the lowest score from one or more sorted sets, or block until one is available
 * [zadd](https://redis.io/commands/zadd/)
   Add one or more members to a sorted set, or update its score if it already exists
 * [zcard](https://redis.io/commands/zcard/)
   Get the number of members in a sorted set
 * [zcount](https://redis.io/commands/zcount/)
   Count the members in a sorted set with scores within the given values
 * [zincrby](https://redis.io/commands/zincrby/)
   Increment the score of a member in a sorted set
 * [zinterstore](https://redis.io/commands/zinterstore/)
   Intersect multiple sorted sets and store the resulting sorted set in a new key
 * [zlexcount](https://redis.io/commands/zlexcount/)
   Count the number of members in a sorted set between a given lexicographical range
 * [zmscore](https://redis.io/commands/zmscore/)
   Get the score associated with the given members in a sorted set
 * [zpopmax](https://redis.io/commands/zpopmax/)
   Remove and return members with the highest scores in a sorted set
 * [zpopmin](https://redis.io/commands/zpopmin/)
   Remove and return members with the lowest scores in a sorted set
 * [zrange](https://redis.io/commands/zrange/)
   Return a range of members in a sorted set
 * [zrangebylex](https://redis.io/commands/zrangebylex/)
   Return a range of members in a sorted set, by lexicographical range
 * [zrangebyscore](https://redis.io/commands/zrangebyscore/)
   Return a range of members in a sorted set, by score
 * [zrank](https://redis.io/commands/zrank/)
   Determine the index of a member in a sorted set
 * [zrem](https://redis.io/commands/zrem/)
   Remove one or more members from a sorted set
 * [zremrangebylex](https://redis.io/commands/zremrangebylex/)
   Remove all members in a sorted set between the given lexicographical range
 * [zremrangebyrank](https://redis.io/commands/zremrangebyrank/)
   Remove all members in a sorted set within the given indexes
 * [zremrangebyscore](https://redis.io/commands/zremrangebyscore/)
   Remove all members in a sorted set within the given scores
 * [zrevrange](https://redis.io/commands/zrevrange/)
   Return a range of members in a sorted set, by index, with scores ordered from high to low
 * [zrevrangebylex](https://redis.io/commands/zrevrangebylex/)
   Return a range of members in a sorted set, by lexicographical range, ordered from higher to lower strings.
 * [zrevrangebyscore](https://redis.io/commands/zrevrangebyscore/)
   Return a range of members in a sorted set, by score, with scores ordered from high to low
 * [zrevrank](https://redis.io/commands/zrevrank/)
   Determine the index of a member in a sorted set, with scores ordered from high to low
 * [zscan](https://redis.io/commands/zscan/)
   Incrementally iterate sorted sets elements and associated scores
 * [zscore](https://redis.io/commands/zscore/)
   Get the score associated with the given member in a sorted set
 * [zunionstore](https://redis.io/commands/zunionstore/)
   Add multiple sorted sets and store the resulting sorted set in a new key

### generic
 * [del](https://redis.io/commands/del/)
   Delete a key
 * [dump](https://redis.io/commands/dump/)
   Return a serialized version of the value stored at the specified key.
 * [exists](https://redis.io/commands/exists/)
   Determine if a key exists
 * [expire](https://redis.io/commands/expire/)
   Set a key's time to live in seconds
 * [expireat](https://redis.io/commands/expireat/)
   Set the expiration for a key as a UNIX timestamp
 * [keys](https://redis.io/commands/keys/)
   Find all keys matching the given pattern
 * [move](https://redis.io/commands/move/)
   Move a key to another database
 * [persist](https://redis.io/commands/persist/)
   Remove the expiration from a key
 * [pexpire](https://redis.io/commands/pexpire/)
   Set a key's time to live in milliseconds
 * [pexpireat](https://redis.io/commands/pexpireat/)
   Set the expiration for a key as a UNIX timestamp specified in milliseconds
 * [pttl](https://redis.io/commands/pttl/)
   Get the time to live for a key in milliseconds
 * [randomkey](https://redis.io/commands/randomkey/)
   Return a random key from the keyspace
 * [rename](https://redis.io/commands/rename/)
   Rename a key
 * [renamenx](https://redis.io/commands/renamenx/)
   Rename a key, only if the new key does not exist
 * [restore](https://redis.io/commands/restore/)
   Create a key using the provided serialized value, previously obtained using DUMP.
 * [scan](https://redis.io/commands/scan/)
   Incrementally iterate the keys space
 * [sort](https://redis.io/commands/sort/)
   Sort the elements in a list, set or sorted set
 * [ttl](https://redis.io/commands/ttl/)
   Get the time to live for a key in seconds
 * [type](https://redis.io/commands/type/)
   Determine the type stored at key
 * [unlink](https://redis.io/commands/unlink/)
   Delete a key asynchronously in another thread. Otherwise it is just as DEL, but non blocking.

### transactions
 * [discard](https://redis.io/commands/discard/)
   Discard all commands issued after MULTI
 * [exec](https://redis.io/commands/exec/)
   Execute all commands issued after MULTI
 * [multi](https://redis.io/commands/multi/)
   Mark the start of a transaction block
 * [unwatch](https://redis.io/commands/unwatch/)
   Forget about all watched keys
 * [watch](https://redis.io/commands/watch/)
   Watch the given keys to determine execution of the MULTI/EXEC block

### connection
 * [echo](https://redis.io/commands/echo/)
   Echo the given string
 * [ping](https://redis.io/commands/ping/)
   Ping the server
 * [select](https://redis.io/commands/select/)
   Change the selected database for the current connection

### scripting
 * [eval](https://redis.io/commands/eval/)
   Execute a Lua script server side
 * [evalsha](https://redis.io/commands/evalsha/)
   Execute a Lua script server side
 * [script](https://redis.io/commands/script/)
   A container for Lua scripts management commands
 * [script exists](https://redis.io/commands/script-exists/)
   Check existence of scripts in the script cache.
 * [script flush](https://redis.io/commands/script-flush/)
   Remove all the scripts from the script cache.
 * [script load](https://redis.io/commands/script-load/)
   Load the specified Lua script into the script cache.

### hash
 * [hdel](https://redis.io/commands/hdel/)
   Delete one or more hash fields
 * [hexists](https://redis.io/commands/hexists/)
   Determine if a hash field exists
 * [hget](https://redis.io/commands/hget/)
   Get the value of a hash field
 * [hgetall](https://redis.io/commands/hgetall/)
   Get all the fields and values in a hash
 * [hincrby](https://redis.io/commands/hincrby/)
   Increment the integer value of a hash field by the given number
 * [hincrbyfloat](https://redis.io/commands/hincrbyfloat/)
   Increment the float value of a hash field by the given amount
 * [hkeys](https://redis.io/commands/hkeys/)
   Get all the fields in a hash
 * [hlen](https://redis.io/commands/hlen/)
   Get the number of fields in a hash
 * [hmget](https://redis.io/commands/hmget/)
   Get the values of all the given hash fields
 * [hmset](https://redis.io/commands/hmset/)
   Set multiple hash fields to multiple values
 * [hscan](https://redis.io/commands/hscan/)
   Incrementally iterate hash fields and associated values
 * [hset](https://redis.io/commands/hset/)
   Set the string value of a hash field
 * [hsetnx](https://redis.io/commands/hsetnx/)
   Set the value of a hash field, only if the field does not exist
 * [hstrlen](https://redis.io/commands/hstrlen/)
   Get the length of the value of a hash field
 * [hvals](https://redis.io/commands/hvals/)
   Get all the values in a hash

### hyperloglog
 * [pfadd](https://redis.io/commands/pfadd/)
   Adds the specified elements to the specified HyperLogLog.
 * [pfcount](https://redis.io/commands/pfcount/)
   Return the approximated cardinality of the set(s) observed by the HyperLogLog at key(s).
 * [pfmerge](https://redis.io/commands/pfmerge/)
   Merge N different HyperLogLogs into a single one.

### pubsub
 * [psubscribe](https://redis.io/commands/psubscribe/)
   Listen for messages published to channels matching the given patterns
 * [publish](https://redis.io/commands/publish/)
   Post a message to a channel
 * [punsubscribe](https://redis.io/commands/punsubscribe/)
   Stop listening for messages posted to channels matching the given patterns
 * [subscribe](https://redis.io/commands/subscribe/)
   Listen for messages published to the given channels
 * [unsubscribe](https://redis.io/commands/unsubscribe/)
   Stop listening for messages posted to the given channels

### set
 * [sadd](https://redis.io/commands/sadd/)
   Add one or more members to a set
 * [scard](https://redis.io/commands/scard/)
   Get the number of members in a set
 * [sdiff](https://redis.io/commands/sdiff/)
   Subtract multiple sets
 * [sdiffstore](https://redis.io/commands/sdiffstore/)
   Subtract multiple sets and store the resulting set in a key
 * [sinter](https://redis.io/commands/sinter/)
   Intersect multiple sets
 * [sintercard](https://redis.io/commands/sintercard/)
   Intersect multiple sets and return the cardinality of the result
 * [sinterstore](https://redis.io/commands/sinterstore/)
   Intersect multiple sets and store the resulting set in a key
 * [sismember](https://redis.io/commands/sismember/)
   Determine if a given value is a member of a set
 * [smembers](https://redis.io/commands/smembers/)
   Get all the members in a set
 * [smismember](https://redis.io/commands/smismember/)
   Returns the membership associated with the given elements for a set
 * [smove](https://redis.io/commands/smove/)
   Move a member from one set to another
 * [spop](https://redis.io/commands/spop/)
   Remove and return one or multiple random members from a set
 * [srandmember](https://redis.io/commands/srandmember/)
   Get one or multiple random members from a set
 * [srem](https://redis.io/commands/srem/)
   Remove one or more members from a set
 * [sscan](https://redis.io/commands/sscan/)
   Incrementally iterate Set elements
 * [sunion](https://redis.io/commands/sunion/)
   Add multiple sets
 * [sunionstore](https://redis.io/commands/sunionstore/)
   Add multiple sets and store the resulting set in a key

# Unimplemented Commands
All the redis commands are implemented in fakeredis with these exceptions:
    
### server
 * [acl](https://redis.io/commands/acl/)
   A container for Access List Control commands 
 * [acl cat](https://redis.io/commands/acl-cat/)
   List the ACL categories or the commands inside a category
 * [acl deluser](https://redis.io/commands/acl-deluser/)
   Remove the specified ACL users and the associated rules
 * [acl dryrun](https://redis.io/commands/acl-dryrun/)
   Returns whether the user can execute the given command without executing the command.
 * [acl genpass](https://redis.io/commands/acl-genpass/)
   Generate a pseudorandom secure password to use for ACL users
 * [acl getuser](https://redis.io/commands/acl-getuser/)
   Get the rules for a specific ACL user
 * [acl help](https://redis.io/commands/acl-help/)
   Show helpful text about the different subcommands
 * [acl list](https://redis.io/commands/acl-list/)
   List the current ACL rules in ACL config file format
 * [acl load](https://redis.io/commands/acl-load/)
   Reload the ACLs from the configured ACL file
 * [acl log](https://redis.io/commands/acl-log/)
   List latest events denied because of ACLs in place
 * [acl save](https://redis.io/commands/acl-save/)
   Save the current ACL rules in the configured ACL file
 * [acl setuser](https://redis.io/commands/acl-setuser/)
   Modify or create the rules for a specific ACL user
 * [acl users](https://redis.io/commands/acl-users/)
   List the username of all the configured ACL rules
 * [acl whoami](https://redis.io/commands/acl-whoami/)
   Return the name of the user associated to the current connection
 * [bgrewriteaof](https://redis.io/commands/bgrewriteaof/)
   Asynchronously rewrite the append-only file
 * [command](https://redis.io/commands/command/)
   Get array of Redis command details
 * [command count](https://redis.io/commands/command-count/)
   Get total number of Redis commands
 * [command docs](https://redis.io/commands/command-docs/)
   Get array of specific Redis command documentation
 * [command getkeys](https://redis.io/commands/command-getkeys/)
   Extract keys given a full Redis command
 * [command getkeysandflags](https://redis.io/commands/command-getkeysandflags/)
   Extract keys and access flags given a full Redis command
 * [command help](https://redis.io/commands/command-help/)
   Show helpful text about the different subcommands
 * [command info](https://redis.io/commands/command-info/)
   Get array of specific Redis command details, or all when no argument is given.
 * [command list](https://redis.io/commands/command-list/)
   Get an array of Redis command names
 * [config](https://redis.io/commands/config/)
   A container for server configuration commands
 * [config get](https://redis.io/commands/config-get/)
   Get the values of configuration parameters
 * [config help](https://redis.io/commands/config-help/)
   Show helpful text about the different subcommands
 * [config resetstat](https://redis.io/commands/config-resetstat/)
   Reset the stats returned by INFO
 * [config rewrite](https://redis.io/commands/config-rewrite/)
   Rewrite the configuration file with the in memory configuration
 * [config set](https://redis.io/commands/config-set/)
   Set configuration parameters to the given values
 * [debug](https://redis.io/commands/debug/)
   A container for debugging commands
 * [failover](https://redis.io/commands/failover/)
   Start a coordinated failover between this server and one of its replicas.
 * [info](https://redis.io/commands/info/)
   Get information and statistics about the server
 * [latency](https://redis.io/commands/latency/)
   A container for latency diagnostics commands
 * [latency doctor](https://redis.io/commands/latency-doctor/)
   Return a human readable latency analysis report.
 * [latency graph](https://redis.io/commands/latency-graph/)
   Return a latency graph for the event.
 * [latency help](https://redis.io/commands/latency-help/)
   Show helpful text about the different subcommands.
 * [latency histogram](https://redis.io/commands/latency-histogram/)
   Return the cumulative distribution of latencies of a subset of commands or all.
 * [latency history](https://redis.io/commands/latency-history/)
   Return timestamp-latency samples for the event.
 * [latency latest](https://redis.io/commands/latency-latest/)
   Return the latest latency samples for all events.
 * [latency reset](https://redis.io/commands/latency-reset/)
   Reset latency data for one or more events.
 * [lolwut](https://redis.io/commands/lolwut/)
   Display some computer art and the Redis version
 * [memory](https://redis.io/commands/memory/)
   A container for memory diagnostics commands
 * [memory doctor](https://redis.io/commands/memory-doctor/)
   Outputs memory problems report
 * [memory help](https://redis.io/commands/memory-help/)
   Show helpful text about the different subcommands
 * [memory malloc-stats](https://redis.io/commands/memory-malloc-stats/)
   Show allocator internal stats
 * [memory purge](https://redis.io/commands/memory-purge/)
   Ask the allocator to release memory
 * [memory stats](https://redis.io/commands/memory-stats/)
   Show memory usage details
 * [memory usage](https://redis.io/commands/memory-usage/)
   Estimate the memory usage of a key
 * [module](https://redis.io/commands/module/)
   A container for module commands
 * [module help](https://redis.io/commands/module-help/)
   Show helpful text about the different subcommands
 * [module list](https://redis.io/commands/module-list/)
   List all modules loaded by the server
 * [module load](https://redis.io/commands/module-load/)
   Load a module
 * [module loadex](https://redis.io/commands/module-loadex/)
   Load a module with extended parameters
 * [module unload](https://redis.io/commands/module-unload/)
   Unload a module
 * [monitor](https://redis.io/commands/monitor/)
   Listen for all requests received by the server in real time
 * [psync](https://redis.io/commands/psync/)
   Internal command used for replication
 * [replconf](https://redis.io/commands/replconf/)
   An internal command for configuring the replication stream
 * [replicaof](https://redis.io/commands/replicaof/)
   Make the server a replica of another instance, or promote it as master.
 * [restore-asking](https://redis.io/commands/restore-asking/)
   An internal command for migrating keys in a cluster
 * [role](https://redis.io/commands/role/)
   Return the role of the instance in the context of replication
 * [shutdown](https://redis.io/commands/shutdown/)
   Synchronously save the dataset to disk and then shut down the server
 * [slaveof](https://redis.io/commands/slaveof/)
   Make the server a replica of another instance, or promote it as master.
 * [slowlog](https://redis.io/commands/slowlog/)
   A container for slow log commands
 * [slowlog get](https://redis.io/commands/slowlog-get/)
   Get the slow log's entries
 * [slowlog help](https://redis.io/commands/slowlog-help/)
   Show helpful text about the different subcommands
 * [slowlog len](https://redis.io/commands/slowlog-len/)
   Get the slow log's length
 * [slowlog reset](https://redis.io/commands/slowlog-reset/)
   Clear all entries from the slow log
 * [sync](https://redis.io/commands/sync/)
   Internal command used for replication

### cluster
 * [asking](https://redis.io/commands/asking/)
   Sent by cluster clients after an -ASK redirect
 * [cluster](https://redis.io/commands/cluster/)
   A container for cluster commands
 * [cluster addslots](https://redis.io/commands/cluster-addslots/)
   Assign new hash slots to receiving node
 * [cluster addslotsrange](https://redis.io/commands/cluster-addslotsrange/)
   Assign new hash slots to receiving node
 * [cluster bumpepoch](https://redis.io/commands/cluster-bumpepoch/)
   Advance the cluster config epoch
 * [cluster count-failure-reports](https://redis.io/commands/cluster-count-failure-reports/)
   Return the number of failure reports active for a given node
 * [cluster countkeysinslot](https://redis.io/commands/cluster-countkeysinslot/)
   Return the number of local keys in the specified hash slot
 * [cluster delslots](https://redis.io/commands/cluster-delslots/)
   Set hash slots as unbound in receiving node
 * [cluster delslotsrange](https://redis.io/commands/cluster-delslotsrange/)
   Set hash slots as unbound in receiving node
 * [cluster failover](https://redis.io/commands/cluster-failover/)
   Forces a replica to perform a manual failover of its master.
 * [cluster flushslots](https://redis.io/commands/cluster-flushslots/)
   Delete a node's own slots information
 * [cluster forget](https://redis.io/commands/cluster-forget/)
   Remove a node from the nodes table
 * [cluster getkeysinslot](https://redis.io/commands/cluster-getkeysinslot/)
   Return local key names in the specified hash slot
 * [cluster help](https://redis.io/commands/cluster-help/)
   Show helpful text about the different subcommands
 * [cluster info](https://redis.io/commands/cluster-info/)
   Provides info about Redis Cluster node state
 * [cluster keyslot](https://redis.io/commands/cluster-keyslot/)
   Returns the hash slot of the specified key
 * [cluster links](https://redis.io/commands/cluster-links/)
   Returns a list of all TCP links to and from peer nodes in cluster
 * [cluster meet](https://redis.io/commands/cluster-meet/)
   Force a node cluster to handshake with another node
 * [cluster myid](https://redis.io/commands/cluster-myid/)
   Return the node id
 * [cluster nodes](https://redis.io/commands/cluster-nodes/)
   Get Cluster config for the node
 * [cluster replicas](https://redis.io/commands/cluster-replicas/)
   List replica nodes of the specified master node
 * [cluster replicate](https://redis.io/commands/cluster-replicate/)
   Reconfigure a node as a replica of the specified master node
 * [cluster reset](https://redis.io/commands/cluster-reset/)
   Reset a Redis Cluster node
 * [cluster saveconfig](https://redis.io/commands/cluster-saveconfig/)
   Forces the node to save cluster state on disk
 * [cluster set-config-epoch](https://redis.io/commands/cluster-set-config-epoch/)
   Set the configuration epoch in a new node
 * [cluster setslot](https://redis.io/commands/cluster-setslot/)
   Bind a hash slot to a specific node
 * [cluster shards](https://redis.io/commands/cluster-shards/)
   Get array of cluster slots to node mappings
 * [cluster slaves](https://redis.io/commands/cluster-slaves/)
   List replica nodes of the specified master node
 * [cluster slots](https://redis.io/commands/cluster-slots/)
   Get array of Cluster slot to node mappings
 * [readonly](https://redis.io/commands/readonly/)
   Enables read queries for a connection to a cluster replica node
 * [readwrite](https://redis.io/commands/readwrite/)
   Disables read queries for a connection to a cluster replica node

### connection
 * [auth](https://redis.io/commands/auth/)
   Authenticate to the server
 * [client](https://redis.io/commands/client/)
   A container for client connection commands
 * [client caching](https://redis.io/commands/client-caching/)
   Instruct the server about tracking or not keys in the next request
 * [client getname](https://redis.io/commands/client-getname/)
   Get the current connection name
 * [client getredir](https://redis.io/commands/client-getredir/)
   Get tracking notifications redirection client ID if any
 * [client help](https://redis.io/commands/client-help/)
   Show helpful text about the different subcommands
 * [client id](https://redis.io/commands/client-id/)
   Returns the client ID for the current connection
 * [client info](https://redis.io/commands/client-info/)
   Returns information about the current client connection.
 * [client kill](https://redis.io/commands/client-kill/)
   Kill the connection of a client
 * [client list](https://redis.io/commands/client-list/)
   Get the list of client connections
 * [client no-evict](https://redis.io/commands/client-no-evict/)
   Set client eviction mode for the current connection
 * [client pause](https://redis.io/commands/client-pause/)
   Stop processing commands from clients for some time
 * [client reply](https://redis.io/commands/client-reply/)
   Instruct the server whether to reply to commands
 * [client setname](https://redis.io/commands/client-setname/)
   Set the current connection name
 * [client tracking](https://redis.io/commands/client-tracking/)
   Enable or disable server assisted client side caching support
 * [client trackinginfo](https://redis.io/commands/client-trackinginfo/)
   Return information about server assisted client side caching for the current connection
 * [client unblock](https://redis.io/commands/client-unblock/)
   Unblock a client blocked in a blocking command from a different connection
 * [client unpause](https://redis.io/commands/client-unpause/)
   Resume processing of clients that were paused
 * [hello](https://redis.io/commands/hello/)
   Handshake with Redis
 * [quit](https://redis.io/commands/quit/)
   Close the connection
 * [reset](https://redis.io/commands/reset/)
   Reset the connection

### bitmap
 * [bitfield](https://redis.io/commands/bitfield/)
   Perform arbitrary bitfield integer operations on strings
 * [bitfield_ro](https://redis.io/commands/bitfield_ro/)
   Perform arbitrary bitfield integer operations on strings. Read-only variant of BITFIELD
 * [bitop](https://redis.io/commands/bitop/)
   Perform bitwise operations between strings
 * [bitpos](https://redis.io/commands/bitpos/)
   Find first bit set or clear in a string

### list
 * [blmove](https://redis.io/commands/blmove/)
   Pop an element from a list, push it to another list and return it; or block until one is available
 * [blmpop](https://redis.io/commands/blmpop/)
   Pop elements from a list, or block until one is available
 * [lmpop](https://redis.io/commands/lmpop/)
   Pop elements from a list
 * [lpos](https://redis.io/commands/lpos/)
   Return the index of matching elements on a list

### sorted-set
 * [bzmpop](https://redis.io/commands/bzmpop/)
   Remove and return members with scores in a sorted set or block until one is available
 * [zdiff](https://redis.io/commands/zdiff/)
   Subtract multiple sorted sets
 * [zdiffstore](https://redis.io/commands/zdiffstore/)
   Subtract multiple sorted sets and store the resulting sorted set in a new key
 * [zinter](https://redis.io/commands/zinter/)
   Intersect multiple sorted sets
 * [zintercard](https://redis.io/commands/zintercard/)
   Intersect multiple sorted sets and return the cardinality of the result
 * [zmpop](https://redis.io/commands/zmpop/)
   Remove and return members with scores in a sorted set
 * [zrandmember](https://redis.io/commands/zrandmember/)
   Get one or multiple random elements from a sorted set
 * [zrangestore](https://redis.io/commands/zrangestore/)
   Store a range of members from sorted set into another key
 * [zunion](https://redis.io/commands/zunion/)
   Add multiple sorted sets

### generic
 * [copy](https://redis.io/commands/copy/)
   Copy a key
 * [expiretime](https://redis.io/commands/expiretime/)
   Get the expiration Unix timestamp for a key
 * [migrate](https://redis.io/commands/migrate/)
   Atomically transfer a key from a Redis instance to another one.
 * [object](https://redis.io/commands/object/)
   A container for object introspection commands
 * [object encoding](https://redis.io/commands/object-encoding/)
   Inspect the internal encoding of a Redis object
 * [object freq](https://redis.io/commands/object-freq/)
   Get the logarithmic access frequency counter of a Redis object
 * [object help](https://redis.io/commands/object-help/)
   Show helpful text about the different subcommands
 * [object idletime](https://redis.io/commands/object-idletime/)
   Get the time since a Redis object was last accessed
 * [object refcount](https://redis.io/commands/object-refcount/)
   Get the number of references to the value of the key
 * [pexpiretime](https://redis.io/commands/pexpiretime/)
   Get the expiration Unix timestamp for a key in milliseconds
 * [sort_ro](https://redis.io/commands/sort_ro/)
   Sort the elements in a list, set or sorted set. Read-only variant of SORT.
 * [touch](https://redis.io/commands/touch/)
   Alters the last access time of a key(s). Returns the number of existing keys specified.
 * [wait](https://redis.io/commands/wait/)
   Wait for the synchronous replication of all the write commands sent in the context of the current connection

### scripting
 * [evalsha_ro](https://redis.io/commands/evalsha_ro/)
   Execute a read-only Lua script server side
 * [eval_ro](https://redis.io/commands/eval_ro/)
   Execute a read-only Lua script server side
 * [fcall](https://redis.io/commands/fcall/)
   Invoke a function
 * [fcall_ro](https://redis.io/commands/fcall_ro/)
   Invoke a read-only function
 * [function](https://redis.io/commands/function/)
   A container for function commands
 * [function delete](https://redis.io/commands/function-delete/)
   Delete a function by name
 * [function dump](https://redis.io/commands/function-dump/)
   Dump all functions into a serialized binary payload
 * [function flush](https://redis.io/commands/function-flush/)
   Deleting all functions
 * [function help](https://redis.io/commands/function-help/)
   Show helpful text about the different subcommands
 * [function kill](https://redis.io/commands/function-kill/)
   Kill the function currently in execution.
 * [function list](https://redis.io/commands/function-list/)
   List information about all the functions
 * [function load](https://redis.io/commands/function-load/)
   Create a function with the given arguments (name, code, description)
 * [function restore](https://redis.io/commands/function-restore/)
   Restore all the functions on the given payload
 * [function stats](https://redis.io/commands/function-stats/)
   Return information about the function currently running (name, description, duration)
 * [script debug](https://redis.io/commands/script-debug/)
   Set the debug mode for executed scripts.
 * [script help](https://redis.io/commands/script-help/)
   Show helpful text about the different subcommands
 * [script kill](https://redis.io/commands/script-kill/)
   Kill the script currently in execution.

### geo
 * [geoadd](https://redis.io/commands/geoadd/)
   Add one or more geospatial items in the geospatial index represented using a sorted set
 * [geodist](https://redis.io/commands/geodist/)
   Returns the distance between two members of a geospatial index
 * [geohash](https://redis.io/commands/geohash/)
   Returns members of a geospatial index as standard geohash strings
 * [geopos](https://redis.io/commands/geopos/)
   Returns longitude and latitude of members of a geospatial index
 * [georadius](https://redis.io/commands/georadius/)
   Query a sorted set representing a geospatial index to fetch members matching a given maximum distance from a point
 * [georadiusbymember](https://redis.io/commands/georadiusbymember/)
   Query a sorted set representing a geospatial index to fetch members matching a given maximum distance from a member
 * [georadiusbymember_ro](https://redis.io/commands/georadiusbymember_ro/)
   A read-only variant for GEORADIUSBYMEMBER
 * [georadius_ro](https://redis.io/commands/georadius_ro/)
   A read-only variant for GEORADIUS
 * [geosearch](https://redis.io/commands/geosearch/)
   Query a sorted set representing a geospatial index to fetch members inside an area of a box or a circle.
 * [geosearchstore](https://redis.io/commands/geosearchstore/)
   Query a sorted set representing a geospatial index to fetch members inside an area of a box or a circle, and store the result in another key.

### string
 * [getex](https://redis.io/commands/getex/)
   Get the value of a key and optionally set its expiration
 * [lcs](https://redis.io/commands/lcs/)
   Find longest common substring

### hash
 * [hrandfield](https://redis.io/commands/hrandfield/)
   Get one or multiple random fields from a hash

### hyperloglog
 * [pfdebug](https://redis.io/commands/pfdebug/)
   Internal commands for debugging HyperLogLog values
 * [pfselftest](https://redis.io/commands/pfselftest/)
   An internal command for testing HyperLogLog values

### pubsub
 * [pubsub](https://redis.io/commands/pubsub/)
   A container for Pub/Sub commands
 * [pubsub channels](https://redis.io/commands/pubsub-channels/)
   List active channels
 * [pubsub help](https://redis.io/commands/pubsub-help/)
   Show helpful text about the different subcommands
 * [pubsub numpat](https://redis.io/commands/pubsub-numpat/)
   Get the count of unique patterns pattern subscriptions
 * [pubsub numsub](https://redis.io/commands/pubsub-numsub/)
   Get the count of subscribers for channels
 * [pubsub shardchannels](https://redis.io/commands/pubsub-shardchannels/)
   List active shard channels
 * [pubsub shardnumsub](https://redis.io/commands/pubsub-shardnumsub/)
   Get the count of subscribers for shard channels
 * [spublish](https://redis.io/commands/spublish/)
   Post a message to a shard channel
 * [ssubscribe](https://redis.io/commands/ssubscribe/)
   Listen for messages published to the given shard channels
 * [sunsubscribe](https://redis.io/commands/sunsubscribe/)
   Stop listening for messages posted to the given shard channels

### stream
 * [xack](https://redis.io/commands/xack/)
   Marks a pending message as correctly processed, effectively removing it from the pending entries list of the consumer group. Return value of the command is the number of messages successfully acknowledged, that is, the IDs we were actually able to resolve in the PEL.
 * [xadd](https://redis.io/commands/xadd/)
   Appends a new entry to a stream
 * [xautoclaim](https://redis.io/commands/xautoclaim/)
   Changes (or acquires) ownership of messages in a consumer group, as if the messages were delivered to the specified consumer.
 * [xclaim](https://redis.io/commands/xclaim/)
   Changes (or acquires) ownership of a message in a consumer group, as if the message was delivered to the specified consumer.
 * [xdel](https://redis.io/commands/xdel/)
   Removes the specified entries from the stream. Returns the number of items actually deleted, that may be different from the number of IDs passed in case certain IDs do not exist.
 * [xgroup](https://redis.io/commands/xgroup/)
   A container for consumer groups commands
 * [xgroup create](https://redis.io/commands/xgroup-create/)
   Create a consumer group.
 * [xgroup createconsumer](https://redis.io/commands/xgroup-createconsumer/)
   Create a consumer in a consumer group.
 * [xgroup delconsumer](https://redis.io/commands/xgroup-delconsumer/)
   Delete a consumer from a consumer group.
 * [xgroup destroy](https://redis.io/commands/xgroup-destroy/)
   Destroy a consumer group.
 * [xgroup help](https://redis.io/commands/xgroup-help/)
   Show helpful text about the different subcommands
 * [xgroup setid](https://redis.io/commands/xgroup-setid/)
   Set a consumer group to an arbitrary last delivered ID value.
 * [xinfo](https://redis.io/commands/xinfo/)
   A container for stream introspection commands
 * [xinfo consumers](https://redis.io/commands/xinfo-consumers/)
   List the consumers in a consumer group
 * [xinfo groups](https://redis.io/commands/xinfo-groups/)
   List the consumer groups of a stream
 * [xinfo help](https://redis.io/commands/xinfo-help/)
   Show helpful text about the different subcommands
 * [xinfo stream](https://redis.io/commands/xinfo-stream/)
   Get information about a stream
 * [xlen](https://redis.io/commands/xlen/)
   Return the number of entries in a stream
 * [xpending](https://redis.io/commands/xpending/)
   Return information and entries from a stream consumer group pending entries list, that are messages fetched but never acknowledged.
 * [xrange](https://redis.io/commands/xrange/)
   Return a range of elements in a stream, with IDs matching the specified IDs interval
 * [xread](https://redis.io/commands/xread/)
   Return never seen elements in multiple streams, with IDs greater than the ones reported by the caller for each stream. Can block.
 * [xreadgroup](https://redis.io/commands/xreadgroup/)
   Return new entries from a stream using a consumer group, or access the history of the pending entries for a given consumer. Can block.
 * [xrevrange](https://redis.io/commands/xrevrange/)
   Return a range of elements in a stream, with IDs matching the specified IDs interval, in reverse order (from greater to smaller IDs) compared to XRANGE
 * [xsetid](https://redis.io/commands/xsetid/)
   An internal command for replicating stream values
 * [xtrim](https://redis.io/commands/xtrim/)
   Trims the stream to (approximately if '~' is passed) a certain size

### json
 * [json.del](https://redis.io/commands/json.del/)
   Deletes a value
 * [json.forget](https://redis.io/commands/json.forget/)
   Deletes a value
 * [json.get](https://redis.io/commands/json.get/)
   Gets the value at one or more paths in JSON serialized form
 * [json.toggle](https://redis.io/commands/json.toggle/)
   Toggles a boolean value
 * [json.clear](https://redis.io/commands/json.clear/)
   Clears all values from an array or an object and sets numeric values to `0`
 * [json.set](https://redis.io/commands/json.set/)
   Sets or updates the JSON value at a path
 * [json.mget](https://redis.io/commands/json.mget/)
   Returns the values at a path from one or more keys
 * [json.numincrby](https://redis.io/commands/json.numincrby/)
   Increments the numeric value at path by a value
 * [json.nummultby](https://redis.io/commands/json.nummultby/)
   Multiplies the numeric value at path by a value
 * [json.strappend](https://redis.io/commands/json.strappend/)
   Appends a string to a JSON string value at path
 * [json.strlen](https://redis.io/commands/json.strlen/)
   Returns the length of the JSON String at path in key
 * [json.arrappend](https://redis.io/commands/json.arrappend/)
   Append one or more json values into the array at path after the last element in it.
 * [json.arrindex](https://redis.io/commands/json.arrindex/)
   Returns the index of the first occurrence of a JSON scalar value in the array at path
 * [json.arrinsert](https://redis.io/commands/json.arrinsert/)
   Inserts the JSON scalar(s) value at the specified index in the array at path
 * [json.arrlen](https://redis.io/commands/json.arrlen/)
   Returns the length of the array at path
 * [json.arrpop](https://redis.io/commands/json.arrpop/)
   Removes and returns the element at the specified index in the array at path
 * [json.arrtrim](https://redis.io/commands/json.arrtrim/)
   Trims the array at path to contain only the specified inclusive range of indices from start to stop
 * [json.objkeys](https://redis.io/commands/json.objkeys/)
   Returns the JSON keys of the object at path
 * [json.objlen](https://redis.io/commands/json.objlen/)
   Returns the number of keys of the object at path
 * [json.type](https://redis.io/commands/json.type/)
   Returns the type of the JSON value at path
 * [json.resp](https://redis.io/commands/json.resp/)
   Returns the JSON value at path in Redis Serialization Protocol (RESP)
 * [json.debug](https://redis.io/commands/json.debug/)
   Debugging container command
 * [json.debug help](https://redis.io/commands/json.debug-help/)
   Shows helpful information
 * [json.debug memory](https://redis.io/commands/json.debug-memory/)
   Reports the size in bytes of a key

### graph
 * [graph.query](https://redis.io/commands/graph.query/)
   Executes the given query against a specified graph
 * [graph.ro_query](https://redis.io/commands/graph.ro_query/)
   Executes a given read only query against a specified graph
 * [graph.delete](https://redis.io/commands/graph.delete/)
   Completely removes the graph and all of its entities
 * [graph.explain](https://redis.io/commands/graph.explain/)
   Returns a query execution plan without running the query
 * [graph.profile](https://redis.io/commands/graph.profile/)
   Executes a query and returns an execution plan augmented with metrics for each operation's execution
 * [graph.slowlog](https://redis.io/commands/graph.slowlog/)
   Returns a list containing up to 10 of the slowest queries issued against the given graph
 * [graph.config get](https://redis.io/commands/graph.config-get/)
   Retrieves a RedisGraph configuration
 * [graph.config set](https://redis.io/commands/graph.config-set/)
   Updates a RedisGraph configuration
 * [graph.list](https://redis.io/commands/graph.list/)
   Lists all graph keys in the keyspace

