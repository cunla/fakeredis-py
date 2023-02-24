# Redis commands

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


### Unsupported server commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [ACL](https://redis.io/commands/acl/) <small>(not implemented)</small>

A container for Access List Control commands 

#### [ACL CAT](https://redis.io/commands/acl-cat/) <small>(not implemented)</small>

List the ACL categories or the commands inside a category

#### [ACL DELUSER](https://redis.io/commands/acl-deluser/) <small>(not implemented)</small>

Remove the specified ACL users and the associated rules

#### [ACL DRYRUN](https://redis.io/commands/acl-dryrun/) <small>(not implemented)</small>

Returns whether the user can execute the given command without executing the command.

#### [ACL GENPASS](https://redis.io/commands/acl-genpass/) <small>(not implemented)</small>

Generate a pseudorandom secure password to use for ACL users

#### [ACL GETUSER](https://redis.io/commands/acl-getuser/) <small>(not implemented)</small>

Get the rules for a specific ACL user

#### [ACL HELP](https://redis.io/commands/acl-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [ACL LIST](https://redis.io/commands/acl-list/) <small>(not implemented)</small>

List the current ACL rules in ACL config file format

#### [ACL LOAD](https://redis.io/commands/acl-load/) <small>(not implemented)</small>

Reload the ACLs from the configured ACL file

#### [ACL LOG](https://redis.io/commands/acl-log/) <small>(not implemented)</small>

List latest events denied because of ACLs in place

#### [ACL SAVE](https://redis.io/commands/acl-save/) <small>(not implemented)</small>

Save the current ACL rules in the configured ACL file

#### [ACL SETUSER](https://redis.io/commands/acl-setuser/) <small>(not implemented)</small>

Modify or create the rules for a specific ACL user

#### [ACL USERS](https://redis.io/commands/acl-users/) <small>(not implemented)</small>

List the username of all the configured ACL rules

#### [ACL WHOAMI](https://redis.io/commands/acl-whoami/) <small>(not implemented)</small>

Return the name of the user associated to the current connection

#### [BGREWRITEAOF](https://redis.io/commands/bgrewriteaof/) <small>(not implemented)</small>

Asynchronously rewrite the append-only file

#### [COMMAND](https://redis.io/commands/command/) <small>(not implemented)</small>

Get array of Redis command details

#### [COMMAND COUNT](https://redis.io/commands/command-count/) <small>(not implemented)</small>

Get total number of Redis commands

#### [COMMAND DOCS](https://redis.io/commands/command-docs/) <small>(not implemented)</small>

Get array of specific Redis command documentation

#### [COMMAND GETKEYS](https://redis.io/commands/command-getkeys/) <small>(not implemented)</small>

Extract keys given a full Redis command

#### [COMMAND GETKEYSANDFLAGS](https://redis.io/commands/command-getkeysandflags/) <small>(not implemented)</small>

Extract keys and access flags given a full Redis command

#### [COMMAND HELP](https://redis.io/commands/command-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [COMMAND INFO](https://redis.io/commands/command-info/) <small>(not implemented)</small>

Get array of specific Redis command details, or all when no argument is given.

#### [COMMAND LIST](https://redis.io/commands/command-list/) <small>(not implemented)</small>

Get an array of Redis command names

#### [CONFIG](https://redis.io/commands/config/) <small>(not implemented)</small>

A container for server configuration commands

#### [CONFIG GET](https://redis.io/commands/config-get/) <small>(not implemented)</small>

Get the values of configuration parameters

#### [CONFIG HELP](https://redis.io/commands/config-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [CONFIG RESETSTAT](https://redis.io/commands/config-resetstat/) <small>(not implemented)</small>

Reset the stats returned by INFO

#### [CONFIG REWRITE](https://redis.io/commands/config-rewrite/) <small>(not implemented)</small>

Rewrite the configuration file with the in memory configuration

#### [CONFIG SET](https://redis.io/commands/config-set/) <small>(not implemented)</small>

Set configuration parameters to the given values

#### [DEBUG](https://redis.io/commands/debug/) <small>(not implemented)</small>

A container for debugging commands

#### [FAILOVER](https://redis.io/commands/failover/) <small>(not implemented)</small>

Start a coordinated failover between this server and one of its replicas.

#### [INFO](https://redis.io/commands/info/) <small>(not implemented)</small>

Get information and statistics about the server

