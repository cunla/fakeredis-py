-----
Below you have a list of [implemented commands](#implemented-commands) and a list
of [unimplemented commands](#unimplemented-commands).

# Implemented Commands
    
### string
 * append
 * decr
 * decrby
 * get
 * getrange
 * getset
 * incr
 * incrby
 * incrbyfloat
 * mget
 * mset
 * msetnx
 * psetex
 * set
 * setex
 * setnx
 * setrange
 * strlen
 * substr

### server
 * bgsave
 * dbsize
 * flushall
 * flushdb
 * lastsave
 * save
 * swapdb
 * time

### bitmap
 * bitcount
 * getbit
 * setbit

### list
 * blpop
 * brpop
 * brpoplpush
 * lindex
 * linsert
 * llen
 * lpop
 * lpush
 * lpushx
 * lrange
 * lrem
 * lset
 * ltrim
 * rpop
 * rpoplpush
 * rpush
 * rpushx

### generic
 * del
 * dump
 * exists
 * expire
 * expireat
 * keys
 * move
 * persist
 * pexpire
 * pexpireat
 * pttl
 * randomkey
 * rename
 * renamenx
 * restore
 * scan
 * sort
 * ttl
 * type
 * unlink

### transactions
 * discard
 * exec
 * multi
 * unwatch
 * watch

### connection
 * echo
 * ping
 * select

### scripting
 * eval
 * evalsha
 * script
 * script load

### hash
 * hdel
 * hexists
 * hget
 * hgetall
 * hincrby
 * hincrbyfloat
 * hkeys
 * hlen
 * hmget
 * hmset
 * hscan
 * hset
 * hsetnx
 * hstrlen
 * hvals

### hyperloglog
 * pfadd
 * pfcount
 * pfmerge

### pubsub
 * psubscribe
 * publish
 * punsubscribe
 * subscribe
 * unsubscribe

### set
 * sadd
 * scard
 * sdiff
 * sdiffstore
 * sinter
 * sinterstore
 * sismember
 * smembers
 * smove
 * spop
 * srandmember
 * srem
 * sscan
 * sunion
 * sunionstore

### sorted-set
 * zadd
 * zcard
 * zcount
 * zincrby
 * zinterstore
 * zlexcount
 * zrange
 * zrangebylex
 * zrangebyscore
 * zrank
 * zrem
 * zremrangebylex
 * zremrangebyrank
 * zremrangebyscore
 * zrevrange
 * zrevrangebylex
 * zrevrangebyscore
 * zrevrank
 * zscan
 * zscore
 * zunionstore


# Unimplemented Commands
All of the redis commands are implemented in fakeredis with these exceptions:
    
### server
 * acl
 * acl cat
 * acl deluser
 * acl dryrun
 * acl genpass
 * acl getuser
 * acl help
 * acl list
 * acl load
 * acl log
 * acl save
 * acl setuser
 * acl users
 * acl whoami
 * bgrewriteaof
 * command
 * command count
 * command docs
 * command getkeys
 * command getkeysandflags
 * command help
 * command info
 * command list
 * config
 * config get
 * config help
 * config resetstat
 * config rewrite
 * config set
 * debug
 * failover
 * info
 * latency
 * latency doctor
 * latency graph
 * latency help
 * latency histogram
 * latency history
 * latency latest
 * latency reset
 * lolwut
 * memory
 * memory doctor
 * memory help
 * memory malloc-stats
 * memory purge
 * memory stats
 * memory usage
 * module
 * module help
 * module list
 * module load
 * module loadex
 * module unload
 * monitor
 * psync
 * replconf
 * replicaof
 * restore-asking
 * role
 * shutdown
 * slaveof
 * slowlog
 * slowlog get
 * slowlog help
 * slowlog len
 * slowlog reset
 * sync

### cluster
 * asking
 * cluster
 * cluster addslots
 * cluster addslotsrange
 * cluster bumpepoch
 * cluster count-failure-reports
 * cluster countkeysinslot
 * cluster delslots
 * cluster delslotsrange
 * cluster failover
 * cluster flushslots
 * cluster forget
 * cluster getkeysinslot
 * cluster help
 * cluster info
 * cluster keyslot
 * cluster links
 * cluster meet
 * cluster myid
 * cluster nodes
 * cluster replicas
 * cluster replicate
 * cluster reset
 * cluster saveconfig
 * cluster set-config-epoch
 * cluster setslot
 * cluster shards
 * cluster slaves
 * cluster slots
 * readonly
 * readwrite

### connection
 * auth
 * client
 * client caching
 * client getname
 * client getredir
 * client help
 * client id
 * client info
 * client kill
 * client list
 * client no-evict
 * client pause
 * client reply
 * client setname
 * client tracking
 * client trackinginfo
 * client unblock
 * client unpause
 * hello
 * quit
 * reset

### bitmap
 * bitfield
 * bitfield_ro
 * bitop
 * bitpos

### list
 * blmove
 * blmpop
 * lmove
 * lmpop
 * lpos

### sorted-set
 * bzmpop
 * bzpopmax
 * bzpopmin
 * zdiff
 * zdiffstore
 * zinter
 * zintercard
 * zmpop
 * zmscore
 * zpopmax
 * zpopmin
 * zrandmember
 * zrangestore
 * zunion

### generic
 * copy
 * expiretime
 * migrate
 * object
 * object encoding
 * object freq
 * object help
 * object idletime
 * object refcount
 * pexpiretime
 * sort_ro
 * touch
 * wait

### scripting
 * evalsha_ro
 * eval_ro
 * fcall
 * fcall_ro
 * function
 * function delete
 * function dump
 * function flush
 * function help
 * function kill
 * function list
 * function load
 * function restore
 * function stats
 * script debug
 * script exists
 * script flush
 * script help
 * script kill

### geo
 * geoadd
 * geodist
 * geohash
 * geopos
 * georadius
 * georadiusbymember
 * georadiusbymember_ro
 * georadius_ro
 * geosearch
 * geosearchstore

### string
 * getdel
 * getex
 * lcs

### hash
 * hrandfield

### hyperloglog
 * pfdebug
 * pfselftest

### pubsub
 * pubsub
 * pubsub channels
 * pubsub help
 * pubsub numpat
 * pubsub numsub
 * pubsub shardchannels
 * pubsub shardnumsub
 * spublish
 * ssubscribe
 * sunsubscribe

### set
 * sintercard
 * smismember

### stream
 * xack
 * xadd
 * xautoclaim
 * xclaim
 * xdel
 * xgroup
 * xgroup create
 * xgroup createconsumer
 * xgroup delconsumer
 * xgroup destroy
 * xgroup help
 * xgroup setid
 * xinfo
 * xinfo consumers
 * xinfo groups
 * xinfo help
 * xinfo stream
 * xlen
 * xpending
 * xrange
 * xread
 * xreadgroup
 * xrevrange
 * xsetid
 * xtrim

