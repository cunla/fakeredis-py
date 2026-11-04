# RedisJson `json` commands (23/23 implemented)

## [JSON.ARRAPPEND](https://redis.io/commands/json.arrappend/)

Append the JSON values into the array at path after the last element in it

## [JSON.ARRINDEX](https://redis.io/commands/json.arrindex/)

Search for the first occurrence of a JSON value in an array

## [JSON.ARRINSERT](https://redis.io/commands/json.arrinsert/)

Insert the json values into the array at path before the index (shifts to the right)

## [JSON.ARRLEN](https://redis.io/commands/json.arrlen/)

Report the length of the JSON array at path in key

## [JSON.ARRPOP](https://redis.io/commands/json.arrpop/)

Remove and return the element at the specified index in the array at path

## [JSON.ARRTRIM](https://redis.io/commands/json.arrtrim/)

Trim an array so that it contains only the specified inclusive range of elements

## [JSON.CLEAR](https://redis.io/commands/json.clear/)

Clear container values (arrays/objects) and set numeric values to 0

## [JSON.DEL](https://redis.io/commands/json.del/)

Delete a value

## [JSON.FORGET](https://redis.io/commands/json.forget/)

Delete a value

## [JSON.GET](https://redis.io/commands/json.get/)

Get JSON value at path

## [JSON.MERGE](https://redis.io/commands/json.merge/)

Merge a given JSON value into matching paths. Consequently, JSON values at matching paths are updated, deleted, or expanded with new children

## [JSON.MGET](https://redis.io/commands/json.mget/)

Return the values at path from multiple key arguments

## [JSON.MSET](https://redis.io/commands/json.mset/)

Set or update one or more JSON values according to the specified key-path-value triplets

## [JSON.NUMINCRBY](https://redis.io/commands/json.numincrby/)

Increment the number value stored at path by number

## [JSON.NUMMULTBY](https://redis.io/commands/json.nummultby/)

Multiply the number value stored at path by number

## [JSON.NUMPOWBY](https://redis.io/commands/json.numpowby/)

Raise the number value stored at path to the power of number

## [JSON.OBJKEYS](https://redis.io/commands/json.objkeys/)

Return the keys in the object that's referenced by path

## [JSON.OBJLEN](https://redis.io/commands/json.objlen/)

Report the number of keys in the JSON object at path in key

## [JSON.SET](https://redis.io/commands/json.set/)

Set the JSON value at path in key

## [JSON.STRAPPEND](https://redis.io/commands/json.strappend/)

Append the json-string values to the string at path

## [JSON.STRLEN](https://redis.io/commands/json.strlen/)

Report the length of the JSON String at path in key

## [JSON.TOGGLE](https://redis.io/commands/json.toggle/)

Toggle the boolean value stored at path

## [JSON.TYPE](https://redis.io/commands/json.type/)

Report the type of JSON value at path



