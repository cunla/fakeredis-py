# `cf` commands (12/12 implemented)

## [CF.RESERVE](https://redis.io/commands/cf.reserve/)

Creates a new Cuckoo Filter

## [CF.ADD](https://redis.io/commands/cf.add/)

Adds an item to a Cuckoo Filter

## [CF.ADDNX](https://redis.io/commands/cf.addnx/)

Adds an item to a Cuckoo Filter if the item did not exist previously.

## [CF.INSERT](https://redis.io/commands/cf.insert/)

Adds one or more items to a Cuckoo Filter. A filter will be created if it does not exist

## [CF.INSERTNX](https://redis.io/commands/cf.insertnx/)

Adds one or more items to a Cuckoo Filter if the items did not exist previously. A filter will be created if it does not exist

## [CF.EXISTS](https://redis.io/commands/cf.exists/)

Checks whether one or more items exist in a Cuckoo Filter

## [CF.MEXISTS](https://redis.io/commands/cf.mexists/)

Checks whether one or more items exist in a Cuckoo Filter

## [CF.DEL](https://redis.io/commands/cf.del/)

Deletes an item from a Cuckoo Filter

## [CF.COUNT](https://redis.io/commands/cf.count/)

Return the number of times an item might be in a Cuckoo Filter

## [CF.SCANDUMP](https://redis.io/commands/cf.scandump/)

Begins an incremental save of the bloom filter

## [CF.LOADCHUNK](https://redis.io/commands/cf.loadchunk/)

Restores a filter previously saved using SCANDUMP

## [CF.INFO](https://redis.io/commands/cf.info/)

Returns information about a Cuckoo Filter



