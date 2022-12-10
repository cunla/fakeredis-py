from fakeredis import _msgs as msgs
from fakeredis._commands import (command)
from fakeredis._helpers import (NoResponse, compile_pattern, SimpleError)


class PubSubCommandsMixin:
    # Pubsub commands
    def __init__(self, *args, **kwargs):
        super(PubSubCommandsMixin, self).__init__(*args, **kwargs)
        self._pubsub = 0  # Count of subscriptions

    def _subscribe(self, channels, subscribers, mtype):
        for channel in channels:
            subs = subscribers[channel]
            if self not in subs:
                subs.add(self)
                self._pubsub += 1
            msg = [mtype, channel, self._pubsub]
            self.put_response(msg)
        return NoResponse()

    def _unsubscribe(self, channels, subscribers, mtype):
        if not channels:
            channels = []
            for (channel, subs) in subscribers.items():
                if self in subs:
                    channels.append(channel)
        for channel in channels:
            subs = subscribers.get(channel, set())
            if self in subs:
                subs.remove(self)
                if not subs:
                    del subscribers[channel]
                self._pubsub -= 1
            msg = [mtype, channel, self._pubsub]
            self.put_response(msg)
        return NoResponse()

    @command((bytes,), (bytes,), flags=msgs.FLAG_NO_SCRIPT)
    def psubscribe(self, *patterns):
        return self._subscribe(patterns, self._server.psubscribers, b'psubscribe')

    @command((bytes,), (bytes,), flags=msgs.FLAG_NO_SCRIPT)
    def subscribe(self, *channels):
        return self._subscribe(channels, self._server.subscribers, b'subscribe')

    @command((), (bytes,), flags=msgs.FLAG_NO_SCRIPT)
    def punsubscribe(self, *patterns):
        return self._unsubscribe(patterns, self._server.psubscribers, b'punsubscribe')

    @command((), (bytes,), flags=msgs.FLAG_NO_SCRIPT)
    def unsubscribe(self, *channels):
        return self._unsubscribe(channels, self._server.subscribers, b'unsubscribe')

    @command((bytes, bytes))
    def publish(self, channel, message):
        receivers = 0
        msg = [b'message', channel, message]
        subs = self._server.subscribers.get(channel, set())
        for sock in subs:
            sock.put_response(msg)
            receivers += 1
        for (pattern, socks) in self._server.psubscribers.items():
            regex = compile_pattern(pattern)
            if regex.match(channel):
                msg = [b'pmessage', pattern, channel, message]
                for sock in socks:
                    sock.put_response(msg)
                    receivers += 1
        return receivers

    @command(name='PUBSUB CHANNELS', fixed=(), repeat=(bytes,))
    def pubsub_channels(self, *args):
        channels = list(self._server.subscribers.keys())
        if len(args) > 0:
            regex = compile_pattern(args[0])
            channels = [ch for ch in channels if regex.match(ch)]
        return channels

    @command(name='PUBSUB NUMSUB', fixed=(), repeat=(bytes,))
    def pubsub_numsub(self, *args):
        channels = args
        tuples_list = [
            (ch, len(self._server.subscribers.get(ch, [])))
            for ch in channels
        ]
        return [item for sublist in tuples_list for item in sublist]

    @command(name='PUBSUB', fixed=())
    def pubsub(self, *args):
        raise SimpleError(msgs.WRONG_ARGS_MSG6.format('pubsub'))

    @command(name='PUBSUB HELP', fixed=())
    def pubsub_help(self, *args):
        if self.version >= 7:
            help_strings = [
                'PUBSUB <subcommand> [<arg> [value] [opt] ...]. Subcommands are:',
                'CHANNELS [<pattern>]',
                "    Return the currently active channels matching a <pattern> (default: '*')"
                '.',
                'NUMPAT',
                '    Return number of subscriptions to patterns.',
                'NUMSUB [<channel> ...]',
                '    Return the number of subscribers for the specified channels, excluding',
                '    pattern subscriptions(default: no channels).',
                'SHARDCHANNELS [<pattern>]',
                '    Return the currently active shard level channels matching a <pattern> (d'
                "efault: '*').",
                'SHARDNUMSUB [<shardchannel> ...]',
                '    Return the number of subscribers for the specified shard level channel(s'
                ')',
                'HELP',
                '    Prints this help.'
            ]
        else:
            help_strings = [
                'PUBSUB <subcommand> [<arg> [value] [opt] ...]. Subcommands are:',
                'CHANNELS [<pattern>]',
                "    Return the currently active channels matching a <pattern> (default: '*')"
                '.',
                'NUMPAT',
                '    Return number of subscriptions to patterns.',
                'NUMSUB [<channel> ...]',
                '    Return the number of subscribers for the specified channels, excluding',
                '    pattern subscriptions(default: no channels).',
                'HELP',
                '    Prints this help.'
            ]
        return [s.encode() for s in help_strings]
