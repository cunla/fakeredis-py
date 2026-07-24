import functools
from typing import List, Union, Tuple, Callable, Optional, Any, Dict

import fakeredis._msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import Key, command, CommandItem, Int
from fakeredis._helpers import SimpleError, casematch, OK, current_time, SimpleString, casematch_any
from fakeredis.model import XStream, StreamRangeTest, StreamGroup, StreamEntryKey
from fakeredis.commands_mixins._mixin_base import CommandsMixinBase


class StreamsCommandsMixin(CommandsMixinBase):
    _blocking: Callable[[Optional[Union[float, int]], Callable[[bool], Any]], Any]

    @command(name="XADD", fixed=(Key(),), repeat=(bytes,))
    def xadd(self, key: CommandItem, *args: bytes) -> Optional[bytes]:
        (nomkstream, limit, maxlen, minid, idmpauto, idmp), left_args = extract_args(
            args, ("nomkstream", "+limit", "~+maxlen", "~minid", "*idmpauto", "**idmp"), error_on_unexpected=False
        )
        if nomkstream and key.value is None:
            return None
        entry_key = left_args[0]
        elements = left_args[1:]
        if not elements or len(elements) % 2 != 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("XADD"))
        stream = key.value if key.value is not None else XStream()
        if self.version < (7,) and entry_key != b"*" and not StreamRangeTest.valid_key(entry_key):
            raise SimpleError(msgs.XADD_INVALID_ID)
        producer_id, idempotent_id = None, None
        if idmp is not None:
            producer_id, idempotent_id = idmp
        if idmpauto is not None:
            producer_id = idmpauto
        res: Optional[bytes] = stream.add(
            elements, entry_key=entry_key, producer_id=producer_id, idempotent_id=idempotent_id
        )
        if res is None:
            if not StreamRangeTest.valid_key(left_args[0]):
                raise SimpleError(msgs.XADD_INVALID_ID)
            raise SimpleError(msgs.XADD_ID_LOWER_THAN_LAST)
        if maxlen is not None or minid is not None:
            stream.trim(max_length=maxlen, start_entry_key=minid, limit=limit)
        key.update(stream)
        return res

    @command(name="XTRIM", fixed=(Key(XStream),), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def xtrim(self, key: CommandItem, *args: bytes) -> int:
        (limit, maxlen, minid), _ = extract_args(args, ("+limit", "~+maxlen", "~minid"))
        if maxlen is not None and minid is not None:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if maxlen is None and minid is None:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        stream = key.value or XStream()
        res = stream.trim(max_length=maxlen, start_entry_key=minid, limit=limit)
        key.update(stream)
        return res

    @command(name="XLEN", fixed=(Key(XStream),))
    def xlen(self, key: CommandItem) -> int:
        return len(key.value)

    @command(name="XRANGE", fixed=(Key(XStream), StreamRangeTest, StreamRangeTest), repeat=(bytes,))
    def xrange(self, key: CommandItem, _min: StreamRangeTest, _max: StreamRangeTest, *args: bytes) -> List[bytes]:
        (count,), _ = extract_args(args, ("+count",))
        return self._xrange(key.value, _min, _max, False, count)

    @command(name="XREVRANGE", fixed=(Key(XStream), StreamRangeTest, StreamRangeTest), repeat=(bytes,))
    def xrevrange(self, key: CommandItem, _min: StreamRangeTest, _max: StreamRangeTest, *args: bytes) -> List[bytes]:
        (count,), _ = extract_args(args, ("+count",))
        return self._xrange(key.value, _max, _min, True, count)

    @command(name="XREAD", fixed=(bytes,), repeat=(bytes,), flags=msgs.FLAG_SKIP_CONVERT_TO_RESP2)
    def xread(self, *args: bytes) -> Union[None, Dict[bytes, Any], List[List[Any]]]:
        ((count, timeout), left_args) = extract_args(args, ("+count", "+block"), error_on_unexpected=False)
        if len(left_args) < 3 or not casematch(left_args[0], b"STREAMS") or len(left_args) % 2 != 1:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        left_args = left_args[1:]
        num_streams = int(len(left_args) / 2)

        stream_start_id_list: List[Tuple[bytes, StreamRangeTest]] = []  # (name, start_id)
        for i in range(num_streams):
            item = CommandItem(left_args[i], self._db, item=self._db.get(left_args[i]), default=None)
            start_id = self._parse_start_id(item, left_args[i + num_streams])
            stream_start_id_list.append((left_args[i], start_id))
        if timeout is None:
            return self._xread(stream_start_id_list, count, blocking=False, first_pass=False)
        else:
            return self._blocking(  # type: ignore
                timeout / 1000.0,
                functools.partial(self._xread, stream_start_id_list, count, True),
            )

    @command(name="XREADGROUP", fixed=(bytes, bytes, bytes), repeat=(bytes,))
    def xreadgroup(
        self, group_const: bytes, group_name: bytes, consumer_name: bytes, *args: bytes
    ) -> Optional[Union[Dict[bytes, Any], List[List[Any]]]]:
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
        group_params: List[Tuple[StreamGroup, bytes, bytes]] = []
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
            res = self._xreadgroup(consumer_name, group_params, count, noack, min_idle_time, False)
        else:
            res = self._blocking(
                timeout / 1000.0,
                functools.partial(self._xreadgroup, consumer_name, group_params, count, noack, min_idle_time),
            )
        if self._client_info.protocol_version == 2:
            return [[k, v] for k, v in res.items()] if res else None
        return res

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
    def xpending(self, key: CommandItem, group_name: bytes, *args: bytes) -> Union[int, List[Any]]:
        if key.value is None:
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
            raise SimpleError(msgs.XNACK_NOGROUP_MSG.format(key.key.decode(), group_name.decode()))

        if start is not None:
            return group.pending(idle, start, end, count, consumer)
        else:
            return group.pending_summary()

    @command(name="XGROUP CREATE", fixed=(Key(XStream), bytes, bytes), repeat=(bytes,), flags=msgs.FLAG_LEAVE_EMPTY_VAL)
    def xgroup_create(self, key: CommandItem, group_name: bytes, start_key: bytes, *args: bytes) -> SimpleString:
        (mkstream, entries_read), _ = extract_args(args, ("mkstream", "+entriesread"))
        if key.value is None and not mkstream:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        if key.value.group_get(group_name) is not None:
            raise SimpleError(msgs.XGROUP_BUSYGROUP)
        key.value.group_add(group_name, start_key, entries_read)
        key.updated()
        return OK

    @command(name="XGROUP SETID", fixed=(Key(XStream), bytes, bytes), repeat=(bytes,))
    def xgroup_setid(self, key: CommandItem, group_name: bytes, start_key: bytes, *args: bytes) -> SimpleString:
        (entries_read,), _ = extract_args(args, ("+entriesread",))
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group = key.value.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key))
        group.set_id(start_key, entries_read)
        return OK

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
    def xinfo_groups(self, key: CommandItem) -> Dict[bytes, Any]:
        if key.value is None:
            raise SimpleError(msgs.NO_KEY_MSG)
        res: Dict[bytes, Any] = key.value.groups_info()
        return res

    @command(name="XINFO STREAM", fixed=(Key(XStream),), repeat=(bytes,), flags=msgs.FLAG_DO_NOT_CREATE)
    def xinfo_stream(self, key: CommandItem, *args: bytes) -> List[bytes]:
        (full,), _ = extract_args(args, ("full",))
        if key.value is None:
            raise SimpleError(msgs.NO_KEY_MSG)
        res: List[bytes] = key.value.stream_info(full)
        return res

    @command(name="XINFO CONSUMERS", fixed=(Key(XStream), bytes), repeat=())
    def xinfo_consumers(self, key: CommandItem, group_name: bytes) -> List[Dict[str, Union[bytes, int]]]:
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key))
        res: List[Dict[str, Union[bytes, int]]] = group.consumers_info()
        return res

    @command(name="XCLAIM", fixed=(Key(XStream), bytes, bytes, Int, bytes), repeat=(bytes,))
    def xclaim(
        self, key: CommandItem, group_name: bytes, consumer_name: bytes, min_idle_ms: int, *args: bytes
    ) -> Union[List[bytes], List[List[Union[bytes, List[bytes]]]]]:
        stream = key.value
        if stream is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = stream.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key))

        (idle, _time, retry, force, justid), msg_ids = extract_args(
            args,
            ("+idle", "+time", "+retrycount", "force", "justid"),
            error_on_unexpected=False,
            left_from_first_unexpected=False,
        )

        if idle is not None and idle > 0 and _time is None:
            _time = current_time() - idle
        msgs_claimed, _ = group.claim(min_idle_ms, msg_ids, consumer_name, _time, force)

        if justid:
            return [msg.encode() for msg in msgs_claimed]
        return [stream.format_record(msg) for msg in msgs_claimed]

    @command(name="XAUTOCLAIM", fixed=(Key(XStream), bytes, bytes, Int, bytes), repeat=(bytes,))
    def xautoclaim(
        self, key: CommandItem, group_name: bytes, consumer_name: bytes, min_idle_ms: int, start: bytes, *args: bytes
    ) -> List[Union[bytes, List[Union[bytes, List[Tuple[bytes, List[bytes]]]]]]]:
        (count, justid), _ = extract_args(args, ("+count", "justid"))
        count = count or 100
        stream = key.value
        if stream is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = stream.group_get(group_name)
        if not group:
            raise SimpleError(msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key))

        keys: List[StreamEntryKey] = group.read_pel_msgs(min_idle_ms, start, count)
        msgs_claimed, msgs_removed = group.claim(min_idle_ms, keys, consumer_name, None, False)

        res: List[Union[bytes, List[Union[bytes, List[Tuple[bytes, List[bytes]]]]]]] = [
            max(msgs_claimed).encode() if len(msgs_claimed) > 0 else start,
            [msg.encode() for msg in msgs_claimed] if justid else [stream.format_record(msg) for msg in msgs_claimed],
        ]
        if self.version >= (7,):
            res.append([msg.encode() for msg in msgs_removed])
        return res

    @command(name="XDELEX", fixed=(Key(XStream),), repeat=(bytes,), server_types=("redis",))
    def xdelex(self, key: CommandItem, *args: bytes) -> List[int]:
        """XDELEX key [KEEPREF | DELREF | ACKED] IDS numids id [id ...]"""
        mode, ids = self._parse_xdelex_args(args, "XDELEX")
        if key.value is None:
            return [-1] * len(ids)
        res = key.value.delete_ex(ids, mode)
        key.updated()
        return res

    @command(name="XACKDEL", fixed=(Key(XStream), bytes), repeat=(bytes,), server_types=("redis",))
    def xackdel(self, key: CommandItem, group_name: bytes, *args: bytes) -> List[int]:
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

    @command(name="XNACK", fixed=(Key(XStream), bytes), repeat=(bytes,), server_types=("redis",))
    def xnack(self, key: CommandItem, group_name: bytes, *args: bytes) -> int:
        """XNACK key group <SILENT | FAIL | FATAL> IDS numids id [id ...] [RETRYCOUNT count] [FORCE]"""
        if self.version < (8, 8):
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
        count: Union[int, None],
    ) -> List[bytes]:
        if stream is None:
            return []
        if count is None:
            count = len(stream)
        res = stream.irange(_min, _max, reverse=reverse)
        return res[:count]

    def _xreadgroup(
        self,
        consumer_name: bytes,
        group_params: List[Tuple[StreamGroup, bytes, bytes]],
        count: Optional[int],
        noack: bool,
        min_idle_time: Optional[int],
        first_pass: bool,
    ) -> Optional[Dict[bytes, Any]]:
        res: Dict[bytes, Any] = {}
        claimed_any = False
        for group, stream_name, start_id in group_params:
            claimed: List[Any] = []
            # CLAIM only applies when reading new entries, not the consumer history
            claim_active = False
            if min_idle_time is not None and start_id == b">":
                claim_active = True
                claimed = group.claim_for_read(min_idle_time, consumer_name, count)
                claimed_any = claimed_any or len(claimed) > 0
            remaining_count = count - len(claimed) if count is not None else None
            stream_results: List[Any] = group.group_read(consumer_name, start_id, remaining_count, noack)
            if first_pass and (count is None) and not claimed_any:
                return None
            if claim_active:
                # With CLAIM, claimed entries are reported before new entries, and every
                # entry carries idle time and delivery count (0 for new entries).
                stream_results = claimed + [record + [0, 0] for record in stream_results]
            if len(stream_results) > 0 or start_id != b">":
                res[stream_name] = stream_results
        return res

    def _xread(
        self, stream_start_id_list: List[Tuple[bytes, StreamRangeTest]], count: int, blocking: bool, first_pass: bool
    ) -> Union[None, Dict[bytes, Any], List[List[Union[bytes, List[Tuple[bytes, List[bytes]]]]]]]:
        max_inf = StreamRangeTest.decode(b"+")
        res: Dict[bytes, Any] = {}
        for stream_name, start_id in stream_start_id_list:
            item = CommandItem(stream_name, self._db, item=self._db.get(stream_name), default=None)
            stream_results = self._xrange(item.value, start_id, max_inf, False, count)
            if len(stream_results) > 0:
                res[item.key] = stream_results

        # On blocking read, and there are no results, return None (instead of an empty list)
        if blocking and len(res) == 0:
            return None
        if self._client_info.protocol_version == 2:
            return [[k, v] for k, v in res.items()]
        return res

    @staticmethod
    def _parse_start_id(key: CommandItem, s: bytes) -> StreamRangeTest:
        if s == b"$":
            if key.value is None:
                return StreamRangeTest.decode(b"0-0")
            return StreamRangeTest.decode(key.value.last_item_key(), exclusive=True)
        return StreamRangeTest.decode(s, exclusive=True)
