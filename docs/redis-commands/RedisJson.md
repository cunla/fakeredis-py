# JSON commands

## json commands

### [JSON.DEL](https://redis.io/commands/json.del/)

Deletes a value

### [JSON.FORGET](https://redis.io/commands/json.forget/)

Deletes a value

### [JSON.GET](https://redis.io/commands/json.get/)

Gets the value at one or more paths in JSON serialized form

### [JSON.TOGGLE](https://redis.io/commands/json.toggle/)

Toggles a boolean value

### [JSON.CLEAR](https://redis.io/commands/json.clear/)

Clears all values from an array or an object and sets numeric values to `0`

### [JSON.SET](https://redis.io/commands/json.set/)

Sets or updates the JSON value at a path

### [JSON.MGET](https://redis.io/commands/json.mget/)

Returns the values at a path from one or more keys

### [JSON.STRAPPEND](https://redis.io/commands/json.strappend/)

Appends a string to a JSON string value at path

### [JSON.STRLEN](https://redis.io/commands/json.strlen/)

Returns the length of the JSON String at path in key

### [JSON.ARRAPPEND](https://redis.io/commands/json.arrappend/)

Append one or more json values into the array at path after the last element in it.

### [JSON.ARRINDEX](https://redis.io/commands/json.arrindex/)

Returns the index of the first occurrence of a JSON scalar value in the array at path

### [JSON.ARRLEN](https://redis.io/commands/json.arrlen/)

Returns the length of the array at path

### [JSON.OBJKEYS](https://redis.io/commands/json.objkeys/)

Returns the JSON keys of the object at path

### [JSON.OBJLEN](https://redis.io/commands/json.objlen/)

Returns the number of keys of the object at path

### [JSON.TYPE](https://redis.io/commands/json.type/)

Returns the type of the JSON value at path


### Unsupported json commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [JSON.NUMINCRBY](https://redis.io/commands/json.numincrby/)

Increments the numeric value at path by a value

#### [JSON.NUMMULTBY](https://redis.io/commands/json.nummultby/)

Multiplies the numeric value at path by a value

#### [JSON.ARRINSERT](https://redis.io/commands/json.arrinsert/)

Inserts the JSON scalar(s) value at the specified index in the array at path

#### [JSON.ARRPOP](https://redis.io/commands/json.arrpop/)

Removes and returns the element at the specified index in the array at path

#### [JSON.ARRTRIM](https://redis.io/commands/json.arrtrim/)

Trims the array at path to contain only the specified inclusive range of indices from start to stop

#### [JSON.RESP](https://redis.io/commands/json.resp/)

Returns the JSON value at path in Redis Serialization Protocol (RESP)

#### [JSON.DEBUG](https://redis.io/commands/json.debug/)

Debugging container command

#### [JSON.DEBUG HELP](https://redis.io/commands/json.debug-help/)

Shows helpful information

#### [JSON.DEBUG MEMORY](https://redis.io/commands/json.debug-memory/)

Reports the size in bytes of a key


