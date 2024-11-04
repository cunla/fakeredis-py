# Dragonfly specific commands

> To implement support for a command, see [here](/guides/implement-command/)

These are commands that are not implemented in Redis but supported in Dragonfly and FakeRedis. To use these commands,
you can call `execute_command` with the command name and arguments as follows:

```python
client = FakeRedis(server_type="dragonfly")
client.execute_command("SADDEX", 10, "key", "value")
```

## [SADDEX](https://www.dragonflydb.io/docs/command-reference/sets/saddex)

Similar to SADD but adds one or more members that expire after specified number of seconds. An error is returned when
the value stored at key is not a set.
