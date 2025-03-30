# Redis `server` commands (23/70 implemented)

## [ACL CAT](https://redis.io/commands/acl-cat/)

Lists the ACL categories, or the commands inside a category.

## [ACL DELUSER](https://redis.io/commands/acl-deluser/)

Deletes ACL users, and terminates their connections.

## [ACL GENPASS](https://redis.io/commands/acl-genpass/)

Generates a pseudorandom, secure password that can be used to identify ACL users.

## [ACL GETUSER](https://redis.io/commands/acl-getuser/)

Lists the ACL rules of a user.

## [ACL LIST](https://redis.io/commands/acl-list/)

Dumps the effective rules in ACL file format.

## [ACL LOAD](https://redis.io/commands/acl-load/)

Reloads the rules from the configured ACL file.

## [ACL LOG](https://redis.io/commands/acl-log/)

Lists recent security events generated due to ACL rules.

## [ACL SAVE](https://redis.io/commands/acl-save/)

Saves the effective ACL rules in the configured ACL file.

## [ACL SETUSER](https://redis.io/commands/acl-setuser/)

Creates and modifies an ACL user and its rules.

## [ACL USERS](https://redis.io/commands/acl-users/)

Lists all ACL users.

## [ACL WHOAMI](https://redis.io/commands/acl-whoami/)

Returns the authenticated username of the current connection.

## [BGSAVE](https://redis.io/commands/bgsave/)

Asynchronously saves the database(s) to disk.

## [COMMAND](https://redis.io/commands/command/)

Returns detailed information about all commands.

## [COMMAND COUNT](https://redis.io/commands/command-count/)

Returns a count of commands.

## [COMMAND INFO](https://redis.io/commands/command-info/)

Returns information about one, multiple or all commands.

## [CONFIG SET](https://redis.io/commands/config-set/)

Sets configuration parameters in-flight.

## [DBSIZE](https://redis.io/commands/dbsize/)

Returns the number of keys in the database.

## [FLUSHALL](https://redis.io/commands/flushall/)

Removes all keys from all databases.

## [FLUSHDB](https://redis.io/commands/flushdb/)

Remove all keys from the current database.

## [LASTSAVE](https://redis.io/commands/lastsave/)

Returns the Unix timestamp of the last successful save to disk.

## [SAVE](https://redis.io/commands/save/)

Synchronously saves the database(s) to disk.

## [SWAPDB](https://redis.io/commands/swapdb/)

Swaps two Redis databases.

## [TIME](https://redis.io/commands/time/)

Returns the server time.


## Unsupported server commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [LATENCY LATEST](https://redis.io/commands/latency-latest/) <small>(not implemented)</small>

Returns the latest latency samples for all events.

#### [PSYNC](https://redis.io/commands/psync/) <small>(not implemented)</small>

An internal command used in replication.

#### [REPLCONF](https://redis.io/commands/replconf/) <small>(not implemented)</small>

An internal command for configuring the replication stream.

#### [SLOWLOG](https://redis.io/commands/slowlog/) <small>(not implemented)</small>

A container for slow log commands.

#### [LATENCY](https://redis.io/commands/latency/) <small>(not implemented)</small>

A container for latency diagnostics commands.

#### [MEMORY DOCTOR](https://redis.io/commands/memory-doctor/) <small>(not implemented)</small>

Outputs a memory problems report.

#### [LATENCY HISTORY](https://redis.io/commands/latency-history/) <small>(not implemented)</small>

Returns timestamp-latency samples for an event.

#### [MEMORY MALLOC-STATS](https://redis.io/commands/memory-malloc-stats/) <small>(not implemented)</small>

Returns the allocator statistics.

#### [MEMORY](https://redis.io/commands/memory/) <small>(not implemented)</small>

A container for memory diagnostics commands.

#### [ROLE](https://redis.io/commands/role/) <small>(not implemented)</small>

Returns the replication role.

#### [MODULE](https://redis.io/commands/module/) <small>(not implemented)</small>

A container for module commands.

#### [SLOWLOG HELP](https://redis.io/commands/slowlog-help/) <small>(not implemented)</small>

Show helpful text about the different subcommands

#### [COMMAND GETKEYS](https://redis.io/commands/command-getkeys/) <small>(not implemented)</small>

Extracts the key names from an arbitrary command.

#### [LOLWUT](https://redis.io/commands/lolwut/) <small>(not implemented)</small>

Displays computer art and the Redis version

#### [CONFIG REWRITE](https://redis.io/commands/config-rewrite/) <small>(not implemented)</small>

Persists the effective configuration to file.

