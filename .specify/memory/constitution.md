<!--
Sync Impact Report
==================
Version change: (unversioned template) → 1.0.0
Bump rationale: Initial ratification. The file was still the pristine placeholder
template; every principle and section is newly defined, so this is the first
released version rather than an amendment.

Modified principles:
  - [PRINCIPLE_1_NAME] → I. Real-Server Parity (NON-NEGOTIABLE)
  - [PRINCIPLE_2_NAME] → II. Drop-In Client Compatibility
  - [PRINCIPLE_3_NAME] → III. Differential Testing Against a Real Server
  - [PRINCIPLE_4_NAME] → IV. Optional Dependencies Stay Optional
  - [PRINCIPLE_5_NAME] → V. Generated Metadata Is Never Hand-Edited

Added sections:
  - Code Quality Standards (was [SECTION_2_NAME])
  - Development Workflow (was [SECTION_3_NAME])
  - Governance (rules filled in)

Removed sections: none

Deferred TODOs:
  - TODO(RATIFICATION_DATE): recorded as the date this constitution was first
    filled in (2026-08-04), not the project's 2011 inception. Replace if the
    maintainer wants the original project start date instead.
-->

# fakeredis Constitution

## Core Principles

### I. Real-Server Parity (NON-NEGOTIABLE)

A real Redis/Valkey server is the specification; fakeredis is the implementation. When behavior
differs, the real server is right and fakeredis MUST change.

- Command semantics, return types, error messages, and edge-case behavior MUST match what the
  emulated server returns for the same input.
- Error responses MUST be raised as `SimpleError` with a message constant from `_msgs.py`, never
  as an uncaught Python exception.
- Server-version-dependent and server-type-dependent behavior MUST be gated explicitly (the
  `version=` / `server_type=` client options), not approximated with a single blended behavior.
- A deliberate divergence from real-server behavior MUST be documented in `docs/` and covered by a
  test that asserts the divergence, so it is a known contract rather than an accident.

Rationale: users adopt fakeredis so their tests can trust the results. A silent behavioral
difference turns a passing test suite into a false negative in production.

### II. Drop-In Client Compatibility

fakeredis MUST remain substitutable for the real client classes without any caller changes.

- Every command MUST work identically across all four supported paths: sync and async, redis-py
  and valkey-py.
- Public entry points (`FakeRedis`, `FakeStrictRedis`, `FakeAsyncRedis`, `FakeValkey`,
  `FakeAsyncValkey`, `FakeServer`, `FakeTcpServer`) and their keyword arguments are public API.
  Removing or renaming one, or changing a default, is a breaking change under Principle governance.
- Support MUST hold for every Python version and every `redis` / `valkey` version declared in
  `pyproject.toml`. Dropping one is a breaking change.
- Both RESP2 and RESP3 protocol encodings MUST be supported for any command whose reply shape
  differs between them.

Rationale: "drop-in" is the product. A feature that only works on the sync redis-py path is not
finished, it is a quarter finished.

### III. Differential Testing Against a Real Server

Every command behavior MUST be pinned by a test that can run against both fakeredis and a real
server.

- New or changed commands MUST have tests in the matching `test/test_mixins/` or `test/test_stack/`
  file, using the injected `r` connection fixture so they execute under both fixture variants.
- Tests MUST NOT be restricted to the fake fixture (`fake_only`) merely because the real-server run
  is inconvenient; that marker is reserved for behavior a real server cannot exhibit.
- Behavior that only exists on some server versions or server types MUST be bounded with the
  provided markers (`supported_server_versions`, `unsupported_server_types`, `resp2_only`,
  `resp3_only`, `run_test_if_redispy_ver`) rather than left to fail on unsupported combinations.
- Tests for newly supported functionality MUST exercise the wire command directly (e.g.
  `raw_command`) when the client library's helper would apply its own client-side validation and
  mask the server behavior under test.

Rationale: parity claims that are not executed against a real server are claims, not facts. The
differential suite is the only mechanism that keeps Principle I honest.

### IV. Optional Dependencies Stay Optional

