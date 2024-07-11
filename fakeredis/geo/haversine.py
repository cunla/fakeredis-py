import math
from typing import Tuple


# class GeoMember:
#     def __init__(self, name: bytes, lat: float, long: float):
#         self.name = name
#         self.long = long
#         self.lat = lat
#
#     @staticmethod
#     def from_bytes_tuple(t: Tuple[bytes, bytes, bytes]) -> 'GeoMember':
#         long = Float.decode(t[0])
#         lat = Float.decode(t[1])
#         name = t[2]
#         return GeoMember(name, lat, long)
#
#     def geohash(self):
#         return geohash.encode(self.lat, self.long)


def distance(origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
    """Calculate the Haversine distance in meters."""
    radius = 6372797.560856  # Earth's quatratic mean radius for WGS-84

    lat1, lon1, lat2, lon2 = map(math.radians, [origin[0], origin[1], destination[0], destination[1]])

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    return c * radius
