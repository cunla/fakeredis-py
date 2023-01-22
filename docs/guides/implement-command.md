# Implementing support for a command

Creating a new command support should be done in the `FakeSocket` class (in `_fakesocket.py`) by creating the method
and using `@command` decorator (which should be the command syntax, you can use existing samples on the file).

For example:

```python
class FakeSocket(BaseFakeSocket, FakeLuaSocket):
    # ...
    @command(name='zscore', fixed=(Key(ZSet), bytes), repeat=(), flags=[])
    def zscore(self, key, member):
        try:
            return self._encodefloat(key.value[member], False)
        except KeyError:
            return None
```

## How to use `@command` decorator

The `@command` decorator register the method as a redis command and define the accepted format for it.
It will create a `Signature` instance for the command. Whenever the command is triggered, the `Signature.apply(..)`
method will be triggered to check the validity of syntax and analyze the command arguments.

By default, it takes the name of the method as the command name.

If the method implements a subcommand (eg, `SCRIPT LOAD`), a Redis module command (eg, `JSON.GET`),
or a python reserve word where you can not use it as the method name (eg, `EXEC`), then you can supply
explicitly the name parameter.

If the command implemented require certain arguments, they can be supplied in the first parameter as a tuple.
When receiving the command through the socket, the bytes will be converted to the argument types
supplied or remain as `bytes`.

Argument types (All in `_commands.py`):

- `Key(KeyType)` - Will get from the DB the key and validate its value is of `KeyType` (if `KeyType` is supplied).
  It will generate a `CommandItem` from it which provides access to the database value.
- `Int` - Decode the `bytes` to `int` and vice versa.
- `DbIndex`/`BitOffset`/`BitValue`/`Timeout` - Basically the same behavior as `Int`, but with different messages when
  encode/decode fail.
- `Hash` - dictionary, usually describe the type of value stored in Key `Key(Hash)`
- `Float` - Encode/Decode `bytes` <-> `float`
- `SortFloat` - Similar to `Float` with different error messages.
- `ScoreTest` - Argument converter for sorted set score endpoints.
- `StringTest` - Argument converter for sorted set endpoints (lex).
- `ZSet` - Sorted Set.

## Implement a test for it

There are multiple scenarios for test, with different versions of redis server, redis-py, etc.
The tests not only assert the validity of output but runs the same test on a real redis-server and compares the output
to the real server output.

- Create tests in the relevant test file.
- If support for the command was introduced in a certain version of redis-py (
  see [redis-py release notes](https://github.com/redis/redis-py/releases/tag/v4.3.4)) you can use the
  decorator `@testtools.run_test_if_redispy_ver` on your tests. example:

```python
@testtools.run_test_if_redispy_ver('above', '4.2.0')  # This will run for redis-py 4.2.0 or above.
def test_expire_should_not_expire__when_no_expire_is_set(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    assert r.expire('foo', 1, xx=True) == 0
```

## Updating documentation

Lastly, run from the root of the project the script to regenerate documentation for
supported and unsupported commands:

```bash
python scripts/supported.py    
```

Include the changes in the `docs/` directory in your pull request.