#### [LATENCY](https://redis.io/commands/latency/) <small>(not implemented)</small>

A container for latency diagnostics commands

#### [LATENCY DOCTOR](https://redis.io/commands/latency-doctor/) <small>(not implemented)</small>

Return a human readable latency analysis report.

#### [LATENCY GRAPH](https://redis.io/commands/latency-graph/) <small>(not implemented)</small>

Return a latency graph for the event.

#### [LATENCY HELP](https://redis.io/commands/latency-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands.

#### [LATENCY HISTOGRAM](https://redis.io/commands/latency-histogram/) <small>(not implemented)</small>

Return the cumulative distribution of latencies of a subset of commands or all.

#### [LATENCY HISTORY](https://redis.io/commands/latency-history/) <small>(not implemented)</small>

Return timestamp-latency samples for the event.

#### [LATENCY LATEST](https://redis.io/commands/latency-latest/) <small>(not implemented)</small>

Return the latest latency samples for all events.

#### [LATENCY RESET](https://redis.io/commands/latency-reset/) <small>(not implemented)</small>

Reset latency data for one or more events.

#### [LOLWUT](https://redis.io/commands/lolwut/) <small>(not implemented)</small>

Display some computer art and the Redis version

#### [MEMORY](https://redis.io/commands/memory/) <small>(not implemented)</small>

A container for memory diagnostics commands

#### [MEMORY DOCTOR](https://redis.io/commands/memory-doctor/) <small>(not implemented)</small>

Outputs memory problems report

#### [MEMORY HELP](https://redis.io/commands/memory-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [MEMORY MALLOC-STATS](https://redis.io/commands/memory-malloc-stats/) <small>(not implemented)</small>

Show allocator internal stats

#### [MEMORY PURGE](https://redis.io/commands/memory-purge/) <small>(not implemented)</small>

Ask the allocator to release memory

#### [MEMORY STATS](https://redis.io/commands/memory-stats/) <small>(not implemented)</small>

Show memory usage details

#### [MEMORY USAGE](https://redis.io/commands/memory-usage/) <small>(not implemented)</small>

Estimate the memory usage of a key

#### [MODULE](https://redis.io/commands/module/) <small>(not implemented)</small>

A container for module commands

#### [MODULE HELP](https://redis.io/commands/module-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [MODULE LIST](https://redis.io/commands/module-list/) <small>(not implemented)</small>

List all modules loaded by the server

#### [MODULE LOAD](https://redis.io/commands/module-load/) <small>(not implemented)</small>

Load a module

#### [MODULE LOADEX](https://redis.io/commands/module-loadex/) <small>(not implemented)</small>

Load a module with extended parameters

#### [MODULE UNLOAD](https://redis.io/commands/module-unload/) <small>(not implemented)</small>

Unload a module

#### [MONITOR](https://redis.io/commands/monitor/) <small>(not implemented)</small>

Listen for all requests received by the server in real time

#### [PSYNC](https://redis.io/commands/psync/) <small>(not implemented)</small>

Internal command used for replication

#### [REPLCONF](https://redis.io/commands/replconf/) <small>(not implemented)</small>

An internal command for configuring the replication stream

#### [REPLICAOF](https://redis.io/commands/replicaof/) <small>(not implemented)</small>

Make the server a replica of another instance, or promote it as master.

#### [RESTORE-ASKING](https://redis.io/commands/restore-asking/) <small>(not implemented)</small>

An internal command for migrating keys in a cluster

#### [ROLE](https://redis.io/commands/role/) <small>(not implemented)</small>

Return the role of the instance in the context of replication

#### [SHUTDOWN](https://redis.io/commands/shutdown/) <small>(not implemented)</small>

Synchronously save the dataset to disk and then shut down the server

#### [SLAVEOF](https://redis.io/commands/slaveof/) <small>(not implemented)</small>

Make the server a replica of another instance, or promote it as master.

#### [SLOWLOG](https://redis.io/commands/slowlog/) <small>(not implemented)</small>

A container for slow log commands

#### [SLOWLOG GET](https://redis.io/commands/slowlog-get/) <small>(not implemented)</small>

Get the slow log's entries

#### [SLOWLOG HELP](https://redis.io/commands/slowlog-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [SLOWLOG LEN](https://redis.io/commands/slowlog-len/) <small>(not implemented)</small>

Get the slow log's length

