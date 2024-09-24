# `connection` commands (4/25 implemented)

## [CLIENT SETINFO](https://redis.io/commands/client-setinfo/)

Sets information specific to the client or connection.

## [ECHO](https://redis.io/commands/echo/)

Returns the given string.

## [PING](https://redis.io/commands/ping/)

Returns the server's liveliness response.

## [SELECT](https://redis.io/commands/select/)

Changes the selected database.


## Unsupported connection commands 
> To implement support for a command, see [here](/guides/implement-command/) 

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


