# Redis `scripting` commands (7/22 implemented)

## [EVAL](https://redis.io/commands/eval/)

Executes a server-side Lua script.

## [EVALSHA](https://redis.io/commands/evalsha/)

Executes a server-side Lua script by SHA1 digest.

## [SCRIPT](https://redis.io/commands/script/)

A container for Lua scripts management commands.

## [SCRIPT EXISTS](https://redis.io/commands/script-exists/)

Determines whether server-side Lua scripts exist in the script cache.

## [SCRIPT FLUSH](https://redis.io/commands/script-flush/)

Removes all server-side Lua scripts from the script cache.

## [SCRIPT HELP](https://redis.io/commands/script-help/)

Returns helpful text about the different subcommands.

## [SCRIPT LOAD](https://redis.io/commands/script-load/)

Loads a server-side Lua script to the script cache.


## Unsupported scripting commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [FCALL](https://redis.io/commands/fcall/) <small>(not implemented)</small>

Invokes a function.

#### [FUNCTION LIST](https://redis.io/commands/function-list/) <small>(not implemented)</small>

Returns information about all libraries.

#### [SCRIPT KILL](https://redis.io/commands/script-kill/) <small>(not implemented)</small>

Terminates a server-side Lua script during execution.

#### [FUNCTION STATS](https://redis.io/commands/function-stats/) <small>(not implemented)</small>

Returns information about a function during execution.

#### [FUNCTION FLUSH](https://redis.io/commands/function-flush/) <small>(not implemented)</small>

Deletes all libraries and functions.

#### [FCALL_RO](https://redis.io/commands/fcall_ro/) <small>(not implemented)</small>

Invokes a read-only function.

#### [FUNCTION DELETE](https://redis.io/commands/function-delete/) <small>(not implemented)</small>

Deletes a library and its functions.

#### [EVAL_RO](https://redis.io/commands/eval_ro/) <small>(not implemented)</small>

Executes a read-only server-side Lua script.

#### [SCRIPT DEBUG](https://redis.io/commands/script-debug/) <small>(not implemented)</small>

Sets the debug mode of server-side Lua scripts.

#### [FUNCTION RESTORE](https://redis.io/commands/function-restore/) <small>(not implemented)</small>

Restores all libraries from a payload.

#### [EVALSHA_RO](https://redis.io/commands/evalsha_ro/) <small>(not implemented)</small>

Executes a read-only server-side Lua script by SHA1 digest.

#### [FUNCTION KILL](https://redis.io/commands/function-kill/) <small>(not implemented)</small>

Terminates a function during execution.

#### [FUNCTION DUMP](https://redis.io/commands/function-dump/) <small>(not implemented)</small>

Dumps all libraries into a serialized binary payload.

#### [FUNCTION LOAD](https://redis.io/commands/function-load/) <small>(not implemented)</small>

Creates a library.

#### [FUNCTION](https://redis.io/commands/function/) <small>(not implemented)</small>

A container for function commands.


