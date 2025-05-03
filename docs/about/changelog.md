---
title: Change log
description: Changelog of all fakeredis releases
tags:
  - changelog
  - release-notes
toc_depth: 2
---

## v2.29.0 - 2025-05-01

### 🚀 Features

- Implement support for `NOVALUES` for `HSCAN`
- Implement support for `CLIENT LIST` #376

### 🐛 Bug Fixes

- Fix `json.set` nx arg behavior #372
- Fix issue with `hset` not resetting expiration over field
- Fix inconsistent 'pending' field in return from XINFO GROUPS #374
- Fix `TDIGEST.QUANTILE` to match redis behavior on a TDigest with one value #377

## v2.28.1 - 2025-04-02

### 🐛 Bug Fixes

- Open commands.json with encoding specified #367
- Fix `xadd` to use last timestamp if the current system timestamp is lower than the last timestamp #368

## v2.28.0 - 2025-03-29

### 🚀 Features

- implement support for `WITHSCORE` in `ZRANK` and `ZREVRANK` #357
- implement support for Connection commands `HELLO`, `CLIENT SETNAME`, `CLIENT GETNAME`, `CLIENT ID`, `CLIENT INFO` #361
- implement support for `HGETEX`, `HSETEX`, `HGETDEL` #365

### 🐛 Bug Fixes

