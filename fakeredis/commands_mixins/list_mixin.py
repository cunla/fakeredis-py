import functools

from fakeredis import _msgs as msgs
from fakeredis._commands import (
    Key, command, Int, CommandItem, Timeout, fix_range)
from fakeredis._helpers import (
    OK, SimpleError, SimpleString, casematch)


def _list_pop(get_slice, key, *args):
    """Implements lpop and rpop.

    `get_slice` must take a count and return a slice expression for the
    range to pop.
    """
    # This implementation is somewhat contorted to match the odd
    # behaviours described in https://github.com/redis/redis/issues/9680.
    count = 1
    if len(args) > 1:
        raise SimpleError(msgs.SYNTAX_ERROR_MSG)
    elif len(args) == 1:
        count = args[0]
        if count < 0:
            raise SimpleError(msgs.INDEX_ERROR_MSG)
    if not key:
        return None
    elif type(key.value) != list:
        raise SimpleError(msgs.WRONGTYPE_MSG)
    slc = get_slice(count)
    ret = key.value[slc]
    del key.value[slc]
    key.updated()
    if not args:
        ret = ret[0]
    return ret


class ListCommandsMixin:
    # List commands

    def _bpop_pass(self, keys, op, first_pass):
        for key in keys:
            item = CommandItem(key, self._db, item=self._db.get(key), default=[])
            if not isinstance(item.value, list):
                if first_pass:
                    raise SimpleError(msgs.WRONGTYPE_MSG)
                else:
                    continue
            if item.value:
                ret = op(item.value)
                item.updated()
                item.writeback()
                return [key, ret]
        return None

    def _bpop(self, args, op):
        keys = args[:-1]
        timeout = Timeout.decode(args[-1])
        return self._blocking(timeout, functools.partial(self._bpop_pass, keys, op))

    @command((bytes, bytes), (bytes,), flags='s')
    def blpop(self, *args):
        return self._bpop(args, lambda lst: lst.pop(0))

    @command((bytes, bytes), (bytes,), flags='s')
    def brpop(self, *args):
        return self._bpop(args, lambda lst: lst.pop())

    def _brpoplpush_pass(self, source, destination, first_pass):
        src = CommandItem(source, self._db, item=self._db.get(source), default=[])
        if not isinstance(src.value, list):
            if first_pass:
                raise SimpleError(msgs.WRONGTYPE_MSG)
            else:
                return None
        if not src.value:
            return None  # Empty list
        dst = CommandItem(destination, self._db, item=self._db.get(destination), default=[])
        if not isinstance(dst.value, list):
            raise SimpleError(msgs.WRONGTYPE_MSG)
        el = src.value.pop()
        dst.value.insert(0, el)
        src.updated()
        src.writeback()
        if destination != source:
            # Ensure writeback only happens once
            dst.updated()
            dst.writeback()
        return el

    @command((bytes, bytes, Timeout), flags='s')
    def brpoplpush(self, source, destination, timeout):
        return self._blocking(timeout,
                              functools.partial(self._brpoplpush_pass, source, destination))

    @command((Key(list, None), Int))
    def lindex(self, key, index):
        try:
            return key.value[index]
        except IndexError:
            return None

    @command((Key(list), bytes, bytes, bytes))
    def linsert(self, key, where, pivot, value):
        if not casematch(where, b'before') and not casematch(where, b'after'):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if not key:
            return 0
        else:
            try:
                index = key.value.index(pivot)
            except ValueError:
                return -1
            if casematch(where, b'after'):
                index += 1
            key.value.insert(index, value)
            key.updated()
            return len(key.value)

    @command((Key(list),))
    def llen(self, key):
        return len(key.value)

    @command((Key(list, None), Key(list), SimpleString, SimpleString))
    def lmove(self, first_list, second_list, src, dst):
        if src not in [b'LEFT', b'RIGHT']:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        if dst not in [b'LEFT', b'RIGHT']:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        el = self.rpop(first_list) if src == b'RIGHT' else self.lpop(first_list)
        self.lpush(second_list, el) if dst == b'LEFT' else self.rpush(second_list, el)
        return el

    @command((Key(),), (Int(),))
    def lpop(self, key, *args):
        return _list_pop(lambda count: slice(None, count), key, *args)

    @command((Key(list), bytes), (bytes,))
    def lpush(self, key, *values):
        for value in values:
            key.value.insert(0, value)
        key.updated()
        return len(key.value)

    @command((Key(list), bytes), (bytes,))
    def lpushx(self, key, *values):
        if not key:
            return 0
        return self.lpush(key, *values)

    @command((Key(list), Int, Int))
    def lrange(self, key, start, stop):
        start, stop = fix_range(start, stop, len(key.value))
        return key.value[start:stop]

    @command((Key(list), Int, bytes))
    def lrem(self, key, count, value):
        a_list = key.value
        found = []
        for i, el in enumerate(a_list):
            if el == value:
                found.append(i)
        if count > 0:
            indices_to_remove = found[:count]
        elif count < 0:
            indices_to_remove = found[count:]
        else:
            indices_to_remove = found
        # Iterating in reverse order to ensure the indices
        # remain valid during deletion.
        for index in reversed(indices_to_remove):
            del a_list[index]
        if indices_to_remove:
            key.updated()
        return len(indices_to_remove)

    @command((Key(list), Int, bytes))
    def lset(self, key, index, value):
        if not key:
            raise SimpleError(msgs.NO_KEY_MSG)
        try:
            key.value[index] = value
            key.updated()
        except IndexError:
            raise SimpleError(msgs.INDEX_ERROR_MSG)
        return OK

    @command((Key(list), Int, Int))
    def ltrim(self, key, start, stop):
        if key:
            if stop == -1:
                stop = None
            else:
                stop += 1
            new_value = key.value[start:stop]
            # TODO: check if this should actually be conditional
            if len(new_value) != len(key.value):
                key.update(new_value)
        return OK

    @command((Key(),), (Int(),))
    def rpop(self, key, *args):
        return _list_pop(lambda count: slice(None, -count - 1, -1), key, *args)

    @command((Key(list, None), Key(list)))
    def rpoplpush(self, src, dst):
        el = self.rpop(src)
        self.lpush(dst, el)
        return el

    @command((Key(list), bytes), (bytes,))
    def rpush(self, key, *values):
        for value in values:
            key.value.append(value)
        key.updated()
        return len(key.value)

    @command((Key(list), bytes), (bytes,))
    def rpushx(self, key, *values):
        if not key:
            return 0
        return self.rpush(key, *values)