The base install MUST remain pure Python with no dependency beyond the core client and
`sortedcontainers`.

- Redis Stack modules (JSON, TimeSeries, Bloom/Cuckoo, TopK, T-Digest, VectorSet) and Lua scripting
  MUST live under `stack/` and activate only when their optional dependency is importable.
- Importing `fakeredis` MUST succeed, and all core commands MUST work, with zero extras installed.
- A missing optional dependency MUST surface as the command being unsupported, never as an
  `ImportError` at import time or a crash mid-command.
- Adding a hard dependency to the base package requires an amendment to this constitution.

Rationale: fakeredis is a test dependency. Every byte it forces into a user's environment is a byte
they did not ask for and a version conflict they may have to resolve.

### V. Generated Metadata Is Never Hand-Edited

Command metadata and the supported-commands documentation are build products of the code.

- `commands.json` MUST be regenerated with `scripts/generate_command_info.py` after any change to a
  command's registration, signature, or name.
- `docs/` supported-command pages MUST be regenerated with
  `scripts/generate_supported_commands_doc.py` and the regenerated files included in the same PR as
  the code change.
- Neither artifact may be edited by hand. If output is wrong, fix the generator or the command
  registration.

Rationale: hand-edited generated files drift silently and then lie to users about what is
supported. Keeping generation in the same commit makes the docs a consequence of the code rather
than a parallel truth.

## Code Quality Standards

- `uv run ruff check fakeredis/`, `uv run ruff format --check fakeredis/`, and
  `uv run mypy fakeredis/` MUST pass before merge. Mypy runs in strict mode over the package.
- Formatting is Ruff-owned: 120-column lines, double quotes. Style MUST NOT be argued in review;
  run the formatter.
- Lint suppressions MUST be narrow (specific rule, specific file or line) and MUST carry a comment
  stating why the flagged pattern is deliberate.
- New commands MUST follow the established pattern: a `@command(...)`-decorated method on the
  appropriate mixin, `Key(type_)` in the signature for auto-fetched keys, `CommandItem.update()` to
  mark writes, and `extract_args` for optional or variadic arguments.
- Command implementations MUST be placed in the mixin matching their data type or feature area. A
  new mixin requires a distinct feature area, not organizational preference.

## Development Workflow

- Commit messages MUST follow Conventional Commits (`fix:`, `feat:`, `docs:`, `chore:`, …), with
  `!` or a `BREAKING CHANGE:` footer for incompatible changes. The type drives the release bump.
- Releases follow semantic versioning: `fix:` → PATCH, `feat:` → MINOR, breaking → MAJOR.
- Changes arrive via pull request from a fork or branch; direct pushes to `master` are reserved for
  release and dependency chores.
- The full test suite requires a real server on `localhost:6390` (`docker compose up -d redis8`).
  Contributors MUST run the suite locally before opening a PR; CI MUST be green before merge.
- User-visible changes MUST update `docs/about/changelog.md`.
- Security vulnerabilities MUST be reported through the Tidelift security contact, never in a
  public issue.

## Governance

This constitution supersedes conflicting practices, habits, and prior review precedent. Where it
and a code comment or older document disagree, this file wins.

- **Amendment procedure**: amendments are proposed as a pull request that modifies this file,
  states the rationale, and identifies the version bump. The maintainer approves. An amendment that
  invalidates existing code MUST include the migration plan or the follow-up issue that carries it.
- **Versioning policy**: this document is versioned semantically. MAJOR for removing or redefining
  a principle in a backward-incompatible way; MINOR for adding a principle or materially expanding
  guidance; PATCH for clarification and wording that does not change what is required.
- **Compliance review**: every pull request is reviewed against these principles. A change that
  violates one MUST either be revised or arrive with an amendment that permits it. Added complexity
  MUST be justified in the PR description against the simpler alternative that was rejected.
- **Runtime guidance**: `CLAUDE.md` holds the operational detail (commands, architecture, file
  layout) for day-to-day work. It elaborates this constitution and MUST NOT contradict it.

**Version**: 1.0.0 | **Ratified**: 2026-08-04 | **Last Amended**: 2026-08-04
