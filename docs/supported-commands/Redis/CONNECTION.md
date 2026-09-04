# Redis `connection` commands (19/24 implemented)

## [AUTH](https://redis.io/commands/auth/)

Authenticates the connection.

## [CLIENT GETNAME](https://redis.io/commands/client-getname/)

Returns the name of the connection.

## [CLIENT ID](https://redis.io/commands/client-id/)

Returns the unique client ID of the connection.

## [CLIENT INFO](https://redis.io/commands/client-info/)

Returns information about the connection.

## [CLIENT KILL](https://redis.io/commands/client-kill/)

Terminates open connections.

## [CLIENT LIST](https://redis.io/commands/client-list/)

Lists open connections.

## [CLIENT NO-EVICT](https://redis.io/commands/client-no-evict/)

Sets the client eviction mode of the connection.

## [CLIENT NO-TOUCH](https://redis.io/commands/client-no-touch/)

Controls whether commands sent by the client affect the LRU/LFU of accessed keys.

## [CLIENT PAUSE](https://redis.io/commands/client-pause/)

Suspends commands processing.

## [CLIENT REPLY](https://redis.io/commands/client-reply/)

Instructs the server whether to reply to commands.

## [CLIENT SETINFO](https://redis.io/commands/client-setinfo/)

Sets information specific to the client or connection.

## [CLIENT SETNAME](https://redis.io/commands/client-setname/)

Sets the connection name.

## [CLIENT UNBLOCK](https://redis.io/commands/client-unblock/)

Unblocks a client blocked by a blocking command from a different connection.

## [CLIENT UNPAUSE](https://redis.io/commands/client-unpause/)

Resumes processing commands from paused clients.

## [ECHO](https://redis.io/commands/echo/)

Returns the given string.

## [HELLO](https://redis.io/commands/hello/)

Handshakes with the Redis server.

## [PING](https://redis.io/commands/ping/)

Returns the server's liveliness response.

## [RESET](https://redis.io/commands/reset/)

Resets the connection.

## [SELECT](https://redis.io/commands/select/)

Changes the selected database.


## Unsupported connection commands
> To implement support for a command, see [here](../../../guides/implement-command/)

#### [CLIENT](https://redis.io/commands/client/) <small>(not implemented)</small>

A container for client connection commands.

#### [CLIENT CACHING](https://redis.io/commands/client-caching/) <small>(not implemented)</small>

Instructs the server whether to track the keys in the next request.

#### [CLIENT GETREDIR](https://redis.io/commands/client-getredir/) <small>(not implemented)</small>

Returns the client ID to which the connection's tracking notifications are redirected.

#### [CLIENT TRACKING](https://redis.io/commands/client-tracking/) <small>(not implemented)</small>

Controls server-assisted client-side caching for the connection.

#### [CLIENT TRACKINGINFO](https://redis.io/commands/client-trackinginfo/) <small>(not implemented)</small>

Returns information about server-assisted client-side caching for the connection.
