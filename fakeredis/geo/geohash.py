# Note: the alphabet in geohash differs from the common base32 alphabet described in IETF's RFC 4648
# (http://tools.ietf.org/html/rfc4648)

from __future__ import annotations

base32 = "0123456789bcdefghjkmnpqrstuvwxyz"
decodemap = {base32[i]: i for i in range(len(base32))}


def geo_decode(geohash: str) -> tuple[float, float, float, float]:
    """
    Decode the geohash to its exact values, including the error margins of the result.  Returns four float values:
    latitude, longitude, the plus/minus error for latitude (as a positive number) and the plus/minus error for longitude
    (as a positive number).
    """
    lat_interval, lon_interval = (-90.0, 90.0), (-180.0, 180.0)
    lat_err, lon_err = 90.0, 180.0
    is_longitude = True
    for c in geohash:
        cd = decodemap[c]
        for mask in [16, 8, 4, 2, 1]:
            if is_longitude:  # adds longitude info
                lon_err /= 2
                if cd & mask:
                    lon_interval = (
                        (lon_interval[0] + lon_interval[1]) / 2,
                        lon_interval[1],
                    )
                else:
                    lon_interval = (
                        lon_interval[0],
                        (lon_interval[0] + lon_interval[1]) / 2,
                    )
            else:  # adds latitude info
                lat_err /= 2
                if cd & mask:
                    lat_interval = (
                        (lat_interval[0] + lat_interval[1]) / 2,
                        lat_interval[1],
                    )
                else:
                    lat_interval = (
                        lat_interval[0],
                        (lat_interval[0] + lat_interval[1]) / 2,
                    )
            is_longitude = not is_longitude
    lat = (lat_interval[0] + lat_interval[1]) / 2
    lon = (lon_interval[0] + lon_interval[1]) / 2
    return lat, lon, lat_err, lon_err


def geo_encode(latitude: float, longitude: float, precision: int = 12) -> str:
    """
    Encode a position given in float arguments latitude, longitude to a geohash which will have the character count
    precision.
    """
    lat_interval, lon_interval = (-90.0, 90.0), (-180.0, 180.0)
    geohash, bits = [], [16, 8, 4, 2, 1]  # type: ignore
    bit, ch = 0, 0
    is_longitude = True

    def next_interval(curr: float, interval: tuple[float, float], ch: int) -> tuple[tuple[float, float], int]:
        mid = (interval[0] + interval[1]) / 2
        if curr > mid:
            ch |= bits[bit]
            return (mid, interval[1]), ch
        else:
            return (interval[0], mid), ch

    while len(geohash) < precision:
        if is_longitude:
            lon_interval, ch = next_interval(longitude, lon_interval, ch)
        else:
            lat_interval, ch = next_interval(latitude, lat_interval, ch)
        is_longitude = not is_longitude
        if bit < 4:
            bit += 1
        else:
            geohash += base32[ch]
            bit = 0
            ch = 0
    return "".join(geohash)


# Redis stores a GEO member's score as the 52-bit interleaved geohash over the *Web Mercator* latitude range, not over
# the -90..90 range the base32 string above uses. The two encodings are different: the string is for humans and GEOHASH
# output, the integer is what every sorted-set command sees as the score.
_GEO_SCORE_LAT_MIN, _GEO_SCORE_LAT_MAX = -85.05112878, 85.05112878
_GEO_SCORE_LON_MIN, _GEO_SCORE_LON_MAX = -180.0, 180.0
_GEO_SCORE_STEP = 26


def _spread_bits(value: int) -> int:
    """Spread the low 32 bits of value so each one lands in an even bit position."""
    value &= 0xFFFFFFFF
    value = (value | (value << 16)) & 0x0000FFFF0000FFFF
    value = (value | (value << 8)) & 0x00FF00FF00FF00FF
    value = (value | (value << 4)) & 0x0F0F0F0F0F0F0F0F
    value = (value | (value << 2)) & 0x3333333333333333
    value = (value | (value << 1)) & 0x5555555555555555
    return value


def _compact_bits(value: int) -> int:
    """Undo _spread_bits: keep the even bits and pack them back down."""
    value &= 0x5555555555555555
    value = (value | (value >> 1)) & 0x3333333333333333
    value = (value | (value >> 2)) & 0x0F0F0F0F0F0F0F0F
    value = (value | (value >> 4)) & 0x00FF00FF00FF00FF
    value = (value | (value >> 8)) & 0x0000FFFF0000FFFF
    value = (value | (value >> 16)) & 0x00000000FFFFFFFF
    return value


def geo_encode_score(latitude: float, longitude: float) -> int:
    """The 52-bit integer Redis uses as a GEO member's score (what ZSCORE returns)."""
    lat_offset = int(
        (latitude - _GEO_SCORE_LAT_MIN) / (_GEO_SCORE_LAT_MAX - _GEO_SCORE_LAT_MIN) * (1 << _GEO_SCORE_STEP)
    )
    lon_offset = int(
        (longitude - _GEO_SCORE_LON_MIN) / (_GEO_SCORE_LON_MAX - _GEO_SCORE_LON_MIN) * (1 << _GEO_SCORE_STEP)
    )
    return _spread_bits(lat_offset) | (_spread_bits(lon_offset) << 1)


def geo_decode_score(bits: int) -> tuple[float, float]:
    """The centre of the cell a GEO score names, as (latitude, longitude)."""
    lat_offset = _compact_bits(bits)
    lon_offset = _compact_bits(bits >> 1)
    lat_step = (_GEO_SCORE_LAT_MAX - _GEO_SCORE_LAT_MIN) / (1 << _GEO_SCORE_STEP)
    lon_step = (_GEO_SCORE_LON_MAX - _GEO_SCORE_LON_MIN) / (1 << _GEO_SCORE_STEP)
    return (
        _GEO_SCORE_LAT_MIN + (lat_offset + 0.5) * lat_step,
        _GEO_SCORE_LON_MIN + (lon_offset + 0.5) * lon_step,
    )