#### [SLOWLOG RESET](https://redis.io/commands/slowlog-reset/) <small>(not implemented)</small>

Clear all entries from the slow log

#### [SYNC](https://redis.io/commands/sync/) <small>(not implemented)</small>

Internal command used for replication


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


### Unsupported string commands 
> To implement support for a command, see [here](/guides/implement-command/) 



### Unsupported cluster commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [ASKING](https://redis.io/commands/asking/) <small>(not implemented)</small>

Sent by cluster clients after an -ASK redirect

#### [CLUSTER](https://redis.io/commands/cluster/) <small>(not implemented)</small>

A container for cluster commands

#### [CLUSTER ADDSLOTS](https://redis.io/commands/cluster-addslots/) <small>(not implemented)</small>

Assign new hash slots to receiving node

#### [CLUSTER ADDSLOTSRANGE](https://redis.io/commands/cluster-addslotsrange/) <small>(not implemented)</small>

Assign new hash slots to receiving node

#### [CLUSTER BUMPEPOCH](https://redis.io/commands/cluster-bumpepoch/) <small>(not implemented)</small>

Advance the cluster config epoch

#### [CLUSTER COUNT-FAILURE-REPORTS](https://redis.io/commands/cluster-count-failure-reports/) <small>(not implemented)</small>

Return the number of failure reports active for a given node

#### [CLUSTER COUNTKEYSINSLOT](https://redis.io/commands/cluster-countkeysinslot/) <small>(not implemented)</small>

Return the number of local keys in the specified hash slot

#### [CLUSTER DELSLOTS](https://redis.io/commands/cluster-delslots/) <small>(not implemented)</small>

Set hash slots as unbound in receiving node

#### [CLUSTER DELSLOTSRANGE](https://redis.io/commands/cluster-delslotsrange/) <small>(not implemented)</small>

Set hash slots as unbound in receiving node

#### [CLUSTER FAILOVER](https://redis.io/commands/cluster-failover/) <small>(not implemented)</small>

Forces a replica to perform a manual failover of its master.

#### [CLUSTER FLUSHSLOTS](https://redis.io/commands/cluster-flushslots/) <small>(not implemented)</small>

Delete a node's own slots information

#### [CLUSTER FORGET](https://redis.io/commands/cluster-forget/) <small>(not implemented)</small>

Remove a node from the nodes table

#### [CLUSTER GETKEYSINSLOT](https://redis.io/commands/cluster-getkeysinslot/) <small>(not implemented)</small>

Return local key names in the specified hash slot

#### [CLUSTER HELP](https://redis.io/commands/cluster-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [CLUSTER INFO](https://redis.io/commands/cluster-info/) <small>(not implemented)</small>

Provides info about Redis Cluster node state

#### [CLUSTER KEYSLOT](https://redis.io/commands/cluster-keyslot/) <small>(not implemented)</small>

Returns the hash slot of the specified key

#### [CLUSTER LINKS](https://redis.io/commands/cluster-links/) <small>(not implemented)</small>

Returns a list of all TCP links to and from peer nodes in cluster

#### [CLUSTER MEET](https://redis.io/commands/cluster-meet/) <small>(not implemented)</small>

Force a node cluster to handshake with another node

#### [CLUSTER MYID](https://redis.io/commands/cluster-myid/) <small>(not implemented)</small>

Return the node id

#### [CLUSTER NODES](https://redis.io/commands/cluster-nodes/) <small>(not implemented)</small>

Get Cluster config for the node

#### [CLUSTER REPLICAS](https://redis.io/commands/cluster-replicas/) <small>(not implemented)</small>

List replica nodes of the specified master node

#### [CLUSTER REPLICATE](https://redis.io/commands/cluster-replicate/) <small>(not implemented)</small>

Reconfigure a node as a replica of the specified master node

#### [CLUSTER RESET](https://redis.io/commands/cluster-reset/) <small>(not implemented)</small>

Reset a Redis Cluster node

#### [CLUSTER SAVECONFIG](https://redis.io/commands/cluster-saveconfig/) <small>(not implemented)</small>

Forces the node to save cluster state on disk

#### [CLUSTER SET-CONFIG-EPOCH](https://redis.io/commands/cluster-set-config-epoch/) <small>(not implemented)</small>

Set the configuration epoch in a new node

#### [CLUSTER SETSLOT](https://redis.io/commands/cluster-setslot/) <small>(not implemented)</small>

