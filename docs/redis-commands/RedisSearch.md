# Search commands

Module currently not implemented in fakeredis.


### Unsupported search commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [FT.CREATE](https://redis.io/commands/ft.create/)

Creates an index with the given spec

#### [FT.INFO](https://redis.io/commands/ft.info/)

Returns information and statistics on the index

#### [FT.EXPLAIN](https://redis.io/commands/ft.explain/)

Returns the execution plan for a complex query

#### [FT.EXPLAINCLI](https://redis.io/commands/ft.explaincli/)

Returns the execution plan for a complex query

#### [FT.ALTER](https://redis.io/commands/ft.alter/)

Adds a new field to the index

#### [FT.DROPINDEX](https://redis.io/commands/ft.dropindex/)

Deletes the index

#### [FT.ALIASADD](https://redis.io/commands/ft.aliasadd/)

Adds an alias to the index

#### [FT.ALIASUPDATE](https://redis.io/commands/ft.aliasupdate/)

Adds or updates an alias to the index

#### [FT.ALIASDEL](https://redis.io/commands/ft.aliasdel/)

Deletes an alias from the index

#### [FT.TAGVALS](https://redis.io/commands/ft.tagvals/)

Returns the distinct tags indexed in a Tag field

#### [FT.SYNUPDATE](https://redis.io/commands/ft.synupdate/)

Creates or updates a synonym group with additional terms

#### [FT.SYNDUMP](https://redis.io/commands/ft.syndump/)

Dumps the contents of a synonym group

#### [FT.SPELLCHECK](https://redis.io/commands/ft.spellcheck/)

Performs spelling correction on a query, returning suggestions for misspelled terms

#### [FT.DICTADD](https://redis.io/commands/ft.dictadd/)

Adds terms to a dictionary

#### [FT.DICTDEL](https://redis.io/commands/ft.dictdel/)

Deletes terms from a dictionary

#### [FT.DICTDUMP](https://redis.io/commands/ft.dictdump/)

Dumps all terms in the given dictionary

#### [FT._LIST](https://redis.io/commands/ft._list/)

Returns a list of all existing indexes

#### [FT.CONFIG SET](https://redis.io/commands/ft.config-set/)

Sets runtime configuration options

#### [FT.CONFIG GET](https://redis.io/commands/ft.config-get/)

Retrieves runtime configuration options

#### [FT.CONFIG HELP](https://redis.io/commands/ft.config-help/)

Help description of runtime configuration options

#### [FT.SEARCH](https://redis.io/commands/ft.search/)

Searches the index with a textual query, returning either documents or just ids

#### [FT.AGGREGATE](https://redis.io/commands/ft.aggregate/)

Adds terms to a dictionary

#### [FT.PROFILE](https://redis.io/commands/ft.profile/)

Performs a `FT.SEARCH` or `FT.AGGREGATE` command and collects performance information

#### [FT.CURSOR READ](https://redis.io/commands/ft.cursor-read/)

Reads from a cursor

#### [FT.CURSOR DEL](https://redis.io/commands/ft.cursor-del/)

Deletes a cursor



### Unsupported suggestion commands 
> To implement support for a command, see [here](/guides/implement-command/) 

#### [FT.SUGADD](https://redis.io/commands/ft.sugadd/)

Adds a suggestion string to an auto-complete suggestion dictionary

#### [FT.SUGGET](https://redis.io/commands/ft.sugget/)

Gets completion suggestions for a prefix

#### [FT.SUGDEL](https://redis.io/commands/ft.sugdel/)

Deletes a string from a suggestion index

#### [FT.SUGLEN](https://redis.io/commands/ft.suglen/)

Gets the size of an auto-complete suggestion dictionary


