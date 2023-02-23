from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import command, Key, Float
from fakeredis._helpers import SimpleError
from fakeredis._zset import ZSet
from fakeredis.geo import geohash
from fakeredis.geo.haversine import distance


class GeoCommandsMixin:
    @command(name='GEOADD', fixed=(Key(ZSet),), repeat=(bytes,))
    def geoadd(self, key, *args):
        (xx, nx, ch), data = extract_args(
            args, ('nx', 'xx', 'ch'),
            error_on_unexpected=False, left_from_first_unexpected=True)
        if xx and nx:
            raise SimpleError(msgs.NX_XX_GT_LT_ERROR_MSG)
        if len(data) == 0 or len(data) % 3 != 0:
            raise SimpleError(msgs.SYNTAX_ERROR_MSG)
        zset = key.value
        old_len, changed_items = len(zset), 0
        for i in range(0, len(data), 3):
            long, lat, name = Float.decode(data[i + 0]), Float.decode(data[i + 1]), data[i + 2]
            if (name in zset and not xx) or (name not in zset and not nx):
                if zset.add(name, geohash.encode(lat, long, 10)):
                    changed_items += 1
        if changed_items:
            key.updated()
        if ch:
            return changed_items
        return len(zset) - old_len

    @command(name='GEOHASH', fixed=(Key(ZSet), bytes), repeat=(bytes,))
    def geohash(self, key, *members):
        hashes = map(key.value.get, members)
        geohash_list = [((x + '0').encode() if x is not None else x) for x in hashes]
        return geohash_list

    @command(name='GEOPOS', fixed=(Key(ZSet), bytes), repeat=(bytes,))
    def geopos(self, key, *members):
        gospositions = map(
            lambda x: geohash.decode(x) if x is not None else x,
            map(key.value.get, members))
        res = [([self._encodefloat(x[1], humanfriendly=False),
                 self._encodefloat(x[0], humanfriendly=False)]
                if x is not None else None)
               for x in gospositions]
        return res

    @command(name='GEODIST', fixed=(Key(ZSet), bytes, bytes), repeat=(bytes,))
    def geodist(self, key, m1, m2, *args):
        geohashes = [key.value.get(m1), key.value.get(m2)]
        if any(elem is None for elem in geohashes):
            return None
        geo_locs = [geohash.decode(x) for x in geohashes]
        res = distance((geo_locs[0][0], geo_locs[0][1]),
                       (geo_locs[1][0], geo_locs[1][1]))
        unit = 1
        if len(args) == 1:
            unit_str = args[0].decode().lower()
            if unit_str == 'km':
                unit = 0.001
            elif unit_str == 'mi':
                unit = 0.000621371
            elif unit_str == 'ft':
                unit = 3.28084
        return res * unit
