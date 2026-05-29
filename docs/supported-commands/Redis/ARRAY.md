# Redis `array` commands (18/18 implemented)

## [ARCOUNT](https://redis.io/commands/arcount/)

Returns the number of non-empty elements in an array.

## [ARDEL](https://redis.io/commands/ardel/)

Deletes elements at the specified indices in an array.

## [ARDELRANGE](https://redis.io/commands/ardelrange/)

Deletes elements in one or more ranges.

## [ARGET](https://redis.io/commands/arget/)

Gets the value at an index in an array.

## [ARGETRANGE](https://redis.io/commands/argetrange/)

Gets values in a range of indices.

## [ARGREP](https://redis.io/commands/argrep/)

Searches array elements in a range using textual predicates.

## [ARINFO](https://redis.io/commands/arinfo/)

Returns metadata about an array.

## [ARINSERT](https://redis.io/commands/arinsert/)

Inserts one or more values at consecutive indices.

## [ARLASTITEMS](https://redis.io/commands/arlastitems/)

Returns the most recently inserted elements.

## [ARLEN](https://redis.io/commands/arlen/)

Returns the length of an array (max index + 1).

## [ARMGET](https://redis.io/commands/armget/)

Gets values at multiple indices in an array.

## [ARMSET](https://redis.io/commands/armset/)

Sets multiple index-value pairs in an array.

## [ARNEXT](https://redis.io/commands/arnext/)

Returns the next index ARINSERT would use.

## [AROP](https://redis.io/commands/arop/)

Performs aggregate operations on array elements in a range.

## [ARRING](https://redis.io/commands/arring/)

Inserts values into a ring buffer of specified size, wrapping and truncating as needed.

## [ARSCAN](https://redis.io/commands/arscan/)

Iterates existing elements in a range, returning index-value pairs.

## [ARSEEK](https://redis.io/commands/arseek/)

Sets the ARINSERT / ARRING cursor to a specific index.

## [ARSET](https://redis.io/commands/arset/)

Sets one or more contiguous values starting at an index in an array.
