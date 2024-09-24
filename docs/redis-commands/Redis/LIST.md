# Redis `list` commands (22/22 implemented)

## [BLMOVE](https://redis.io/commands/blmove/)

Pops an element from a list, pushes it to another list and returns it. Blocks until an element is available otherwise. Deletes the list if the last element was moved.

## [BLMPOP](https://redis.io/commands/blmpop/)

Pops the first element from one of multiple lists. Blocks until an element is available otherwise. Deletes the list if the last element was popped.

## [BLPOP](https://redis.io/commands/blpop/)

Removes and returns the first element in a list. Blocks until an element is available otherwise. Deletes the list if the last element was popped.

## [BRPOP](https://redis.io/commands/brpop/)

Removes and returns the last element in a list. Blocks until an element is available otherwise. Deletes the list if the last element was popped.

## [BRPOPLPUSH](https://redis.io/commands/brpoplpush/)

Pops an element from a list, pushes it to another list and returns it. Block until an element is available otherwise. Deletes the list if the last element was popped.

## [LINDEX](https://redis.io/commands/lindex/)

Returns an element from a list by its index.

## [LINSERT](https://redis.io/commands/linsert/)

Inserts an element before or after another element in a list.

## [LLEN](https://redis.io/commands/llen/)

Returns the length of a list.

## [LMOVE](https://redis.io/commands/lmove/)

Returns an element after popping it from one list and pushing it to another. Deletes the list if the last element was moved.

## [LMPOP](https://redis.io/commands/lmpop/)

Returns multiple elements from a list after removing them. Deletes the list if the last element was popped.

## [LPOP](https://redis.io/commands/lpop/)

Returns the first elements in a list after removing it. Deletes the list if the last element was popped.

## [LPOS](https://redis.io/commands/lpos/)

Returns the index of matching elements in a list.

## [LPUSH](https://redis.io/commands/lpush/)

Prepends one or more elements to a list. Creates the key if it doesn't exist.

## [LPUSHX](https://redis.io/commands/lpushx/)

Prepends one or more elements to a list only when the list exists.

## [LRANGE](https://redis.io/commands/lrange/)

Returns a range of elements from a list.

## [LREM](https://redis.io/commands/lrem/)

Removes elements from a list. Deletes the list if the last element was removed.

## [LSET](https://redis.io/commands/lset/)

Sets the value of an element in a list by its index.

## [LTRIM](https://redis.io/commands/ltrim/)

Removes elements from both ends a list. Deletes the list if all elements were trimmed.

## [RPOP](https://redis.io/commands/rpop/)

Returns and removes the last elements of a list. Deletes the list if the last element was popped.

## [RPOPLPUSH](https://redis.io/commands/rpoplpush/)

Returns the last element of a list after removing and pushing it to another list. Deletes the list if the last element was popped.

## [RPUSH](https://redis.io/commands/rpush/)

Appends one or more elements to a list. Creates the key if it doesn't exist.

## [RPUSHX](https://redis.io/commands/rpushx/)

Appends an element to a list only when the list exists.



