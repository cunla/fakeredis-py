import functools
from typing import List, Union, Tuple, Callable

import fakeredis._msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import Key, command, CommandItem, Int
from fakeredis._helpers import SimpleError, casematch, OK, current_time, Database
from fakeredis._stream import XStream, StreamRangeTest, StreamGroup


class StreamsCommandsMixin:
    _db: Database
    version: Tuple[int]
    _blocking: Callable

    @command(
        name="XADD",
        fixed=(Key(),),
        repeat=(bytes,),
    )
    def xadd(self, key, *args):
        (nomkstream, limit, maxlen, minid), left_args = extract_args(
            args,
            ("nomkstream", "+limit", "~+maxlen", "~minid"),
            error_on_unexpected=False,
        )
        if nomkstream and key.value is None:
            return None
        entry_key = left_args[0]
        elements = left_args[1:]
        if not elements or len(elements) % 2 != 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("XADD"))
        stream = key.value if key.value is not None else XStream()
        if (
                self.version < (7,)
                and entry_key != b"*"
                and not StreamRangeTest.valid_key(entry_key)
        ):
            raise SimpleError(msgs.XADD_INVALID_ID)
        entry_key = stream.add(elements, entry_key=entry_key)
        if entry_key is None:
            if not StreamRangeTest.valid_key(left_args[0]):
                raise SimpleError(msgs.XADD_INVALID_ID)
            raise SimpleError(msgs.XADD_ID_LOWER_THAN_LAST)
        if maxlen is not None or minid is not None:
            stream.trim(max_length=maxlen, start_entry_key=minid, limit=limit)
        key.update(stream)
        return entry_key

    @command(
        name="XTRIM",
        fixed=(Key(XStream),),
        repeat=(bytes,),
        flags=msgs.FLAG_LEAVE_EMPTY_VAL,
    )
    def xtrim(self, key, *args):
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
    def xlen(self, key):
        return len(key.value)

    @staticmethod
    def _xrange(
            stream: XStream,
            _min: StreamRangeTest,
            _max: StreamRangeTest,
            reverse: bool,
            count: Union[int, None],
    ) -> List:
        if stream is None:
            return []
        if count is None:
            count = len(stream)
        res = stream.irange(_min, _max, reverse=reverse)
        return res[:count]

    @command(
        name="XRANGE",
        fixed=(Key(XStream), StreamRangeTest, StreamRangeTest),
        repeat=(bytes,),
    )
    def xrange(self, key, _min, _max, *args):
        (count,), _ = extract_args(args, ("+count",))
        return self._xrange(key.value, _min, _max, False, count)

    @command(
        name="XREVRANGE",
        fixed=(Key(XStream), StreamRangeTest, StreamRangeTest),
        repeat=(bytes,),
    )
    def xrevrange(self, key, _min, _max, *args):
        (count,), _ = extract_args(args, ("+count",))
        return self._xrange(key.value, _max, _min, True, count)

    def _xread(self, stream_start_id_list: List, count: int, first_pass: bool):
        max_inf = StreamRangeTest.decode(b"+")
        res = list()
        for item, start_id in stream_start_id_list:
            stream_results = self._xrange(item.value, start_id, max_inf, False, count)
            if first_pass and (count is None or len(stream_results) < count):
                raise SimpleError(msgs.WRONGTYPE_MSG)
            if len(stream_results) > 0:
                res.append([item.key, stream_results])
        return res

    def _xreadgroup(
            self,
            consumer_name: bytes,
            group_params: List[Tuple[StreamGroup, bytes, bytes]],
            count: int,
            noack: bool,
            first_pass: bool,
    ):
        res = list()
        for group, stream_name, start_id in group_params:
            stream_results = group.group_read(consumer_name, start_id, count, noack)
            if first_pass and (count is None or len(stream_results) < count):
                raise SimpleError(msgs.WRONGTYPE_MSG)
            if len(stream_results) > 0 or start_id != b">":
                res.append([stream_name, stream_results])
        return res

    @staticmethod
    def _parse_start_id(key: CommandItem, s: bytes) -> StreamRangeTest:
        if s == b"$":
            return StreamRangeTest.decode(key.value.last_item_key(), exclusive=True)
        return StreamRangeTest.decode(s, exclusive=True)

    @command(name="XREAD", fixed=(bytes,), repeat=(bytes,))
    def xread(self, *args):
        (
            count,
            timeout,
        ), left_args = extract_args(
            args,
            (
                "+count",
                "+block",
            ),
            error_on_unexpected=False,
        )
        if (
                len(left_args) < 3
                or not casematch(left_args[0], b"STREAMS")
                or len(left_args) % 2 != 1
        ):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        left_args = left_args[1:]
        num_streams = int(len(left_args) / 2)

        stream_start_id_list = list()
        for i in range(num_streams):
            item = CommandItem(
                left_args[i], self._db, item=self._db.get(left_args[i]), default=None
            )
            start_id = self._parse_start_id(item, left_args[i + num_streams])
            stream_start_id_list.append(
                (
                    item,
                    start_id,
                )
            )
        if timeout is None:
            return self._xread(stream_start_id_list, count, False)
        else:
            return self._blocking(
                timeout, functools.partial(self._xread, stream_start_id_list, count)
            )

    @command(name="XREADGROUP", fixed=(bytes, bytes, bytes), repeat=(bytes,))
    def xreadgroup(self, group_const, group_name, consumer_name, *args):
        if not casematch(b"GROUP", group_const):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        (count, timeout, noack), left_args = extract_args(
            args, ("+count", "+block", "noack"), error_on_unexpected=False
        )
        if (
                len(left_args) < 3
                or not casematch(left_args[0], b"STREAMS")
                or len(left_args) % 2 != 1
        ):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        left_args = left_args[1:]
        num_streams = int(len(left_args) / 2)

        # List of (group, stream_name, stream start-id)
        group_params: List[Tuple[StreamGroup, bytes, bytes]] = list()
        for i in range(num_streams):
            item = CommandItem(
                left_args[i], self._db, item=self._db.get(left_args[i]), default=None
            )
            if item.value is None:
                raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
            group: StreamGroup = item.value.group_get(group_name)
            if not group:
                raise SimpleError(
                    msgs.XREADGROUP_KEY_OR_GROUP_NOT_FOUND_MSG.format(
                        left_args[i].decode(), group_name.decode()
                    )
                )
            group_params.append(
                (
                    group,
                    left_args[i],
                    left_args[i + num_streams],
                )
            )
        if timeout is None:
            return self._xreadgroup(consumer_name, group_params, count, noack, False)
        else:
            return self._blocking(
                timeout,
                functools.partial(
                    self._xreadgroup, consumer_name, group_params, count, noack
                ),
            )

    @command(
        name="XDEL",
        fixed=(Key(XStream),),
        repeat=(bytes,),
    )
    def xdel(self, key, *args):
        if len(args) == 0:
            raise SimpleError(msgs.WRONG_ARGS_MSG6.format("xdel"))
        res = key.value.delete(args)
        return res

    @command(
        name="XACK",
        fixed=(Key(XStream), bytes),
        repeat=(bytes,),
    )
    def xack(self, key, group_name, *args):
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
    )
    def xpending(self, key, group_name, *args):
        if key.value is None:
            return 0
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
            return 0 if start is not None else []

        if start is not None:
            return group.pending(idle, start, end, count, consumer)
        else:
            return group.pending_summary()

    @command(
        name="XGROUP CREATE",
        fixed=(Key(XStream), bytes, bytes),
        repeat=(bytes,),
        flags=msgs.FLAG_LEAVE_EMPTY_VAL,
    )
    def xgroup_create(self, key, group_name, start_key, *args):
        (
            mkstream,
            entries_read,
        ), _ = extract_args(args, ("mkstream", "+entriesread"))
        if key.value is None and not mkstream:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        if key.value.group_get(group_name) is not None:
            raise SimpleError(msgs.XGROUP_BUSYGROUP)
        key.value.group_add(group_name, start_key, entries_read)
        key.updated()
        return OK

    @command(
        name="XGROUP SETID",
        fixed=(Key(XStream), bytes, bytes),
        repeat=(bytes,),
    )
    def xgroup_setid(self, key, group_name, start_key, *args):
        (entries_read,), _ = extract_args(args, ("+entriesread",))
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group = key.value.group_get(group_name)
        if not group:
            raise SimpleError(
                msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key)
            )
        group.set_id(start_key, entries_read)
        return OK

    @command(
        name="XGROUP DESTROY",
        fixed=(
                Key(XStream),
                bytes,
        ),
        repeat=(),
    )
    def xgroup_destroy(
            self,
            key,
            group_name,
    ):
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        res = key.value.group_delete(group_name)
        return res

    @command(
        name="XGROUP CREATECONSUMER",
        fixed=(Key(XStream), bytes, bytes),
        repeat=(),
    )
    def xgroup_createconsumer(self, key, group_name, consumer_name):
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            raise SimpleError(
                msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key)
            )
        return group.add_consumer(consumer_name)

    @command(
        name="XGROUP DELCONSUMER",
        fixed=(Key(XStream), bytes, bytes),
        repeat=(),
    )
    def xgroup_delconsumer(self, key, group_name, consumer_name):
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            raise SimpleError(
                msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key)
            )
        return group.del_consumer(consumer_name)

    @command(
        name="XINFO GROUPS",
        fixed=(Key(XStream),),
        repeat=(),
    )
    def xinfo_groups(
            self,
            key,
    ):
        if key.value is None:
            raise SimpleError(msgs.NO_KEY_MSG)
        return key.value.groups_info()

    @command(
        name="XINFO STREAM",
        fixed=(Key(XStream),),
        repeat=(bytes,),
    )
    def xinfo_stream(self, key, *args):
        (full,), _ = extract_args(args, ("full",))
        if key.value is None:
            raise SimpleError(msgs.NO_KEY_MSG)
        return key.value.stream_info(full)

    @command(
        name="XINFO CONSUMERS",
        fixed=(Key(XStream), bytes),
        repeat=(),
    )
    def xinfo_consumers(
            self,
            key,
            group_name,
    ):
        if key.value is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = key.value.group_get(group_name)
        if not group:
            raise SimpleError(
                msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key)
            )
        return group.consumers_info()

    @command(
        name="XCLAIM",
        fixed=(Key(XStream), bytes, bytes, Int, bytes),
        repeat=(bytes,),
    )
    def xclaim(self, key, group_name, consumer_name, min_idle_ms, *args):
        stream = key.value
        if stream is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = stream.group_get(group_name)
        if not group:
            raise SimpleError(
                msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key)
            )

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

    @command(
        name="XAUTOCLAIM",
        fixed=(Key(XStream), bytes, bytes, Int, bytes),
        repeat=(bytes,),
    )
    def xautoclaim(self, key, group_name, consumer_name, min_idle_ms, start, *args):
        (count, justid), _ = extract_args(args, ("+count", "justid"))
        count = count or 100
        stream = key.value
        if stream is None:
            raise SimpleError(msgs.XGROUP_KEY_NOT_FOUND_MSG)
        group: StreamGroup = stream.group_get(group_name)
        if not group:
            raise SimpleError(
                msgs.XGROUP_GROUP_NOT_FOUND_MSG.format(group_name.decode(), key)
            )

        keys = group.read_pel_msgs(min_idle_ms, start, count)
        msgs_claimed, msgs_removed = group.claim(
            min_idle_ms, keys, consumer_name, None, False
        )

        res = [
            max(msgs_claimed).encode() if len(msgs_claimed) > 0 else start,
            [msg.encode() for msg in msgs_claimed]
            if justid
            else [stream.format_record(msg) for msg in msgs_claimed],
        ]
        if self.version >= (7,):
            res.append([msg.encode() for msg in msgs_removed])
        return res
