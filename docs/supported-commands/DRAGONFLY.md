# Dragonfly specific commands

> To implement support for a command, see [here](../../guides/implement-command/)

These are commands that are not implemented in Redis but supported in Dragonfly and FakeRedis. To use these commands,
you can call `execute_command` with the command name and arguments as follows:

```python
client = FakeRedis(server_type="dragonfly")
client.execute_command("SADDEX", 10, "key", "value")
```

## [SADDEX](https://www.dragonflydb.io/docs/command-reference/sets/saddex)

Similar to SADD but adds one or more members that expire after specified number of seconds. An error is returned when
the value stored at key is not a set.

## [CL.THROTTLE](https://www.dragonflydb.io/docs/command-reference/rate-limiter/cl.throttle)

`CL.THROTTLE key max_burst count_per_period period [quantity]`

Applies a rate limit to `key` using the generic cell rate algorithm (GCRA), a leaky bucket over a rolling time window.
`quantity` (the number of tokens the request costs, 1 by default) is applied to a bucket of `max_burst + 1` tokens that
refills at `count_per_period` tokens every `period` seconds. Replies with an array of five integers:

1. Whether the action was limited: `0` if it is allowed, `1` if it was blocked.
2. The total limit of the key (`max_burst + 1`), equivalent to `X-RateLimit-Limit`.
3. The remaining limit of the key, equivalent to `X-RateLimit-Remaining`.
4. The number of seconds until the caller should retry, `-1` if the action was allowed. Equivalent to `Retry-After`.
5. The number of seconds until the limit resets to its maximum capacity, equivalent to `X-RateLimit-Reset`.

```python
client = FakeRedis(server_type="dragonfly")
# Allow 5 actions, refilling at one action every 10 seconds
client.execute_command("CL.THROTTLE", "user123", 4, 1, 10)  # [0, 5, 4, -1, 11]
```