Bind a hash slot to a specific node

#### [CLUSTER SHARDS](https://redis.io/commands/cluster-shards/) <small>(not implemented)</small>

Get array of cluster slots to node mappings

#### [CLUSTER SLAVES](https://redis.io/commands/cluster-slaves/) <small>(not implemented)</small>

List replica nodes of the specified master node

#### [CLUSTER SLOTS](https://redis.io/commands/cluster-slots/) <small>(not implemented)</small>

Get array of Cluster slot to node mappings

#### [READONLY](https://redis.io/commands/readonly/) <small>(not implemented)</small>

Enables read queries for a connection to a cluster replica node

#### [READWRITE](https://redis.io/commands/readwrite/) <small>(not implemented)</small>

Disables read queries for a connection to a cluster replica node


## connection commands

### [ECHO](https://redis.io/commands/echo/)

Echo the given string

### [PING](https://redis.io/commands/ping/)

Ping the server

### [SELECT](https://redis.io/commands/select/)

Change the selected database for the current connection


### Unsupported connection commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [AUTH](https://redis.io/commands/auth/) <small>(not implemented)</small>

Authenticate to the server

#### [CLIENT](https://redis.io/commands/client/) <small>(not implemented)</small>

A container for client connection commands

#### [CLIENT CACHING](https://redis.io/commands/client-caching/) <small>(not implemented)</small>

Instruct the server about tracking or not keys in the next request

#### [CLIENT GETNAME](https://redis.io/commands/client-getname/) <small>(not implemented)</small>

Get the current connection name

#### [CLIENT GETREDIR](https://redis.io/commands/client-getredir/) <small>(not implemented)</small>

Get tracking notifications redirection client ID if any

#### [CLIENT HELP](https://redis.io/commands/client-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [CLIENT ID](https://redis.io/commands/client-id/) <small>(not implemented)</small>

Returns the client ID for the current connection

#### [CLIENT INFO](https://redis.io/commands/client-info/) <small>(not implemented)</small>

Returns information about the current client connection.

#### [CLIENT KILL](https://redis.io/commands/client-kill/) <small>(not implemented)</small>

Kill the connection of a client

#### [CLIENT LIST](https://redis.io/commands/client-list/) <small>(not implemented)</small>

Get the list of client connections

#### [CLIENT NO-EVICT](https://redis.io/commands/client-no-evict/) <small>(not implemented)</small>

Set client eviction mode for the current connection

#### [CLIENT PAUSE](https://redis.io/commands/client-pause/) <small>(not implemented)</small>

Stop processing commands from clients for some time

#### [CLIENT REPLY](https://redis.io/commands/client-reply/) <small>(not implemented)</small>

Instruct the server whether to reply to commands

#### [CLIENT SETNAME](https://redis.io/commands/client-setname/) <small>(not implemented)</small>

Set the current connection name

#### [CLIENT TRACKING](https://redis.io/commands/client-tracking/) <small>(not implemented)</small>

Enable or disable server assisted client side caching support

#### [CLIENT TRACKINGINFO](https://redis.io/commands/client-trackinginfo/) <small>(not implemented)</small>

Return information about server assisted client side caching for the current connection

#### [CLIENT UNBLOCK](https://redis.io/commands/client-unblock/) <small>(not implemented)</small>

Unblock a client blocked in a blocking command from a different connection

#### [CLIENT UNPAUSE](https://redis.io/commands/client-unpause/) <small>(not implemented)</small>

Resume processing of clients that were paused

#### [HELLO](https://redis.io/commands/hello/) <small>(not implemented)</small>

Handshake with Redis

#### [QUIT](https://redis.io/commands/quit/) <small>(not implemented)</small>

Close the connection

#### [RESET](https://redis.io/commands/reset/) <small>(not implemented)</small>

Reset the connection


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


### Unsupported bitmap commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [BITFIELD](https://redis.io/commands/bitfield/) <small>(not implemented)</small>

Perform arbitrary bitfield integer operations on strings

#### [BITFIELD_RO](https://redis.io/commands/bitfield_ro/) <small>(not implemented)</small>

Perform arbitrary bitfield integer operations on strings. Read-only variant of BITFIELD


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


### Unsupported list commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [BLMOVE](https://redis.io/commands/blmove/) <small>(not implemented)</small>

Pop an element from a list, push it to another list and return it; or block until one is available

