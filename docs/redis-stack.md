# Support for redis-stack

To install all supported modules, you can install fakeredis with `pip install fakeredis[lua,json,bf]`.

## RedisJson support

The JSON capability of Redis Stack provides JavaScript Object Notation (JSON) support for Redis. It lets you store,
update, and retrieve JSON values in a Redis database, similar to any other Redis data type. Redis JSON also works
seamlessly with Search and Query to let you index and query JSON documents.

JSONPath's syntax: The following JSONPath syntax table was adapted from Goessner's [path syntax comparison][4].

Currently, Redis Json module is fully implemented (see [supported commands][1]).
Support for JSON commands (e.g., [`JSON.GET`][2]) is implemented using
[jsonpath-ng,][3] you can install it using `pip install 'fakeredis[json]'`.

```pycon
>>> import fakeredis
>>> from redis.commands.json.path import Path
>>> r = fakeredis.FakeStrictRedis()
>>> assert r.json().set("foo", Path.root_path(), {"x": "bar"}, ) == 1
>>> r.json().get("foo")
{'x': 'bar'}
>>> r.json().get("foo", Path("x"))
'bar'
```

## Bloom filter support

Bloom filters are a probabilistic data structure that checks for the presence of an element in a set.

Instead of storing all the elements in the set, Bloom Filters store only the elements' hashed representation, thus
sacrificing some precision. The trade-off is that Bloom Filters are very space-efficient and fast.

You can get a false positive result, but never a false negative, i.e., if the bloom filter says that an element is not
in the set, then it is definitely not in the set. If the bloom filter says that an element is in the set, then it is
most likely in the set, but it is not guaranteed.

Currently, RedisBloom module bloom filter commands are fully implemented using [pybloom-live][5](
see [supported commands][6]).

You can install it using `pip install 'fakeredis[probabilistic]'`.

```pycon
>>> import fakeredis
>>> r = fakeredis.FakeStrictRedis()
>>> r.bf().madd('key', 'v1', 'v2', 'v3') == [1, 1, 1]
>>> r.bf().exists('key', 'v1')
1
>>> r.bf().exists('key', 'v5')
0
```

## [Count-Min Sketch][8] support

Count-min sketch is a probabilistic data structure that estimates the frequency of an element in a data stream.

You can install it using `pip install 'fakeredis[probabilistic]'`.

```pycon
>>> import fakeredis
>>> r = fakeredis.FakeStrictRedis()
>>> r.cms().initbydim("cmsDim", 100, 5)
OK
>>> r.cms().incrby("cmsDim", ["foo"], [3])
[3]
```

## [Cuckoo filter][9] support

Cuckoo filters are a probabilistic data structure that checks for the presence of an element in a set

You can install it using `pip install 'fakeredis[probabilistic]'`.

## [Redis programmability][7]

Redis provides a programming interface that lets you execute custom scripts on the server itself. In Redis 7 and beyond,
you can use Redis Functions to manage and run your scripts. In Redis 6.2 and below, you use Lua scripting with the EVAL
command to program the server.

If you wish to have Lua scripting support (this includes features like ``redis.lock.Lock``, which are implemented in
Lua), you will need [lupa][10], you can install it using `pip install 'fakeredis[lua]'`

By default, FakeRedis works with LUA version 5.1, to use a different version supported by lupa,
set the `FAKEREDIS_LUA_VERSION` environment variable to the desired version (e.g., `5.4`).

### LUA binary modules

fakeredis supports using LUA binary modules as well. In order to have your FakeRedis instance load a LUA binary module,
you can use the `lua_modules` parameter.

```pycon
>>> import fakeredis
>>> r = fakeredis.FakeStrictRedis(lua_modules={"my_module.so"})
```

The module `.so`/`.dll` file should be in the working directory.

To install LUA modules, you can use [luarocks][11] to install the module and then copy the `.so`/`.dll` file to the
working directory.

For example, to install `lua-cjson`:

```sh
luarocks install lua-cjson
cp /opt/homebrew/lib/lua/5.4/cjson.so `pwd`
```

[1]:./redis-commands/RedisJson/

[2]:https://redis.io/commands/json.get/

[3]:https://github.com/h2non/jsonpath-ng

[4]:https://goessner.net/articles/JsonPath/index.html#e2

[5]:https://github.com/joseph-fox/python-bloomfilter

[6]:./redis-commands/BloomFilter/

[7]:https://redis.io/docs/interact/programmability/

[8]:https://redis.io/docs/data-types/probabilistic/count-min-sketch/

[9]:https://redis.io/docs/data-types/probabilistic/cuckoo-filter/

[10]:https://pypi.org/project/lupa/

[11]:https://luarocks.org/