- Fix `test_tcp_server_started` to close the connection @mgorny (#363)
- [ACL] Always allow `AUTH` command @wakonig (#362)
- [ACL] Provide `default` account acl on startup @wakonig (#362)

### 🧰 Maintenance

- Refactor hypothesis tests (#366)

## v2.27.0 - 2025-02-11

### 🚀 Features

- ACL commands support #338
    - `ACL LOAD`, `ACL SAVE`, `ACL LIST`, `ACL USERS`, `ACL GETUSER`, `ACL SETUSER`, `ACL DELUSER`, `ACL CAT`,
      `ACL LOG`, `ACL HELP`, `ACL WHOAMI`, `ACL GENPASS`, `ACL AUTH`, `ACL LOG_RESET`, `ACL LOG_COUNT`, `ACL LOG_GET`,
      `ACL LOG_HELP`, `ACL LOG_RESET`, `ACL LOG_COUNT`, `ACL LOG_GET`, `ACL LOG_HELP`
- Add support disable_decoding in async read_response #349
- Implement support for `SADDEX`, using a new set implementation with support for expiring members #350

### 🧰 Maintenance

- Remove end of life python 3.8 from test matrix
- Add python 3.13 to test matrix
- Improve documentation for Dragonfly/Valkey support

## v2.26.2 - 2024-12-15

### 🐛 Bug Fixes

- Fix bug in `xreadgroup` when stream length is less than COUNT with BLOCK #344

### 🧰 Maintenance

- Implement test for `SADDEX` (Dragonfly specific command) #348
- Update dependencies

## v2.26.1 - 2024-10-26

### 🐛 Bug Fixes

- Minor fix: using typing_extensions instead of typing for python 3.7 support #341/#343

## v2.26.0 - 2024-10-24

### 🚀 Features

- Support for server-type specific commands #340
- Support for Dragonfly `SADDEX` command #340

### 🐛 Bug Fixes

- Fix bug in bitpos function for the clear bit mode @Diskein #337

## v2.25.1 - 2024-09-30

### 🐛 Bug Fixes

- Fix missing default values for version/server_type in `FakeBaseConnectionMixin` #334

## v2.25.0 - 2024-09-28

### 🚀 Features

- Implement support for hash expiration related commands @j00bar #328
    - `HEXPIRE`, `HEXPIREAT`, `HEXPIRETIME`, `HPERSIST`, `HPEXPIRE`, `HPEXPIREAT`, `HPEXPIRETIME`, `HPTTL`, `HTTL`,
- Implement support for `SORT_RO` #325, `EXPIRETIME` #323, and `PEXPIRETIME` #324
- Support for creating a tcp server listening to multiple clients
- Testing against valkey 8.0 #333
- Improve documentation #332

### 🐛 Bug Fixes

- Replace `typing_extensions` dependency with `typing-extensions` #330

## v2.24.1 - 2024-08-26

### 🐛 Bug Fixes

- Fix license file added to site-packages #320

## v2.24.0 - 2024-08-24

### 🚀 Features

- Support for TIME SERIES commands (no support for align arguments on some commands) #310

### 🐛 Bug Fixes

- fix:xrevrange to work with exclusive ranges @hurlenko #319

### 🧰 Maintenance

- Update all dependencies, particularly pytest to v8
- Add tests against Dragonfly server #318
- Implement decocator `unsupported_server_types` to enable excluding tests from running against certain server types
  #318

## v2.23.5 - 2024-08-03

### 🐛 Bug Fixes

- fix:issue with async connection and blocking operations writing responses twice to socket #316

## v2.23.4- 2024-08-26

### 🐛 Bug Fixes

- fix:move random seed to HeavyKeeper to avoid issues #315

### 🧰 Maintenance

- Documented how to use fakeredis with FastAPI. @ sjjessop #292
- Using black for linting python code.

## v2.23.3- 2024-06-29

### 🧰 Maintenance

- docs: Full code for FastAPI integration (#312)

### 🐛 Bug Fixes

- Fix ttl for empty stream #313

## v2.23.2- 2024-05-18

### 🐛 Bug Fixes

- Fix reading multiple streams with blocking #309

## v2.23.1- 2024-05-12

### 🐛 Bug Fixes

- Fix `XREAD` behavior when `COUNT` is not provided but `BLOCKING` is provided #308

## v2.23.0 - 2024-05-07

### 🚀 Features

- Support for TDigest
  commands: `TDIGEST.ADD`,`TDIGEST.BYRANK`,`TDIGEST.BYREVRANK`,`TDIGEST.CDF`, `TDIGEST.CREATE`, `TDIGEST.INFO`,
  `TDIGEST.MAX`, `TDIGEST.MERGE`, `TDIGEST.MIN`, `TDIGEST.QUANTILE`, `TDIGEST.RANK`, `TDIGEST.RESET`, `TDIGEST.REVRANK`,
  `TDIGEST.TRIMMED_MEAN`.

### 🐛 Bug Fixes

- Import `Self` from typing vs. typing_extension

### 🧰 Maintenance

- Update dependencies
- Add redis-py 5.0.4 to tests
- Update lupa version constraint #306 @noamkush

## v2.22.0 - 2024-04-19

### 🚀 Features

- Support for setting LUA version from environment variable  `FAKEREDIS_LUA_VERSION` #287
- Support for loading LUA binary modules in fakeredis #304

### 🐛 Bug Fixes

- Fix the type hint for the version parameter in the async client #302
- Using LUA 5.1 like real redis #287
- fix: FakeRedisMixin.from_url() return type is really Self. @ben-xo #305

## v2.21.3 - 2024-03-12

### 🐛 Bug Fixes

- Revert behavior of defaulting to share the same server data structure between connections @howamith #303
- Fix type hint for version #302

## v2.21.2 - 2024-03-12

> Note: Since connection params are defaulted to be the same between async and sync connections, different FakeRedis
> connections with the same connection params (or without connection parameters) will share the same server data
> structure.

### 🐛 Bug Fixes

- Connection params are defaulted to be the same between async and sync connections #297
- `xinfo_stream` raises exception when stream does not exist #296

## v2.21.1 - 2024-02-15

### 🐛 Bug Fixes

- Support for float timeout values #289

### 🧰 Maintenance

- Fix django cache documentation #286

## v2.21.0 - 2024-01-30

### 🚀 Features

- Implement all TOP-K commands (`TOPK.INFO`, `TOPK.LIST`, `TOPK.RESERVE`,
  `TOPK.ADD`, `TOPK.COUNT`, `TOPK.QUERY`, `TOPK.INCRBY`) #278
- Implement all cuckoo filter commands #276
- Implement all Count-Min Sketch commands #277

### 🐛 Bug Fixes

- Fix XREAD blocking bug #274 #275
- EXAT option does not work #279

### 🧰 Maintenance

- Support for redis-py 5.1.0b3
- Improve `@testtools.run_test_if_redispy_ver`
- Refactor bloom filter commands implementation to use [pyprobables](https://github.com/barrust/pyprobables) instead of
  pybloom_live

## v2.20.1 - 2023-12-13

### 🐛 Bug Fixes

- Fix `XREAD` bug #256

### 🧰 Maintenance

- Testing for python 3.12
- Dependencies update

## v2.20.0 - 2023-10-21

### 🚀 Features

- Implement `BITFIELD` command #247
- Implement `COMMAND`, `COMMAND INFO`, `COMMAND COUNT` #248

## v2.19.0

### 🚀 Features

- Implement Bloom filters commands #239

### 🐛 Bug Fixes

- Fix error on blocking XREADGROUP #237

## v2.18.1

### 🐛 Bug Fixes

- Fix stream type issue #233

### 🧰 Maintenance

- Add mypy hints to everything
- Officially for redis-py 5.0.0, redis 7.2

## v2.18.0

### 🚀 Features

- Implement `PUBSUB NUMPAT` #195, `SSUBSCRIBE` #199, `SPUBLISH` #198,
  `SUNSUBSCRIBE` #200, `PUBSUB SHARDCHANNELS` #196, `PUBSUB SHARDNUMSUB` #197

### 🐛 Bug Fixes

- Fix All aio.FakeRedis instances share the same server #218

## v2.17.0

### 🚀 Features

- Implement `LPOS` #207, `LMPOP` #184, and `BLMPOP` #183
- Implement `ZMPOP` #191, `BZMPOP` #186

### 🐛 Bug Fixes

- Fix incorrect error msg for the group not found #210
- fix: use the same server_key within the pipeline when issued watch #213
- issue with ZRANGE and ZRANGESTORE with BYLEX #214

### Contributors

We'd like to thank all the contributors who worked on this release!

@OlegZv, @sjjessop

## v2.16.0

### 🚀 Features

- Implemented support for `JSON.MSET` #174, `JSON.MERGE` #181

### 🐛 Bug Fixes

- Add support for `version` for async FakeRedis #205

### 🧰 Maintenance

- Updated how to test django_rq #204

## v2.15.0

### 🚀 Features

- Implemented support for various stream groups commands:
    - `XGROUP CREATE` #161, `XGROUP DESTROY` #164, `XGROUP SETID` #165, `XGROUP DELCONSUMER` #162,
      `XGROUP CREATECONSUMER` #163, `XINFO GROUPS` #168, `XINFO CONSUMERS` #168, `XINFO STREAM` #169, `XREADGROUP` #171,
      `XACK` #157, `XPENDING` #170, `XCLAIM` #159, `XAUTOCLAIM` #158
- Implemented sorted set commands:
    - `ZRANDMEMBER` #192, `ZDIFF` #187, `ZINTER` #189, `ZUNION` #194, `ZDIFFSTORE` #188,
      `ZINTERCARD` #190, `ZRANGESTORE` #193
- Implemented list commands:
    - `BLMOVE` #182,

### 🧰 Maintenance

- Improved documentation.

## v2.14.2

### 🐛 Bug Fixes

- Fix documentation link

## v2.14.1

### 🐛 Bug Fixes

- Fix requirement for packaging.Version #177

## v2.14.0

### 🚀 Features

- Implement `HRANDFIELD` #156
- Implement `JSON.MSET`

### 🧰 Maintenance

- Improve streams code

## v2.13.0

### 🐛 Bug Fixes

- Fixed xadd timestamp (fixes #151) (#152)
- Implement XDEL #153

### 🧰 Maintenance

- Improve test code
- Fix reported security issue

## v2.12.1

### 🐛 Bug Fixes

- Add support for `Connection.read_response` arguments used in redis-py 4.5.5 and 5.0.0
- Adding state for scan commands (#99)

### 🧰 Maintenance

- Improved documentation (added async sample, etc.)
- Add redis-py 5.0.0b3 to GitHub workflow

## v2.12.0

### 🚀 Features

- Implement `XREAD` #147

## v2.11.2

### 🐛 Bug Fixes

- Unique FakeServer when no connection params are provided (#142)

## v2.11.1

### 🧰 Maintenance

- Minor fixes supporting multiple connections
- Update documentation

## v2.11.0

### 🚀 Features

- connection parameters awareness:
  Creating multiple clients with the same connection parameters will result in
  the same server data structure.

### 🐛 Bug Fixes

- Fix creating fakeredis.aioredis using url with user/password (#139)

## v2.10.3

### 🧰 Maintenance

- Support for redis-py 5.0.0b1
- Include tests in sdist (#133)

### 🐛 Bug Fixes

- Fix import used in GenericCommandsMixin.randomkey (#135)

## v2.10.2

### 🐛 Bug Fixes

- Fix async_timeout usage on py3.11 (#132)

## v2.10.1

### 🐛 Bug Fixes

- Enable testing django-cache using `FakeConnection`.

## v2.10.0

### 🚀 Features

- All geo commands implemented

## v2.9.2

### 🐛 Bug Fixes

- Fix bug for `xrange`

## v2.9.1

### 🐛 Bug Fixes

- Fix bug for `xrevrange`

## v2.9.0

### 🚀 Features

- Implement `XTRIM`
- Add support for `MAXLEN`, `MAXID`, `LIMIT` arguments for `XADD` command
- Add support for `ZRANGE` arguments for `ZRANGE` command [#127](https://github.com/cunla/fakeredis-py/issues/127)

### 🧰 Maintenance

- Relax python version requirement #128

## v2.8.0

### 🚀 Features

- Support for redis-py 4.5.0 [#125](https://github.com/cunla/fakeredis-py/issues/125)

### 🐛 Bug Fixes

- Fix import error for redis-py v3+ [#121](https://github.com/cunla/fakeredis-py/issues/121)

## v2.7.1

### 🐛 Bug Fixes

- Fix import error for NoneType #527

## v2.7.0

### 🚀 Features

- Implement `JSON.ARRINDEX`, `JSON.OBJLEN`, `JSON.OBJKEYS` ,
  `JSON.ARRPOP`, `JSON.ARRTRIM`, `JSON.NUMINCRBY`, `JSON.NUMMULTBY`,
  `XADD`, `XLEN`, `XRANGE`, `XREVRANGE`

### 🧰 Maintenance

- Improve json commands implementation.
- Improve commands documentation.

## v2.6.0

### 🚀 Features

- Implement `JSON.TYPE`, `JSON.ARRLEN` and `JSON.ARRAPPEND`

### 🐛 Bug Fixes

- Fix encoding of None (#118)

### 🧰 Maintenance

- Start skeleton for streams commands in `streams_mixin.py` and `test_streams_commands.py`
- Start migrating documentation to https://fakeredis.readthedocs.io/

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v2.5.0...v2.6.0

## v2.5.0

#### 🚀 Features

- Implement support for `BITPOS` (bitmap command) (#112)

#### 🐛 Bug Fixes

- Fix json mget when dict is returned (#114)
- fix: proper export (#116)

#### 🧰 Maintenance

- Extract param handling (#113)

#### Contributors

We'd like to thank all the contributors who worked on this release!

@Meemaw, @Pichlerdom

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v2.4.0...v2.5.0

## v2.4.0

#### 🚀 Features

- Implement `LCS` (#111), `BITOP` (#110)

#### 🐛 Bug Fixes

- Fix a bug the checking type in scan\_iter (#109)

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v2.3.0...v2.4.0

## v2.3.0

#### 🚀 Features

- Implement `GETEX` (#102)
- Implement support for `JSON.STRAPPEND` (json command) (#98)
- Implement `JSON.STRLEN`, `JSON.TOGGLE` and fix bugs with `JSON.DEL` (#96)
- Implement `PUBSUB CHANNELS`, `PUBSUB NUMSUB`

#### 🐛 Bug Fixes

- ZADD with XX \& GT allows updates with lower scores (#105)

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v2.2.0...v2.3.0

## v2.2.0

#### 🚀 Features

- Implement `JSON.CLEAR` (#87)
- Support for [redis-py v4.4.0](https://github.com/redis/redis-py/releases/tag/v4.4.0)

#### 🧰 Maintenance

- Implement script to create issues for missing commands
- Remove checking for deprecated redis-py versions in tests

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v2.1.0...v2.2.0

## v2.1.0

#### 🚀 Features

- Implement json.mget (#85)
- Initial json module support - `JSON.GET`, `JSON.SET` and `JSON.DEL` (#80)

#### 🐛 Bug Fixes

- fix: add nowait for asyncio disconnect (#76)

#### 🧰 Maintenance

- Refactor how commands are registered (#79)
- Refactor tests from redispy4\_plus (#77)

#### Contributors

We'd like to thank all the contributors who worked on this release!

@hyeongguen-song, @the-wondersmith

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v2.0.0...v2.1.0

## v2.0.0

#### 🚀 Breaking changes

- Remove support for aioredis separate from redis-py (redis-py versions 4.1.2 and below). (#65)

#### 🚀 Features

- Add support for redis-py v4.4rc4 (#73)
- Add mypy support (#74)

#### 🧰 Maintenance

- Separate commands to mixins (#71)
- Use release-drafter
- Update GitHub workflows

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v1.10.1...v2.0.0

## v1.10.1

#### What's Changed

* Implement support for `zmscore` by @the-wondersmith in #67

#### New Contributors

* @the-wondersmith made their first contribution in #67

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v1.10.0...v1.10.1

## v1.10.0

#### What's Changed

* implement `GETDEL` and `SINTERCARD` support in #57
* Test get float-type behavior in #59
* Implement `BZPOPMIN`/`BZPOPMAX` support in #60

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v1.9.4...v1.10.0

## v1.9.4

### What's Changed

* Separate LUA support to a different file in [#55](https://github.com/cunla/fakeredis-py/pull/55)
  **Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v1.9.3...v1.9.4

## v1.9.3

### Changed

* Removed python-six dependency

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v1.9.2...v1.9.3

## v1.9.2

#### What's Changed

* zadd support for GT/LT in [#49](https://github.com/cunla/fakeredis-py/pull/49)
* Remove `six` dependency in [#51](https://github.com/cunla/fakeredis-py/pull/51)
* Add host to `conn_pool_args`  in [#51](https://github.com/cunla/fakeredis-py/pull/51)

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v1.9.1...v1.9.2

## v1.9.1

#### What's Changed

* Zrange byscore in [#44](https://github.com/cunla/fakeredis-py/pull/44)
* Expire options in [#46](https://github.com/cunla/fakeredis-py/pull/46)

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v1.9.0...v1.9.1

## v1.9.0

#### What's Changed

* Enable redis7 support in [#42](https://github.com/cunla/fakeredis-py/pull/42)

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v1.8.2...v1.9.0

## v1.8.2

#### What's Changed

* Update the `publish` GitHub action to create an issue on failure by @terencehonles
  in [#33](https://github.com/dsoftwareinc/fakeredis-py/pull/33)
* Add `release draft` job in [#37](https://github.com/dsoftwareinc/fakeredis-py/pull/37)
* Fix input and output type of cursors for SCAN commands by @tohin
  in [#40](https://github.com/dsoftwareinc/fakeredis-py/pull/40)
* Fix passing params in args—Fix #36 in [#41](https://github.com/dsoftwareinc/fakeredis-py/pull/41)

#### New Contributors

* @tohin made their first contribution in [#40](https://github.com/dsoftwareinc/fakeredis-py/pull/40)

**Full Changelog**: https://github.com/dsoftwareinc/fakeredis-py/compare/v1.8.1...v1.8.2

## v1.8.1

#### What's Changed

* fix: allow redis 4.3.* by @terencehonles in [#30](https://github.com/dsoftwareinc/fakeredis-py/pull/30)

#### New Contributors

* @terencehonles made their first contribution in [#30](https://github.com/dsoftwareinc/fakeredis-py/pull/30)

**Full Changelog**: https://github.com/dsoftwareinc/fakeredis-py/compare/v1.8...v1.8.1

## v1.8

#### What's Changed

* Fix handling url with username and password in [#27](https://github.com/dsoftwareinc/fakeredis-py/pull/27)
* Refactor tests in [#28](https://github.com/dsoftwareinc/fakeredis-py/pull/28)
* 23 - Re-add dependencies lost during switch to poetry by @xkortex
  in [#26](https://github.com/dsoftwareinc/fakeredis-py/pull/26)

**Full Changelog**: https://github.com/dsoftwareinc/fakeredis-py/compare/v1.7.6.1...v1.8

## v1.7.6

#### Added

* add `IMOVE` operation by @BGroever in [#11](https://github.com/dsoftwareinc/fakeredis-py/pull/11)
* Add `SMISMEMBER` command by @OlegZv in [#20](https://github.com/dsoftwareinc/fakeredis-py/pull/20)

#### Removed

* Remove Python 3.7 by @nzw0301 in [#8](https://github.com/dsoftwareinc/fakeredis-py/pull/8)

#### What's Changed

* fix: work with `redis.asyncio` by @zhongkechen in [#10](https://github.com/dsoftwareinc/fakeredis-py/pull/10)
* Migrate to poetry in [#12](https://github.com/dsoftwareinc/fakeredis-py/pull/12)
* Create annotation for redis4+ tests in [#14](https://github.com/dsoftwareinc/fakeredis-py/pull/14)
* Make aioredis and lupa optional dependencies in [#16](https://github.com/dsoftwareinc/fakeredis-py/pull/16)
* Remove aioredis requirement if redis-py 4.2+ by @ikornaselur
  in [#19](https://github.com/dsoftwareinc/fakeredis-py/pull/19)

#### New Contributors

* @nzw0301 made their first contribution in [#8](https://github.com/dsoftwareinc/fakeredis-py/pull/8)
* @zhongkechen made their first contribution in [#10](https://github.com/dsoftwareinc/fakeredis-py/pull/10)
* @BGroever made their first contribution in [#11](https://github.com/dsoftwareinc/fakeredis-py/pull/11)
* @ikornaselur made their first contribution in [#19](https://github.com/dsoftwareinc/fakeredis-py/pull/19)
* @OlegZv made their first contribution in [#20](https://github.com/dsoftwareinc/fakeredis-py/pull/20)

**Full Changelog**: https://github.com/dsoftwareinc/fakeredis-py/compare/v1.7.5...v1.7.6

#### Thanks to our sponsors this month

- @beatgeek

## v1.7.5

#### What's Changed

* Fix python3.8 redis4.2+ issue in [#6](https://github.com/dsoftwareinc/fakeredis-py/pull/6)

**Full Changelog**: https://github.com/dsoftwareinc/fakeredis-py/compare/v1.7.4...v1.7.5

## v1.7.4

#### What's Changed

* Support for python3.8 in [#1](https://github.com/dsoftwareinc/fakeredis-py/pull/1)
* Feature/publish action in [#2](https://github.com/dsoftwareinc/fakeredis-py/pull/2)

**Full Changelog**: https://github.com/dsoftwareinc/fakeredis-py/compare/1.7.1...v1.7.4
