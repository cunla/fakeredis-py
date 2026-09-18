from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any

import fakeredis._msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import CommandItem, Int, Key, command
from fakeredis._helpers import OK, SimpleError, SimpleString, casematch, casematch_any, current_time
from fakeredis.commands_mixins._mixin_base import CommandsMixinBase
from fakeredis.model import StreamEntryKey, StreamGroup, StreamRangeTest, XStream
from fakeredis.model._stream import MAX_KEY, MIN_KEY


@dataclass
class _AddTrimArgs:
    """The options of XADD and XTRIM, and XADD's entry ID, as redis' streamParseAddOrTrimArgsOrReply leaves them."""

    maxlen: int | None = None
    minid: StreamEntryKey | None = None
    approx: bool = False
    limit: int = 0  # the most entries to trim, 0 for no limit
    ref_policy: bytes = b"KEEPREF"
    nomkstream: bool = False
    idmp_pid: bytes | None = None
    idmp_iid: bytes | None = None  # None with a producer ID for IDMPAUTO
    entry_id: StreamEntryKey | None = None  # None for `*`
    seq_given: bool = True  # False for `ms-*`
    id_index: int = 0  # the position of XADD's entry ID in its arguments


class StreamsCommandsMixin(CommandsMixinBase):
    @command(name="XADD", fixed=(Key(),), repeat=(bytes,))
    def xadd(self, key: CommandItem, *args: bytes) -> bytes | None:
        if len(args) < 3:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("xadd"))
        opts = self._parse_add_trim_args(args, xadd=True)
        fields = args[opts.id_index + 1 :]
        if len(fields) < 2 or len(fields) % 2 != 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("xadd"))
        if opts.entry_id == MIN_KEY and opts.seq_given:
            raise SimpleError(msgs.XADD_ID_ZERO_MSG)
        if key.value is None and opts.nomkstream:
            return None
        stream = self._stream_value(key) or XStream()
        idempotent_id = b""
        if opts.idmp_pid is not None:
            idempotent_id = opts.idmp_iid if opts.idmp_iid is not None else hex(hash(fields)).encode()
            existing = stream.idmp_lookup(opts.idmp_pid, idempotent_id)
            if existing is not None:
                return existing.encode()
        if stream.last_id == MAX_KEY:
            raise SimpleError(msgs.XADD_IDS_EXHAUSTED_MSG)
        entry_key = stream.next_id(opts.entry_id, opts.seq_given)
        if entry_key is None:
            raise SimpleError(msgs.XADD_ID_LOWER_THAN_LAST)
        stream.add(fields, entry_key, *self._stream_node_limits())
        if opts.idmp_pid is not None:
            stream.idmp_record(opts.idmp_pid, idempotent_id, entry_key)
        if opts.maxlen is not None or opts.minid is not None:
            self._trim_stream(stream, opts)
        key.update(stream)
        return entry_key.encode()

    @command(name="XTRIM", fixed=(Key(),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def xtrim(self, key: CommandItem, *args: bytes) -> int:
        if len(args) < 2:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("xtrim"))
        opts = self._parse_add_trim_args(args, xadd=False)
        stream = self._stream_value(key)
        if stream is None:
            return 0
        trimmed = self._trim_stream(stream, opts)
        if trimmed:
            key.updated()
        return trimmed

    def _parse_add_trim_args(self, args: tuple[bytes, ...], xadd: bool) -> _AddTrimArgs:
        """Parse the options XADD and XTRIM share, in any order, and for XADD the entry ID that ends them."""
        opts = _AddTrimArgs()
        # Consumer group reference policies and idempotent producers are Redis-only, from 8.2 and 8.6 respectively.
        ref_policies = self.server_type == "redis" and self.version >= (8, 2)
        idmp = self.server_type == "redis" and self.version >= (8, 6)
        ref_policy_given = limit_given = False
        i = 0
        while i < len(args):
            opt, more = args[i], len(args) - 1 - i
            if xadd and opt == b"*":
                break
            if casematch_any(opt, b"maxlen", b"minid") and more:
                if opts.maxlen is not None or opts.minid is not None:
                    raise SimpleError(msgs.XTRIM_MAXLEN_AND_MINID_MSG)
                opts.approx = more >= 2 and args[i + 1] == b"~"
                if more >= 2 and args[i + 1] in (b"~", b"="):
                    i += 1
                i += 1
                if casematch(opt, b"maxlen"):
                    opts.maxlen = Int.decode(args[i])
                    if opts.maxlen < 0:
                        raise SimpleError(msgs.XTRIM_MAXLEN_NEGATIVE_MSG)
                else:
                    opts.minid = StreamEntryKey.parse_str(args[i])
            elif casematch(opt, b"limit") and more:
                i += 1
                opts.limit = Int.decode(args[i])
                if opts.limit < 0:
                    raise SimpleError(msgs.XTRIM_LIMIT_NEGATIVE_MSG)
                limit_given = True
            elif ref_policies and not ref_policy_given and casematch_any(opt, b"keepref", b"delref", b"acked"):
                opts.ref_policy = opt.upper()
                ref_policy_given = True
            elif xadd and casematch(opt, b"nomkstream"):
                opts.nomkstream = True
            elif xadd and idmp and casematch(opt, b"idmpauto") and more:
                if opts.idmp_pid is not None:
                    raise SimpleError(msgs.XADD_IDMP_TWICE_MSG)
                if not args[i + 1]:
                    raise SimpleError(msgs.XADD_IDMPAUTO_EMPTY_PID_MSG)
                opts.idmp_pid = args[i + 1]
                i += 1
            elif xadd and idmp and casematch(opt, b"idmp") and more >= 2:
                if opts.idmp_pid is not None:
                    raise SimpleError(msgs.XADD_IDMP_TWICE_MSG)
                if not args[i + 1]:
                    raise SimpleError(msgs.XADD_IDMP_EMPTY_PID_MSG)
                if not args[i + 2]:
                    raise SimpleError(msgs.XADD_IDMP_EMPTY_IID_MSG)
                opts.idmp_pid, opts.idmp_iid = args[i + 1], args[i + 2]
                i += 2
            elif xadd:
                # Anything else is the entry ID; `ms-*` arrived in Redis 7.
                opts.entry_id, opts.seq_given = StreamEntryKey.parse_xadd_id(opt, allow_seq_star=self.version >= (7,))
                if opts.idmp_pid is not None:
                    raise SimpleError(msgs.XADD_IDMP_EXPLICIT_ID_MSG)
                break
            else:
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
            i += 1
        opts.id_index = i

        trims = opts.maxlen is not None or opts.minid is not None
        if opts.limit and not trims:
            raise SimpleError(msgs.XTRIM_LIMIT_WITHOUT_STRATEGY_MSG)
        if not xadd and not trims:
            raise SimpleError(msgs.XTRIM_NO_STRATEGY_MSG)
        if limit_given and not opts.approx:
            raise SimpleError(msgs.XTRIM_LIMIT_WITHOUT_APPROX_MSG)
        if not limit_given and opts.approx:
            # Approximate trimming is kept from doing too much at once: 100 nodes' worth of entries by default.
            node_max_entries = self._stream_node_limits()[0]
            opts.limit = min(100 * node_max_entries, 1000000) if node_max_entries > 0 else 10000
        return opts

    def _trim_stream(self, stream: XStream, opts: _AddTrimArgs) -> int:
        if self.server_type == "kividb":
            # KiviDB trims exactly, `~` or not, and takes no notice of LIMIT.
            return stream.trim(opts.maxlen, opts.minid, ref_policy=opts.ref_policy)
        if opts.approx and opts.ref_policy != b"KEEPREF" and self.version < (8, 6):
            # Before Redis 8.6, approximate trimming stopped short of any node it could not drop whole, which only
            # KEEPREF ever does.
            return 0
        return stream.trim(opts.maxlen, opts.minid, opts.approx, opts.limit, opts.ref_policy)

    def _stream_node_limits(self) -> tuple[int, int]:
        """The `stream-node-max-entries` and `stream-node-max-bytes` settings, which decide how entries are packed
        into nodes, and so how much approximate trimming drops."""
        limits = []
        for name, default in ((b"stream-node-max-entries", 100), (b"stream-node-max-bytes", 4096)):
            try:
                limits.append(int(self._server.config.get(name, default)))
            except ValueError:
                limits.append(default)
        return limits[0], limits[1]

    @staticmethod
    def _stream_value(key: CommandItem) -> XStream | None:
        if key.value is not None and not isinstance(key.value, XStream):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        return key.value

    @command(name="XLEN", fixed=(Key(XStream),))
    def xlen(self, key: CommandItem) -> int:
        return len(key.value)

    @command(name="XRANGE", fixed=(Key(XStream), StreamRangeTest, StreamRangeTest), repeat=(bytes,))
    def xrange(self, key: CommandItem, _min: StreamRangeTest, _max: StreamRangeTest, *args: bytes) -> list[bytes]:
        (count,), _ = extract_args(args, ("+count",))
        return self._xrange(key.value, _min, _max, False, count)

    @command(name="XREVRANGE", fixed=(Key(XStream), StreamRangeTest, StreamRangeTest), repeat=(bytes,))
    def xrevrange(self, key: CommandItem, _min: StreamRangeTest, _max: StreamRangeTest, *args: bytes) -> list[bytes]:
        (count,), _ = extract_args(args, ("+count",))
        return self._xrange(key.value, _max, _min, True, count)

    @command(name="XREAD", fixed=(bytes,), repeat=(bytes,), flags=msgs.FLAG_SKIP_CONVERT_TO_RESP2)
    def xread(self, *args: bytes) -> None | dict[bytes, Any] | list[list[Any]]:
        ((count, timeout), left_args) = extract_args(args, ("+count", "+block"), error_on_unexpected=False)
        if len(left_args) < 3 or not casematch(left_args[0], b"STREAMS") or len(left_args) % 2 != 1:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        left_args = left_args[1:]
        num_streams = int(len(left_args) / 2)

        stream_start_id_list: list[tuple[bytes, StreamRangeTest]] = []  # (name, start_id)
        for i in range(num_streams):
            item = CommandItem(left_args[i], self._db, item=self._db.get(left_args[i]), default=None)
            start_id = self._parse_start_id(item, left_args[i + num_streams])
            stream_start_id_list.append((left_args[i], start_id))
        if timeout is None:
            return self._empty_stream_read_reply(
                self._xread(stream_start_id_list, count, blocking=False, first_pass=False)
            )
        return self._blocking(  # type: ignore[no-any-return]
            timeout / 1000.0,
            functools.partial(self._xread, stream_start_id_list, count, True),
            self._empty_stream_read_reply,
        )

    @command(name="XREADGROUP", fixed=(bytes, bytes, bytes), repeat=(bytes,))
    def xreadgroup(
        self, group_const: bytes, group_name: bytes, consumer_name: bytes, *args: bytes
    ) -> dict[bytes, Any] | list[list[Any]] | None:
        if not casematch(b"GROUP", group_const):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        (count, timeout, noack, min_idle_time), left_args = extract_args(
            args, ("+count", "+block", "noack", "+claim"), error_on_unexpected=False
        )
        if min_idle_time is not None and min_idle_time < 0:
            raise SimpleError(msgs.XREADGROUP_CLAIM_NEGATIVE_MSG)
        if len(left_args) < 3 or not casematch(left_args[0], b"STREAMS") or len(left_args) % 2 != 1:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        left_args = left_args[1:]
        num_streams = int(len(left_args) / 2)

        # List of (group, stream_name, stream start-id)
        group_params: list[tuple[StreamGroup, bytes, bytes]] = []
        for i in range(num_streams):
            item = CommandItem(left_args[i], self._db, item=self._db.get(left_args[i]), default=None)
            if item.value is None:
                raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
            group: StreamGroup = item.value.group_get(group_name)
            if not group:
                raise SimpleError(
                    msgs.XREADGROUP_KEY_OR_GROUP_NOT_FOUND_MSG.format(left_args[i].decode(), group_name.decode())
                )
            group_params.append((group, left_args[i], left_args[i + num_streams]))
        if timeout is None:
            return self._xreadgroup_reply(
                self._xreadgroup(consumer_name, group_params, count, noack, min_idle_time, False)
            )
        return self._blocking(  # type: ignore[no-any-return]
            timeout / 1000.0,
            functools.partial(self._xreadgroup, consumer_name, group_params, count, noack, min_idle_time),
            self._xreadgroup_reply,
        )

    @command(name="XDEL", fixed=(Key(XStream),), repeat=(bytes,))
    def xdel(self, key: CommandItem, *args: bytes) -> int:
        if len(args) == 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("xdel"))
        res: int = key.value.delete(args)
        return res

    @command(name="XACK", fixed=(Key(XStream), bytes), repeat=(bytes,))
    def xack(self, key: CommandItem, group_name: bytes, *args: bytes) -> int:
        if len(args) == 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("xack"))
        if key.value is None:
            return 0
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            return 0
        return group.ack(args)  # type: ignore

    @command(
        name="XPENDING",
        fixed=(Key(XStream), bytes),
        repeat=(bytes,),
        flags=msgs.FLAG_DO_NOT_CREATE,
    )
    def xpending(self, key: CommandItem, group_name: bytes, *args: bytes) -> int | list[Any]:
        # Dragonfly looks the key up before the group, so a missing stream is "no such key" and a missing group names
        # only the group it could not find.
        is_dragonfly = self.server_type == "dragonfly"
        if key.value is None:
            if is_dragonfly:
                raise SimpleError(msgs.NO_KEY_MSG)
            raise SimpleError(msgs.XNACK_NOGROUP_MSG.format(key.key.decode(), group_name.decode()))
        idle, start, end, count, consumer = None, None, None, None, None

        if len(args) > 4 and casematch(b"idle", args[0]):  # Idle
            idle = Int.decode(args[1])
            args = args[2:]
        if 0 < len(args) < 3:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        elif len(args) >= 3:
            start, end, count = (
                StreamRangeTest.decode(args[0]),
                StreamRangeTest.decode(args[1]),
                Int.decode(args[2]),
            )
            if len(args) > 3:
                consumer = args[3]
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            if is_dragonfly:
                raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key.key.decode()))
            raise SimpleError(msgs.XNACK_NOGROUP_MSG.format(key.key.decode(), group_name.decode()))

        if start is not None:
            return group.pending(idle, start, end, count, consumer)
        else:
            return group.pending_summary()

    @command(name="XGROUP CREATE", fixed=(Key(XStream), bytes, bytes), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def xgroup_create(self, key: CommandItem, group_name: bytes, start_key: bytes, *args: bytes) -> SimpleString:
        (mkstream, entries_read_arg), _ = extract_args(args, ("mkstream", "+entriesread"))
        entries_read = self._entries_read_arg(entries_read_arg)
        if key.key not in self._db and not mkstream:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        stream: XStream = key.value
        last_delivered_key = stream.last_id if start_key == b"$" else StreamEntryKey.parse_str(start_key)
        if stream.group_get(group_name) is not None:
            raise SimpleError(msgs.XGROUP_BUSYGROUP)
        if self.server_type == "dragonfly":
            entries_read = None  # Dragonfly takes ENTRIESREAD here, but ignores it
        stream.group_add(group_name, last_delivered_key, self._clamp_entries_read(stream, entries_read))
        key.updated()
        return OK

    @command(name="XGROUP SETID", fixed=(Key(XStream), bytes, bytes), repeat=(bytes,))
    def xgroup_setid(self, key: CommandItem, group_name: bytes, start_key: bytes, *args: bytes) -> SimpleString:
        (entries_read_arg,), _ = extract_args(args, ("+entriesread",))
        entries_read = self._entries_read_arg(entries_read_arg)
        if key.key not in self._db:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        stream: XStream = key.value
        group = stream.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key))
        # Unlike CREATE, SETID also takes `-` and `+`.
        if start_key in (b"$", b"-", b"+"):
            last_delivered_key = {b"$": stream.last_id, b"-": MIN_KEY, b"+": MAX_KEY}[start_key]
        elif self.server_type == "dragonfly" and not StreamRangeTest.valid_key(start_key):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        else:
            last_delivered_key = StreamEntryKey.parse_str(start_key)
        if entries_read_arg is None and self.server_type == "dragonfly":
            entries_read = group.entries_read  # Dragonfly keeps the group's count unless given ENTRIESREAD
        group.set_id(last_delivered_key, self._clamp_entries_read(stream, entries_read))
        return OK

    def _entries_read_arg(self, entries_read: int | None) -> int | None:
        """The ENTRIESREAD of XGROUP CREATE/SETID, with -1 (like no ENTRIESREAD at all) meaning unknown: None."""
        if entries_read is not None and entries_read < -1:
            raise SimpleError(
                msgs.SYNTAX_ERROR_MSG if self.server_type == "dragonfly" else msgs.XGROUP_ENTRIES_READ_MSG
            )
        return None if entries_read == -1 else entries_read

    def _clamp_entries_read(self, stream: XStream, entries_read: int | None) -> int | None:
        # Since 8.2.3 redis caps ENTRIESREAD at the number of entries the stream has ever taken in.
        if entries_read is not None and self.server_type == "redis" and self.version >= (8, 2, 3):
            return min(entries_read, stream.entries_added)
        return entries_read

    @property
    def _trim_aware_lag(self) -> bool:
        """Whether XINFO works out a group's lag with the shortcuts Redis 7.4 added (see `StreamGroup.lag`)."""
        return self.server_type == "redis" and self.version >= (7, 4)

    @command(name="XGROUP DESTROY", fixed=(Key(XStream), bytes), repeat=())
    def xgroup_destroy(self, key: CommandItem, group_name: bytes) -> int:
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        res: int = key.value.group_delete(group_name)
        return res

    @command(name="XGROUP CREATECONSUMER", fixed=(Key(XStream), bytes, bytes), repeat=())
    def xgroup_createconsumer(self, key: CommandItem, group_name: bytes, consumer_name: bytes) -> int:
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key))
        return group.add_consumer(consumer_name)

    @command(name="XGROUP DELCONSUMER", fixed=(Key(XStream), bytes, bytes), repeat=())
    def xgroup_delconsumer(self, key: CommandItem, group_name: bytes, consumer_name: bytes) -> int:
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key))
        return group.del_consumer(consumer_name)

    @command(name="XINFO GROUPS", fixed=(Key(XStream),), repeat=(), flags=msgs.FLAG_DO_NOT_CREATE)
    def xinfo_groups(self, key: CommandItem) -> list[dict[bytes, Any]]:
        if key.value is None:
            raise SimpleError(msgs.NO_KEY_MSG)
        res: list[dict[bytes, Any]] = key.value.groups_info(self._trim_aware_lag)
        if self.server_type == "dragonfly":
            # Dragonfly uses -1 as its "lag unknown" sentinel and reports it as nil.
            for group in res:
                if group.get(b"lag") == -1:
                    group[b"lag"] = None
        return res

    @command(name="XINFO STREAM", fixed=(Key(XStream),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def xinfo_stream(self, key: CommandItem, *args: bytes) -> list[bytes]:
        (full,), _ = extract_args(args, ("full",))
        if key.value is None:
            raise SimpleError(msgs.NO_KEY_MSG)
        res: list[bytes] = key.value.stream_info(full, self._trim_aware_lag)
        if self.server_type == "dragonfly" and self._client_info.protocol_version == 3:
            # An empty stream's first/last entry is a null array on dragonfly, where redis sends nil; under RESP3 a
            # client reads that back as an empty array.
            for i in range(0, len(res) - 1, 2):
                if res[i] in (b"first-entry", b"last-entry") and res[i + 1] is None:
                    res[i + 1] = []  # type: ignore[call-overload]
        return res

    @command(name="XINFO CONSUMERS", fixed=(Key(XStream), bytes), repeat=())
    def xinfo_consumers(self, key: CommandItem, group_name: bytes) -> list[dict[str, bytes | int]]:
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key))
        res: list[dict[str, bytes | int]] = group.consumers_info()
        return res

    @command(name="XCLAIM", fixed=(Key(XStream), bytes, bytes, Int, bytes), repeat=(bytes,))
    def xclaim(
        self, key: CommandItem, group_name: bytes, consumer_name: bytes, min_idle_ms: int, *args: bytes
    ) -> list[bytes] | list[list[bytes | list[bytes]]]:
        stream = key.value
        if stream is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = stream.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key))

        (idle, _time, retrycount, force, justid), msg_ids = extract_args(
            args,
            ("+idle", "+time", "+retrycount", "force", "justid"),
            error_on_unexpected=False,
            left_from_first_unexpected=False,
        )

        if idle is not None and idle > 0 and _time is None:
            _time = current_time() - idle
        msgs_claimed, _ = group.claim(
            min_idle_ms, msg_ids, consumer_name, _time, force, justid=bool(justid), retrycount=retrycount
        )

        if justid:
            return [msg.encode() for msg in msgs_claimed]
        return [stream.format_record(msg) for msg in msgs_claimed]

    @command(name="XAUTOCLAIM", fixed=(Key(XStream), bytes, bytes, Int, bytes), repeat=(bytes,))
    def xautoclaim(
        self, key: CommandItem, group_name: bytes, consumer_name: bytes, min_idle_ms: int, start: bytes, *args: bytes
    ) -> list[bytes | list[bytes | list[tuple[bytes, list[bytes]]]]]:
        (count, justid), _ = extract_args(args, ("+count", "justid"))
        count = count or 100
        stream = key.value
        if stream is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = stream.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key))

        keys, next_key = group.read_pel_msgs(min_idle_ms, start, count)
        msgs_claimed, msgs_removed = group.claim(min_idle_ms, keys, consumer_name, None, False, justid=bool(justid))

        res: list[bytes | list[bytes | list[tuple[bytes, list[bytes]]]]] = [
            next_key.encode() if next_key is not None else b"0-0",
            [msg.encode() for msg in msgs_claimed] if justid else [stream.format_record(msg) for msg in msgs_claimed],
        ]
        if self.version >= (7,):
            res.append([msg.encode() for msg in msgs_removed])
        return res

    @command(name="XDELEX", fixed=(Key(XStream),), repeat=(bytes,), server_types=("redis", "kividb"))
    def xdelex(self, key: CommandItem, *args: bytes) -> list[int]:
        """XDELEX key [KEEPREF | DELREF | ACKED] IDS numids id [id ...]"""
        mode, ids = self._parse_xdelex_args(args, "XDELEX")
        if key.value is None:
            return [-1] * len(ids)
        res = key.value.delete_ex(ids, mode)
        key.updated()
        return res

    # KiviDB has XACKDEL, but shaped like XACK - `XACKDEL key group id [id ...]`, with no ref-policy
    # and no IDS count - so the Redis form below would answer where the real server errors.
    @command(name="XACKDEL", fixed=(Key(XStream), bytes), repeat=(bytes,), server_types=("redis",))
    def xackdel(self, key: CommandItem, group_name: bytes, *args: bytes) -> list[int]:
        """XACKDEL key group [KEEPREF | DELREF | ACKED] IDS numids id [id ...]"""
        mode, ids = self._parse_xdelex_args(args, "XACKDEL")
        if key.value is None:
            return [-1] * len(ids)
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            return [-1] * len(ids)
        res = key.value.ackdel(group, ids, mode)
        key.updated()
        return res

    @staticmethod
    def _parse_xdelex_args(args: tuple, cmd_name: str):
        """Parse [KEEPREF|DELREF|ACKED] IDS numids id [id ...] for XDELEX/XACKDEL."""
        i = 0
        mode = b"KEEPREF"
        if i < len(args) and (casematch_any(args[i], b"KEEPREF", b"DELREF", b"ACKED")):
            mode = args[i].upper()
            i += 1
        if i >= len(args) or not casematch(args[i], b"IDS"):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        i += 1
        if i >= len(args):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        num_ids = Int.decode(args[i])
        i += 1
        if num_ids < 1 or i + num_ids > len(args):
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format(cmd_name.lower()))
        ids = list(args[i : i + num_ids])
        return mode, ids

    @command(name="XNACK", fixed=(Key(XStream), bytes), repeat=(bytes,), server_types=("redis", "kividb"))
    def xnack(self, key: CommandItem, group_name: bytes, *args: bytes) -> int:
        """XNACK key group <SILENT | FAIL | FATAL> IDS numids id [id ...] [RETRYCOUNT count] [FORCE]"""
        # As for INCREX, KiviDB has XNACK despite reporting redis_version 7.0.15.
        if self.version < (8, 8) and self.server_type != "kividb":
            raise SimpleError(msgs.UNKNOWN_COMMAND_MSG.format("XNACK"))
        if len(args) < 3:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("XNACK"))
        if not casematch_any(args[0], b"SILENT", b"FAIL", b"FATAL"):
            raise SimpleError(msgs.XNACK_INVALID_MODE_MSG)
        mode = args[0].upper()
        if not casematch(args[1], b"IDS"):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        num_ids = Int.decode(args[2])
        if len(args) < 3 + num_ids:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        ids, remaining = list(args[3 : 3 + num_ids]), args[3 + num_ids :]
        (retry_count, force), _ = extract_args(remaining, ("+retrycount", "force"))

        if key.value is None:
            raise SimpleError(msgs.XNACK_NOGROUP_MSG.format(key.key.decode(), group_name.decode()))
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XNACK_NOGROUP_MSG.format(key.key.decode(), group_name.decode()))
        return group.nack_entries(ids, mode, retry_count, bool(force))

    @command(name="XIDMPRECORD", fixed=(Key(XStream), bytes, bytes, bytes), repeat=(), server_types=("redis",))
    def xidmprecord(self, key: CommandItem, pid: bytes, iid: bytes, stream_id: bytes) -> SimpleString:
        if key.value is None:
            raise SimpleError(msgs.NO_KEY_MSG)
        key.value.record_idmp(pid, iid, stream_id)
        key.updated()
        return OK

    @command(name="XCFGSET", fixed=(Key(XStream),), repeat=(bytes,))
    def xcfgset(self, key: CommandItem, *args: bytes) -> SimpleString:
        stream = key.value
        if stream is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        (duration, max_size), _ = extract_args(args, ("+idmp-duration", "+idmp-maxsize"))
        if duration is not None:
            if 1 <= duration <= 86400:
                stream.set_idmp_duration(duration)
            else:
                raise SimpleError("ERR IDMP-DURATION must be between 1 and 86400 seconds")
        if max_size is not None:
            if 1 <= max_size <= 10000:
                stream.set_idmp_duration(max_size)
            else:
                raise SimpleError("ERR IDMP-MAXSIZE must be between 1 and 10000 entries")
        key.update(stream)
        return OK

    @staticmethod
    def _xrange(
        stream: XStream,
        _min: StreamRangeTest,
        _max: StreamRangeTest,
        reverse: bool,
        count: int | None,
    ) -> list[bytes]:
        if stream is None:
            return []
        if count is None:
            count = len(stream)
        res = stream.irange(_min, _max, reverse=reverse)
        return res[:count]

    def _xreadgroup(
        self,
        consumer_name: bytes,
        group_params: list[tuple[StreamGroup, bytes, bytes]],
        count: int | None,
        noack: bool,
        min_idle_time: int | None,
        first_pass: bool,
    ) -> dict[bytes, Any] | None:
        res: dict[bytes, Any] = {}
        claimed_any = False
        for group, stream_name, start_id in group_params:
            claimed: list[Any] = []
            # CLAIM only applies when reading new entries, not the consumer history
            claim_active = False
            if min_idle_time is not None and start_id == b">":
                claim_active = True
                claimed = group.claim_for_read(min_idle_time, consumer_name, count)
                claimed_any = claimed_any or len(claimed) > 0
            remaining_count = count - len(claimed) if count is not None else None
            stream_results: list[Any] = group.group_read(consumer_name, start_id, remaining_count, noack)
            if first_pass and (count is None) and not claimed_any:
                return None
            if claim_active:
                # With CLAIM, claimed entries are reported before new entries, and every entry carries idle time and
                # delivery count (0 for new entries).
                stream_results = claimed + [record + [0, 0] for record in stream_results]
            if len(stream_results) > 0 or start_id != b">":
                res[stream_name] = stream_results
        return res

    def _empty_stream_read_reply(self, res: dict[bytes, Any] | list[Any] | None) -> dict[bytes, Any] | list[Any] | None:
        """Shape an XREAD/XREADGROUP reply that matched nothing, under RESP3.

        Redis answers with an empty map; dragonfly answers with an empty array. Note that redis-py's RESP3 parser
        assumes the map and cannot consume dragonfly's reply. Under RESP2 both send a null array, so the reply is left
        as it is.
        """
        if not res and self.server_type == "dragonfly" and self._client_info.protocol_version == 3:
            return []
        return res

    def _xreadgroup_reply(self, res: dict[bytes, Any] | None) -> dict[bytes, Any] | list[Any] | None:
        """Turn the streams XREADGROUP matched into the reply for the protocol in use."""
        if self._client_info.protocol_version == 2:
            return [[k, v] for k, v in res.items()] if res else None
        return self._empty_stream_read_reply(res)

    def _xread(
        self, stream_start_id_list: list[tuple[bytes, StreamRangeTest]], count: int, blocking: bool, first_pass: bool
    ) -> None | dict[bytes, Any] | list[list[bytes | list[tuple[bytes, list[bytes]]]]]:
        max_inf = StreamRangeTest.decode(b"+")
        res: dict[bytes, Any] = {}
        for stream_name, start_id in stream_start_id_list:
            item = CommandItem(stream_name, self._db, item=self._db.get(stream_name), default=None)
            stream_results = self._xrange(item.value, start_id, max_inf, False, count)
            if len(stream_results) > 0:
                res[item.key] = stream_results

        if self._resp_version == 2:
            # On blocking read, and there are no results, return None (instead of an empty list)
            if blocking and len(res) == 0:
                return None
            return [[k, v] for k, v in res.items()]
        if not res:
            # None keeps `_blocking` waiting; the caller shapes the reply once it gives up.
            return None if blocking else res
        if blocking and not first_pass and self.server_type == "dragonfly":
            # A blocking read that was woken by a new entry is answered by dragonfly with the RESP2-style array, not the
            # map it sends when the entry was already there.
            return [[k, v] for k, v in res.items()]
        return res

    @staticmethod
    def _parse_start_id(key: CommandItem, s: bytes) -> StreamRangeTest:
        if s == b"$":
            if key.value is None:
                return StreamRangeTest.decode(b"0-0")
            return StreamRangeTest.decode(key.value.last_item_key(), exclusive=True)
        return StreamRangeTest.decode(s, exclusive=True)
