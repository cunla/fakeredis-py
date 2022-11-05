from fakeredis import _msgs as msgs
from fakeredis._commands import command, DbIndex
from fakeredis._helpers import SimpleError, OK, PONG


class ConnectionCommandsMixin:
    # Connection commands
    # TODO: auth, quit

    @command((bytes,))
    def echo(self, message):
        return message

    @command((), (bytes,))
    def ping(self, *args):
        msg = msgs.WRONG_ARGS_MSG7 if self.version >= 7 else msgs.WRONG_ARGS_MSG6.format('ping')
        if len(args) > 1:
            raise SimpleError(msg)
        if self._pubsub:
            return [b'pong', args[0] if args else b'']
        else:
            return args[0] if args else PONG

    @command((DbIndex,))
    def select(self, index):
        self._db = self._server.dbs[index]
        self._db_num = index
        return OK
