import time

from fakeredis import _msgs as msgs
from fakeredis._commands import (command, DbIndex)
from fakeredis._helpers import (OK, SimpleError, casematch, BGSAVE_STARTED)


class ServerCommandsMixin:
    # TODO: lots

    @command((), (bytes,), flags='s')
    def bgsave(self, *args):
        if len(args) > 1 or (len(args) == 1 and not casematch(args[0], b'schedule')):
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        self._server.lastsave = int(time.time())
        return BGSAVE_STARTED

    @command(())
    def dbsize(self):
        return len(self._db)

    @command((), (bytes,))
    def flushdb(self, *args):
        if args:
            if len(args) != 1 or not casematch(args[0], b'async'):
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        self._db.clear()
        return OK

    @command((), (bytes,))
    def flushall(self, *args):
        if args:
            if len(args) != 1 or not casematch(args[0], b'async'):
                raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        for db in self._server.dbs.values():
            db.clear()
        # TODO: clear watches and/or pubsub as well?
        return OK

    @command(())
    def lastsave(self):
        return self._server.lastsave

    @command((), flags='s')
    def save(self):
        self._server.lastsave = int(time.time())
        return OK

    @command(())
    def time(self):
        now_us = round(time.time() * 1000000)
        now_s = now_us // 1000000
        now_us %= 1000000
        return [str(now_s).encode(), str(now_us).encode()]

    @command((DbIndex, DbIndex))
    def swapdb(self, index1, index2):
        if index1 != index2:
            db1 = self._server.dbs[index1]
            db2 = self._server.dbs[index2]
            db1.swap(db2)
        return OK
