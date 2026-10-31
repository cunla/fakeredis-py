# Geohashes as Redis computes them for the GEO commands (geohash.c in Redis).
#
# A member's score in the sorted set is a 52-bit geohash: 26 bits of longitude and 26 bits of latitude, interleaved.
# Redis maps the latitude from the Web Mercator range [-85.05112878, 85.05112878] rather than [-90, 90], so to answer
# GEOHASH it decodes the score and encodes the position again with the standard ranges.
#
# Note: the alphabet in geohash differs from the common base32 alphabet described in IETF's RFC 4648
# (http://tools.ietf.org/html/rfc4648)

from __future__ import annotations

base32 = "0123456789bcdefghjkmnpqrstuvwxyz"

GEO_STEP = 26  # bits for each coordinate
GEO_LAT_MIN, GEO_LAT_MAX = -85.05112878, 85.05112878
GEO_LONG_MIN, GEO_LONG_MAX = -180.0, 180.0


def _interleave(x: int, y: int) -> int:
    """Interleave the bits of x and y, x taking the even bits and y the odd ones."""
    bits = 0
    for i in range(32):
        bits |= ((x >> i) & 1) << (2 * i) | ((y >> i) & 1) << (2 * i + 1)
    return bits


def _deinterleave(bits: int) -> tuple[int, int]:
    """Split interleaved bits back into x (the even bits) and y (the odd bits)."""
    x = y = 0
    for i in range(32):
        x |= ((bits >> (2 * i)) & 1) << i
        y |= ((bits >> (2 * i + 1)) & 1) << i
    return x, y


def _encode(latitude: float, longitude: float, lat_min: float, lat_max: float) -> int:
    lat_offset = (latitude - lat_min) / (lat_max - lat_min)
    long_offset = (longitude - GEO_LONG_MIN) / (GEO_LONG_MAX - GEO_LONG_MIN)
    return _interleave(int(lat_offset * (1 << GEO_STEP)), int(long_offset * (1 << GEO_STEP)))


def geo_encode(latitude: float, longitude: float) -> int:
    """Encode a position to the 52-bit geohash that Redis keeps as the member's score."""
    return _encode(latitude, longitude, GEO_LAT_MIN, GEO_LAT_MAX)


def geo_decode(score: float) -> tuple[float, float, float, float]:
    """
    Decode a member's score to the centre of its geohash cell.  Returns four float values: latitude, longitude, the
    plus/minus error for latitude (as a positive number) and the plus/minus error for longitude (as a positive number).
    """
    lat_bits, long_bits = _deinterleave(int(score))
    lat_scale, long_scale = GEO_LAT_MAX - GEO_LAT_MIN, GEO_LONG_MAX - GEO_LONG_MIN
    lat_min = GEO_LAT_MIN + (lat_bits / (1 << GEO_STEP)) * lat_scale
    lat_max = GEO_LAT_MIN + ((lat_bits + 1) / (1 << GEO_STEP)) * lat_scale
    long_min = GEO_LONG_MIN + (long_bits / (1 << GEO_STEP)) * long_scale
    long_max = GEO_LONG_MIN + ((long_bits + 1) / (1 << GEO_STEP)) * long_scale
    lat = min(max((lat_min + lat_max) / 2, GEO_LAT_MIN), GEO_LAT_MAX)
    long = min(max((long_min + long_max) / 2, GEO_LONG_MIN), GEO_LONG_MAX)
    return lat, long, (lat_max - lat_min) / 2, (long_max - long_min) / 2


def geohash_string(score: float) -> str:
    """The standard geohash of a member's position, as GEOHASH gives it: the 52 bits make 10 characters, and Redis
    pads them to 11 with a "0"."""
    lat, long, _, _ = geo_decode(score)
    bits = _encode(lat, long, -90.0, 90.0)
    return "".join(base32[(bits >> (52 - (i + 1) * 5)) & 0x1F] for i in range(10)) + "0"