#### [BLMPOP](https://redis.io/commands/blmpop/) <small>(not implemented)</small>

Pop elements from a list, or block until one is available

#### [LMPOP](https://redis.io/commands/lmpop/) <small>(not implemented)</small>

Pop elements from a list

#### [LPOS](https://redis.io/commands/lpos/) <small>(not implemented)</small>

Return the index of matching elements on a list


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


### Unsupported sorted-set commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [BZMPOP](https://redis.io/commands/bzmpop/) <small>(not implemented)</small>

Remove and return members with scores in a sorted set or block until one is available

#### [ZDIFF](https://redis.io/commands/zdiff/) <small>(not implemented)</small>

Subtract multiple sorted sets

#### [ZDIFFSTORE](https://redis.io/commands/zdiffstore/) <small>(not implemented)</small>

Subtract multiple sorted sets and store the resulting sorted set in a new key

#### [ZINTER](https://redis.io/commands/zinter/) <small>(not implemented)</small>

Intersect multiple sorted sets

#### [ZINTERCARD](https://redis.io/commands/zintercard/) <small>(not implemented)</small>

Intersect multiple sorted sets and return the cardinality of the result

#### [ZMPOP](https://redis.io/commands/zmpop/) <small>(not implemented)</small>

Remove and return members with scores in a sorted set

#### [ZRANDMEMBER](https://redis.io/commands/zrandmember/) <small>(not implemented)</small>

Get one or multiple random elements from a sorted set

#### [ZRANGESTORE](https://redis.io/commands/zrangestore/) <small>(not implemented)</small>

Store a range of members from sorted set into another key

#### [ZUNION](https://redis.io/commands/zunion/) <small>(not implemented)</small>

Add multiple sorted sets


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


### Unsupported generic commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [COPY](https://redis.io/commands/copy/) <small>(not implemented)</small>

Copy a key

#### [EXPIRETIME](https://redis.io/commands/expiretime/) <small>(not implemented)</small>

Get the expiration Unix timestamp for a key

#### [MIGRATE](https://redis.io/commands/migrate/) <small>(not implemented)</small>

Atomically transfer a key from a Redis instance to another one.

#### [OBJECT](https://redis.io/commands/object/) <small>(not implemented)</small>

A container for object introspection commands

#### [OBJECT ENCODING](https://redis.io/commands/object-encoding/) <small>(not implemented)</small>

Inspect the internal encoding of a Redis object

#### [OBJECT FREQ](https://redis.io/commands/object-freq/) <small>(not implemented)</small>

Get the logarithmic access frequency counter of a Redis object

#### [OBJECT HELP](https://redis.io/commands/object-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [OBJECT IDLETIME](https://redis.io/commands/object-idletime/) <small>(not implemented)</small>

Get the time since a Redis object was last accessed

#### [OBJECT REFCOUNT](https://redis.io/commands/object-refcount/) <small>(not implemented)</small>

Get the number of references to the value of the key

#### [PEXPIRETIME](https://redis.io/commands/pexpiretime/) <small>(not implemented)</small>

Get the expiration Unix timestamp for a key in milliseconds

#### [SORT_RO](https://redis.io/commands/sort_ro/) <small>(not implemented)</small>

Sort the elements in a list, set or sorted set. Read-only variant of SORT.

#### [TOUCH](https://redis.io/commands/touch/) <small>(not implemented)</small>

Alters the last access time of a key(s). Returns the number of existing keys specified.

#### [WAIT](https://redis.io/commands/wait/) <small>(not implemented)</small>

Wait for the synchronous replication of all the write commands sent in the context of the current connection


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


### Unsupported transactions commands 
> To implement support for a command, see [here](/guides/implement-command/) 


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


### Unsupported scripting commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [EVALSHA_RO](https://redis.io/commands/evalsha_ro/) <small>(not implemented)</small>

Execute a read-only Lua script server side

#### [EVAL_RO](https://redis.io/commands/eval_ro/) <small>(not implemented)</small>

Execute a read-only Lua script server side

#### [FCALL](https://redis.io/commands/fcall/) <small>(not implemented)</small>

Invoke a function

#### [FCALL_RO](https://redis.io/commands/fcall_ro/) <small>(not implemented)</small>

Invoke a read-only function

#### [FUNCTION](https://redis.io/commands/function/) <small>(not implemented)</small>

A container for function commands

