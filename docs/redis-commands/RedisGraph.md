# Graph commands

Module currently not implemented in fakeredis.


### Unsupported graph commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [GRAPH.QUERY](https://redis.io/commands/graph.query/)

Executes the given query against a specified graph

#### [GRAPH.RO_QUERY](https://redis.io/commands/graph.ro_query/)

Executes a given read only query against a specified graph

#### [GRAPH.DELETE](https://redis.io/commands/graph.delete/)

Completely removes the graph and all of its entities

#### [GRAPH.EXPLAIN](https://redis.io/commands/graph.explain/)

Returns a query execution plan without running the query

#### [GRAPH.PROFILE](https://redis.io/commands/graph.profile/)

Executes a query and returns an execution plan augmented with metrics for each operation's execution

#### [GRAPH.SLOWLOG](https://redis.io/commands/graph.slowlog/)

Returns a list containing up to 10 of the slowest queries issued against the given graph

#### [GRAPH.CONFIG GET](https://redis.io/commands/graph.config-get/)

Retrieves a RedisGraph configuration

#### [GRAPH.CONFIG SET](https://redis.io/commands/graph.config-set/)

Updates a RedisGraph configuration

#### [GRAPH.LIST](https://redis.io/commands/graph.list/)

Lists all graph keys in the keyspace


