import sys
from collections import namedtuple
from typing import List, Optional, Any

from fakeredis import _msgs as msgs
from fakeredis._command_args_parsing import extract_args
from fakeredis._commands import command, Key, Float
from fakeredis._helpers import SimpleError
from fakeredis._zset import ZSet
from fakeredis.geo import geohash
from fakeredis.geo.haversine import distance


def translate_meters_to_unit(unit_arg: bytes) -> float:
    unit_str = unit_arg.decode().lower()
    if unit_str == 'km':
        unit = 0.001
    elif unit_str == 'mi':
        unit = 0.000621371
    elif unit_str == 'ft':
        unit = 3.28084
    else:  # meter
        unit = 1
    return unit


GeoResult = namedtuple('GeoResult', 'name long lat hash distance')


class GeoCommandsMixin:
    # TODO
    # GEORADIUS, GEORADIUS_RO,
    # GEORADIUSBYMEMBER, GEORADIUSBYMEMBER_RO,
    # GEOSEARCH, GEOSEARCHSTORE

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
        unit = translate_meters_to_unit(args[0]) if len(args) == 1 else 1
        return res * unit

    def _parse_results(
            self, items: List[GeoResult],
            withcoord: bool, withdist: bool, withhash: bool,
            count: Optional[int], desc: bool) -> List[Any]:
        items = sorted(items, key=lambda x: x.distance, reverse=desc)
        if count:
            items = items[:count]
        res = list()
        for item in items:
            new_item = [item.name, ]
            if withdist:
                new_item.append(self._encodefloat(item.distance, False))
            if withcoord:
                new_item.append([self._encodefloat(item.long, False),
                                 self._encodefloat(item.lat, False)])
            if len(new_item) == 1:
                new_item = new_item[0]
            res.append(new_item)
        return res

    @command(name='GEORADIUS', fixed=(Key(ZSet), Float, Float, Float), repeat=(bytes,))
    def georadius(self, key, long, lat, radius, *args):
        zset = key.value
        results = list()
        (withcoord, withdist, withhash, count, count_any, desc, store, storedist), left_args = extract_args(
            args, ('withcoord', 'withdist', 'withhash', '+count', 'any', 'desc', '*store', '*storedist'),
            error_on_unexpected=False, left_from_first_unexpected=False)
        unit = translate_meters_to_unit(args[0]) if len(args) >= 1 else 1
        count = count or sys.maxsize

        for name, _hash in zset.items():
            p_lat, p_long, _, _ = geohash.decode(_hash)
            dist = distance((p_lat, p_long), (lat, long)) * unit
            if dist < radius:
                results.append(GeoResult(name, p_long, p_lat, _hash, dist))
                if count_any and len(results) >= count:
                    break

        return self._parse_results(results, withcoord, withdist, withhash, count, desc)
