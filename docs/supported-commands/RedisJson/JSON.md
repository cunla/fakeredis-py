# RedisJson `json` commands (22/22 implemented)

## [JSON.ARRAPPEND](https://redis.io/commands/json.arrappend/)

Append one or more json values into the array at path after the last element in it.

## [JSON.ARRINDEX](https://redis.io/commands/json.arrindex/)

Returns the index of the first occurrence of a JSON scalar value in the array at path

## [JSON.ARRINSERT](https://redis.io/commands/json.arrinsert/)

Inserts the JSON scalar(s) value at the specified index in the array at path

## [JSON.ARRLEN](https://redis.io/commands/json.arrlen/)

Returns the length of the array at path

## [JSON.ARRPOP](https://redis.io/commands/json.arrpop/)

Removes and returns the element at the specified index in the array at path

## [JSON.ARRTRIM](https://redis.io/commands/json.arrtrim/)

Trims the array at path to contain only the specified inclusive range of indices from start to stop

## [JSON.CLEAR](https://redis.io/commands/json.clear/)

Clears all values from an array or an object and sets numeric values to `0`

## [JSON.DEL](https://redis.io/commands/json.del/)

Deletes a value

## [JSON.FORGET](https://redis.io/commands/json.forget/)

Deletes a value

## [JSON.GET](https://redis.io/commands/json.get/)

Gets the value at one or more paths in JSON serialized form

## [JSON.MERGE](https://redis.io/commands/json.merge/)

Merges a given JSON value into matching paths. Consequently, JSON values at matching paths are updated, deleted, or expanded with new children

## [JSON.MGET](https://redis.io/commands/json.mget/)

Returns the values at a path from one or more keys

## [JSON.MSET](https://redis.io/commands/json.mset/)

Sets or updates the JSON value of one or more keys

## [JSON.NUMINCRBY](https://redis.io/commands/json.numincrby/)

Increments the numeric value at path by a value

## [JSON.NUMMULTBY](https://redis.io/commands/json.nummultby/)

Multiplies the numeric value at path by a value

## [JSON.OBJKEYS](https://redis.io/commands/json.objkeys/)

Returns the JSON keys of the object at path

## [JSON.OBJLEN](https://redis.io/commands/json.objlen/)

Returns the number of keys of the object at path

## [JSON.SET](https://redis.io/commands/json.set/)

Sets or updates the JSON value at a path

## [JSON.STRAPPEND](https://redis.io/commands/json.strappend/)

Appends a string to a JSON string value at path

## [JSON.STRLEN](https://redis.io/commands/json.strlen/)

Returns the length of the JSON String at path in key

## [JSON.TOGGLE](https://redis.io/commands/json.toggle/)

Toggles a boolean value

## [JSON.TYPE](https://redis.io/commands/json.type/)

Returns the type of the JSON value at path