#### [INFO](https://redis.io/commands/info/) <small>(not implemented)</small>

Returns information and statistics about the server.

#### [BGREWRITEAOF](https://redis.io/commands/bgrewriteaof/) <small>(not implemented)</small>

Asynchronously rewrites the append-only file to disk.

#### [LATENCY RESET](https://redis.io/commands/latency-reset/) <small>(not implemented)</small>

Resets the latency data for one or more events.

#### [MEMORY PURGE](https://redis.io/commands/memory-purge/) <small>(not implemented)</small>

Asks the allocator to release memory.

#### [MEMORY USAGE](https://redis.io/commands/memory-usage/) <small>(not implemented)</small>

Estimates the memory usage of a key.

#### [MODULE LOAD](https://redis.io/commands/module-load/) <small>(not implemented)</small>

Loads a module.

#### [SLOWLOG LEN](https://redis.io/commands/slowlog-len/) <small>(not implemented)</small>

Returns the number of entries in the slow log.

#### [CONFIG RESETSTAT](https://redis.io/commands/config-resetstat/) <small>(not implemented)</small>

Resets the server's statistics.

#### [LATENCY HELP](https://redis.io/commands/latency-help/) <small>(not implemented)</small>

Returns helpful text about the different subcommands.

#### [MONITOR](https://redis.io/commands/monitor/) <small>(not implemented)</small>

Listens for all requests received by the server in real-time.

#### [REPLICAOF](https://redis.io/commands/replicaof/) <small>(not implemented)</small>

Configures a server as replica of another, or promotes it to a master.

#### [CONFIG GET](https://redis.io/commands/config-get/) <small>(not implemented)</small>

Returns the effective values of configuration parameters.

#### [CONFIG](https://redis.io/commands/config/) <small>(not implemented)</small>

A container for server configuration commands.

#### [COMMAND DOCS](https://redis.io/commands/command-docs/) <small>(not implemented)</small>

Returns documentary information about one, multiple or all commands.

#### [MODULE LIST](https://redis.io/commands/module-list/) <small>(not implemented)</small>

Returns all loaded modules.

#### [ACL DRYRUN](https://redis.io/commands/acl-dryrun/) <small>(not implemented)</small>

Simulates the execution of a command by a user, without executing the command.

#### [FAILOVER](https://redis.io/commands/failover/) <small>(not implemented)</small>

Starts a coordinated failover from a server to one of its replicas.

#### [LATENCY GRAPH](https://redis.io/commands/latency-graph/) <small>(not implemented)</small>

Returns a latency graph for an event.

#### [MEMORY STATS](https://redis.io/commands/memory-stats/) <small>(not implemented)</small>

Returns details about memory usage.

#### [RESTORE-ASKING](https://redis.io/commands/restore-asking/) <small>(not implemented)</small>

An internal command for migrating keys in a cluster.

#### [ACL](https://redis.io/commands/acl/) <small>(not implemented)</small>

A container for Access List Control commands.

#### [COMMAND LIST](https://redis.io/commands/command-list/) <small>(not implemented)</small>

Returns a list of command names.

#### [SYNC](https://redis.io/commands/sync/) <small>(not implemented)</small>

An internal command used in replication.

#### [LATENCY HISTOGRAM](https://redis.io/commands/latency-histogram/) <small>(not implemented)</small>

Returns the cumulative distribution of latencies of a subset or all commands.

#### [MODULE LOADEX](https://redis.io/commands/module-loadex/) <small>(not implemented)</small>

Loads a module using extended parameters.

#### [SLOWLOG RESET](https://redis.io/commands/slowlog-reset/) <small>(not implemented)</small>

Clears all entries from the slow log.

#### [LATENCY DOCTOR](https://redis.io/commands/latency-doctor/) <small>(not implemented)</small>

Returns a human-readable latency analysis report.

#### [COMMAND GETKEYSANDFLAGS](https://redis.io/commands/command-getkeysandflags/) <small>(not implemented)</small>

Extracts the key names and access flags for an arbitrary command.

#### [MODULE UNLOAD](https://redis.io/commands/module-unload/) <small>(not implemented)</small>

Unloads a module.

#### [SLAVEOF](https://redis.io/commands/slaveof/) <small>(not implemented)</small>

Sets a Redis server as a replica of another, or promotes it to being a master.

#### [SLOWLOG GET](https://redis.io/commands/slowlog-get/) <small>(not implemented)</small>

Returns the slow log's entries.

#### [SHUTDOWN](https://redis.io/commands/shutdown/) <small>(not implemented)</small>

Synchronously saves the database(s) to disk and shuts down the Redis server.


