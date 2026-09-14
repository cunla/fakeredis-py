# Redis `scripting` commands (19/23 implemented)

## [EVAL](https://redis.io/commands/eval/)

Executes a server-side Lua script.

## [EVALSHA](https://redis.io/commands/evalsha/)

Executes a server-side Lua script by SHA1 digest.

## [FCALL](https://redis.io/commands/fcall/)

Invokes a function.

## [FCALL_RO](https://redis.io/commands/fcall_ro/)

Invokes a read-only function.

## [FUNCTION](https://redis.io/commands/function/)

A container for function commands.

## [FUNCTION DELETE](https://redis.io/commands/function-delete/)

Deletes a library and its functions.

## [FUNCTION DUMP](https://redis.io/commands/function-dump/)

Dumps all libraries into a serialized binary payload.

## [FUNCTION FLUSH](https://redis.io/commands/function-flush/)

Deletes all libraries and functions.

## [FUNCTION HELP](https://redis.io/commands/function-help/)

Returns helpful text about the different subcommands.

## [FUNCTION KILL](https://redis.io/commands/function-kill/)

Terminates a function during execution.

## [FUNCTION LIST](https://redis.io/commands/function-list/)

Returns information about all libraries.

## [FUNCTION LOAD](https://redis.io/commands/function-load/)

Creates a library.

## [FUNCTION RESTORE](https://redis.io/commands/function-restore/)

Restores all libraries from a payload.

## [FUNCTION STATS](https://redis.io/commands/function-stats/)

Returns information about a function during execution.

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
> To implement support for a command, see [here](../../../guides/implement-command/)

#### [EVAL_RO](https://redis.io/commands/eval_ro/) <small>(not implemented)</small>

Executes a read-only server-side Lua script.

#### [EVALSHA_RO](https://redis.io/commands/evalsha_ro/) <small>(not implemented)</small>

Executes a read-only server-side Lua script by SHA1 digest.

#### [SCRIPT DEBUG](https://redis.io/commands/script-debug/) <small>(not implemented)</small>

Sets the debug mode of server-side Lua scripts.

#### [SCRIPT KILL](https://redis.io/commands/script-kill/) <small>(not implemented)</small>

Terminates a server-side Lua script during execution.
