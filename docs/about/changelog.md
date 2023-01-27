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
- fix: properly export (#116)
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
- Fix bug checking type in scan\_iter (#109)

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
- Add mypy support  (#74)
#### 🧰 Maintenance
- Separate commands to mixins (#71)
- Use release-drafter
- Update GitHub workflows

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v1.10.1...v2.0.0
## v1.10.1
#### What's Changed

* Implement support for `zmscore` by @the-wondersmith in [#67](https://github.com/cunla/fakeredis-py/pull/67)
#### New Contributors

* @the-wondersmith made their first contribution in [#67](https://github.com/cunla/fakeredis-py/pull/67)

**Full Changelog**: https://github.com/cunla/fakeredis-py/compare/v1.10.0...v1.10.1
## v1.10.0
#### What's Changed

* implement `GETDEL` and `SINTERCARD` support in [#57](https://github.com/cunla/fakeredis-py/pull/57)
* Test get float-type behavior in [#59](https://github.com/cunla/fakeredis-py/pull/59)
* Implement `BZPOPMIN`/`BZPOPMAX` support in [#60](https://github.com/cunla/fakeredis-py/pull/60)

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
* Remove six dependency in [#51](https://github.com/cunla/fakeredis-py/pull/51)
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

* Update publish GitHub action to create an issue on failure by @terencehonles
  in [#33](https://github.com/dsoftwareinc/fakeredis-py/pull/33)
* Add release draft job in [#37](https://github.com/dsoftwareinc/fakeredis-py/pull/37)
* Fix input and output type of cursors for SCAN commands by @tohin
  in [#40](https://github.com/dsoftwareinc/fakeredis-py/pull/40)
* Fix passing params in args - Fix #36 in [#41](https://github.com/dsoftwareinc/fakeredis-py/pull/41)
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

**Full Changelog**: https://github.com/dsoftwareinc/fakeredis-py/compare/v1.7.6.1...v1.8
## v1.7.6.1
#### What's Changed

* 23 - Re-add dependencies lost during switch to poetry by @xkortex
  in [#26](https://github.com/dsoftwareinc/fakeredis-py/pull/26)
#### New Contributors

* @xkortex made their first contribution in https://github.com/dsoftwareinc/fakeredis-py/pull/26

**Full Changelog**: https://github.com/dsoftwareinc/fakeredis-py/compare/v1.7.6...v1.7.6.1
## v1.7.6
#### Added

* add IMOVE operation by @BGroever in [#11](https://github.com/dsoftwareinc/fakeredis-py/pull/11)
* Add SMISMEMBER command by @OlegZv in [#20](https://github.com/dsoftwareinc/fakeredis-py/pull/20)
#### Removed

* Remove Python 3.7 by @nzw0301 in [#8](https://github.com/dsoftwareinc/fakeredis-py/pull/8)
#### What's Changed

* fix: work with redis.asyncio by @zhongkechen in [#10](https://github.com/dsoftwareinc/fakeredis-py/pull/10)
* Migrate to poetry in [#12](https://github.com/dsoftwareinc/fakeredis-py/pull/12)
* Create annotation for redis4+ tests in [#14](https://github.com/dsoftwareinc/fakeredis-py/pull/14)
* Make aioredis and lupa optional dependencies in [#16](https://github.com/dsoftwareinc/fakeredis-py/pull/16)
* Remove aioredis requirement if redis-py 4.2+ by @ikornaselur in [#19](https://github.com/dsoftwareinc/fakeredis-py/pull/19)
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