#### [FUNCTION DELETE](https://redis.io/commands/function-delete/) <small>(not implemented)</small>

Delete a function by name

#### [FUNCTION DUMP](https://redis.io/commands/function-dump/) <small>(not implemented)</small>

Dump all functions into a serialized binary payload

#### [FUNCTION FLUSH](https://redis.io/commands/function-flush/) <small>(not implemented)</small>

Deleting all functions

#### [FUNCTION HELP](https://redis.io/commands/function-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [FUNCTION KILL](https://redis.io/commands/function-kill/) <small>(not implemented)</small>

Kill the function currently in execution.

#### [FUNCTION LIST](https://redis.io/commands/function-list/) <small>(not implemented)</small>

List information about all the functions

#### [FUNCTION LOAD](https://redis.io/commands/function-load/) <small>(not implemented)</small>

Create a function with the given arguments (name, code, description)

#### [FUNCTION RESTORE](https://redis.io/commands/function-restore/) <small>(not implemented)</small>

Restore all the functions on the given payload

#### [FUNCTION STATS](https://redis.io/commands/function-stats/) <small>(not implemented)</small>

Return information about the function currently running (name, description, duration)

#### [SCRIPT DEBUG](https://redis.io/commands/script-debug/) <small>(not implemented)</small>

Set the debug mode for executed scripts.

#### [SCRIPT KILL](https://redis.io/commands/script-kill/) <small>(not implemented)</small>

Kill the script currently in execution.


## geo commands

### [GEOADD](https://redis.io/commands/geoadd/)

Add one or more geospatial items in the geospatial index represented using a sorted set

### [GEODIST](https://redis.io/commands/geodist/)

Returns the distance between two members of a geospatial index

### [GEOHASH](https://redis.io/commands/geohash/)

Returns members of a geospatial index as standard geohash strings

### [GEOPOS](https://redis.io/commands/geopos/)

Returns longitude and latitude of members of a geospatial index

### [GEORADIUS](https://redis.io/commands/georadius/)

Query a sorted set representing a geospatial index to fetch members matching a given maximum distance from a point

### [GEORADIUSBYMEMBER](https://redis.io/commands/georadiusbymember/)

Query a sorted set representing a geospatial index to fetch members matching a given maximum distance from a member

### [GEORADIUSBYMEMBER_RO](https://redis.io/commands/georadiusbymember_ro/)

A read-only variant for GEORADIUSBYMEMBER

### [GEORADIUS_RO](https://redis.io/commands/georadius_ro/)

A read-only variant for GEORADIUS

### [GEOSEARCH](https://redis.io/commands/geosearch/)

Query a sorted set representing a geospatial index to fetch members inside an area of a box or a circle.


### Unsupported geo commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [GEOSEARCHSTORE](https://redis.io/commands/geosearchstore/) <small>(not implemented)</small>

Query a sorted set representing a geospatial index to fetch members inside an area of a box or a circle, and store the result in another key.


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


### Unsupported hash commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [HRANDFIELD](https://redis.io/commands/hrandfield/) <small>(not implemented)</small>

Get one or multiple random fields from a hash


## hyperloglog commands

### [PFADD](https://redis.io/commands/pfadd/)

Adds the specified elements to the specified HyperLogLog.

### [PFCOUNT](https://redis.io/commands/pfcount/)

Return the approximated cardinality of the set(s) observed by the HyperLogLog at key(s).

### [PFMERGE](https://redis.io/commands/pfmerge/)

Merge N different HyperLogLogs into a single one.


### Unsupported hyperloglog commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [PFDEBUG](https://redis.io/commands/pfdebug/) <small>(not implemented)</small>

Internal commands for debugging HyperLogLog values

#### [PFSELFTEST](https://redis.io/commands/pfselftest/) <small>(not implemented)</small>

An internal command for testing HyperLogLog values


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


### Unsupported pubsub commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [PUBSUB NUMPAT](https://redis.io/commands/pubsub-numpat/) <small>(not implemented)</small>

Get the count of unique patterns pattern subscriptions

#### [PUBSUB SHARDCHANNELS](https://redis.io/commands/pubsub-shardchannels/) <small>(not implemented)</small>

List active shard channels

#### [PUBSUB SHARDNUMSUB](https://redis.io/commands/pubsub-shardnumsub/) <small>(not implemented)</small>

Get the count of subscribers for shard channels

