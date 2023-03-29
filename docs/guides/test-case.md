
# Write a new test case

There are multiple scenarios for test, with different versions of python, redis-py and redis server, etc.
The tests not only assert the validity of the expected output with FakeRedis but also with a real redis server.
That way parity of real Redis and FakeRedis is ensured.

To write a new test case for a command:

- Determine which mixin the command belongs to and the test file for
  the mixin (eg, `string_mixin.py` => `test_string_commands.py`).
- Tests should support python 3.7 and above.
- Determine when support for the command was introduced
    - To limit the redis-server versions it will run on use:
      `@pytest.mark.max_server(version)` and `@pytest.mark.min_server(version)`
    - To limit the redis-py version use `@run_test_if_redispy_ver(above/below, version)`
- pytest will inject a redis connection to the argument `r` of the test.

Sample of running a test for redis-py v4.2.0 and above, redis-server 7.0 and above.

```python
@pytest.mark.min_server('7')
@testtools.run_test_if_redispy_ver('above', '4.2.0')
def test_expire_should_not_expire__when_no_expire_is_set(r):
    r.set('foo', 'bar')
    assert r.get('foo') == b'bar'
    assert r.expire('foo', 1, xx=True) == 0
```
