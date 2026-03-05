# Redis `vector_set` commands (9/12 implemented)

## [VADD](https://redis.io/commands/vadd/)

Add a new element to a vector set, or update its vector if it already exists.

## [VCARD](https://redis.io/commands/vcard/)

Return the number of elements in a vector set.

## [VDIM](https://redis.io/commands/vdim/)

Return the dimension of vectors in the vector set.

## [VEMB](https://redis.io/commands/vemb/)

Return the vector associated with an element.

## [VGETATTR](https://redis.io/commands/vgetattr/)

Retrieve the JSON attributes of elements.

## [VRANDMEMBER](https://redis.io/commands/vrandmember/)

Return one or multiple random members from a vector set.

## [VRANGE](https://redis.io/commands/vrange/)

Return elements in a lexicographical range

## [VREM](https://redis.io/commands/vrem/)

Remove an element from a vector set.

## [VSETATTR](https://redis.io/commands/vsetattr/)

Associate or remove the JSON attributes of elements.


## Unsupported vector_set commands
> To implement support for a command, see [here](/guides/implement-command/)

#### [VINFO](https://redis.io/commands/vinfo/) <small>(not implemented)</small>

Return information about a vector set.

#### [VLINKS](https://redis.io/commands/vlinks/) <small>(not implemented)</small>

Return the neighbors of an element at each layer in the HNSW graph.

#### [VSIM](https://redis.io/commands/vsim/) <small>(not implemented)</small>

Return elements by vector similarity.