#### [SPUBLISH](https://redis.io/commands/spublish/) <small>(not implemented)</small>

Post a message to a shard channel

#### [SSUBSCRIBE](https://redis.io/commands/ssubscribe/) <small>(not implemented)</small>

Listen for messages published to the given shard channels

#### [SUNSUBSCRIBE](https://redis.io/commands/sunsubscribe/) <small>(not implemented)</small>

Stop listening for messages posted to the given shard channels


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


### Unsupported set commands 
> To implement support for a command, see [here](/guides/implement-command/) 


## stream commands

### [XADD](https://redis.io/commands/xadd/)

Appends a new entry to a stream

### [XLEN](https://redis.io/commands/xlen/)

Return the number of entries in a stream

### [XRANGE](https://redis.io/commands/xrange/)

Return a range of elements in a stream, with IDs matching the specified IDs interval

### [XREVRANGE](https://redis.io/commands/xrevrange/)

Return a range of elements in a stream, with IDs matching the specified IDs interval, in reverse order (from greater to smaller IDs) compared to XRANGE

### [XTRIM](https://redis.io/commands/xtrim/)

Trims the stream to (approximately if '~' is passed) a certain size


### Unsupported stream commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [XACK](https://redis.io/commands/xack/) <small>(not implemented)</small>

Marks a pending message as correctly processed, effectively removing it from the pending entries list of the consumer group. Return value of the command is the number of messages successfully acknowledged, that is, the IDs we were actually able to resolve in the PEL.

#### [XAUTOCLAIM](https://redis.io/commands/xautoclaim/) <small>(not implemented)</small>

Changes (or acquires) ownership of messages in a consumer group, as if the messages were delivered to the specified consumer.

#### [XCLAIM](https://redis.io/commands/xclaim/) <small>(not implemented)</small>

Changes (or acquires) ownership of a message in a consumer group, as if the message was delivered to the specified consumer.

#### [XDEL](https://redis.io/commands/xdel/) <small>(not implemented)</small>

Removes the specified entries from the stream. Returns the number of items actually deleted, that may be different from the number of IDs passed in case certain IDs do not exist.

#### [XGROUP](https://redis.io/commands/xgroup/) <small>(not implemented)</small>

A container for consumer groups commands

#### [XGROUP CREATE](https://redis.io/commands/xgroup-create/) <small>(not implemented)</small>

Create a consumer group.

#### [XGROUP CREATECONSUMER](https://redis.io/commands/xgroup-createconsumer/) <small>(not implemented)</small>

Create a consumer in a consumer group.

#### [XGROUP DELCONSUMER](https://redis.io/commands/xgroup-delconsumer/) <small>(not implemented)</small>

Delete a consumer from a consumer group.

#### [XGROUP DESTROY](https://redis.io/commands/xgroup-destroy/) <small>(not implemented)</small>

Destroy a consumer group.

#### [XGROUP HELP](https://redis.io/commands/xgroup-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [XGROUP SETID](https://redis.io/commands/xgroup-setid/) <small>(not implemented)</small>

Set a consumer group to an arbitrary last delivered ID value.

#### [XINFO](https://redis.io/commands/xinfo/) <small>(not implemented)</small>

A container for stream introspection commands

#### [XINFO CONSUMERS](https://redis.io/commands/xinfo-consumers/) <small>(not implemented)</small>

List the consumers in a consumer group

#### [XINFO GROUPS](https://redis.io/commands/xinfo-groups/) <small>(not implemented)</small>

List the consumer groups of a stream

#### [XINFO HELP](https://redis.io/commands/xinfo-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [XINFO STREAM](https://redis.io/commands/xinfo-stream/) <small>(not implemented)</small>

Get information about a stream

#### [XPENDING](https://redis.io/commands/xpending/) <small>(not implemented)</small>

Return information and entries from a stream consumer group pending entries list, that are messages fetched but never acknowledged.

#### [XREAD](https://redis.io/commands/xread/) <small>(not implemented)</small>

Return never seen elements in multiple streams, with IDs greater than the ones reported by the caller for each stream. Can block.

#### [XREADGROUP](https://redis.io/commands/xreadgroup/) <small>(not implemented)</small>

Return new entries from a stream using a consumer group, or access the history of the pending entries for a given consumer. Can block.

#### [XSETID](https://redis.io/commands/xsetid/) <small>(not implemented)</small>

An internal command for replicating stream values


