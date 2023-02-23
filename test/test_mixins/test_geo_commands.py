import pytest
import redis


def test_geoadd(r: redis.Redis):
    values = ((2.1909389952632, 41.433791470673, "place1") +
              (2.1873744593677, 41.406342043777, "place2",))
    assert r.geoadd("barcelona", values) == 2
    assert r.zcard("barcelona") == 2

    values = (2.1909389952632, 41.433791470673, "place1")
    assert r.geoadd("a", values) == 1
    values = ((2.1909389952632, 31.433791470673, "place1") +
              (2.1873744593677, 41.406342043777, "place2",))
    assert r.geoadd("a", values, ch=True) == 2
    assert r.zrange("a", 0, -1) == [b"place1", b"place2"]

    with pytest.raises(redis.RedisError):
        r.geoadd("barcelona", (1, 2))


def test_geoadd_xx(r: redis.Redis):
    values = ((2.1909389952632, 41.433791470673, "place1") +
              (2.1873744593677, 41.406342043777, "place2",))
    assert r.geoadd("a", values) == 2
    values = (
            (2.1909389952632, 41.433791470673, "place1")
            + (2.1873744593677, 41.406342043777, "place2")
            + (2.1804738294738, 41.405647879212, "place3")
    )
    assert r.geoadd("a", values, nx=True) == 1
    assert r.zrange("a", 0, -1) == [b"place3", b"place2", b"place1"]


def test_geoadd_ch(r: redis.Redis):
    values = (2.1909389952632, 41.433791470673, "place1")
    assert r.geoadd("a", values) == 1
    values = (2.1909389952632, 31.433791470673, "place1") + (
        2.1873744593677,
        41.406342043777,
        "place2",
    )
    assert r.geoadd("a", values, ch=True) == 2
    assert r.zrange("a", 0, -1) == [b"place1", b"place2"]


def test_geohash(r: redis.Redis):
    values = ((2.1909389952632, 41.433791470673, "place1") +
              (2.1873744593677, 41.406342043777, "place2",))
    r.geoadd("barcelona", values)
    assert r.geohash("barcelona", "place1", "place2", "place3") == [
        "sp3e9yg3kd0",
        "sp3e9cbc3t0",
        None,
    ]


def test_geopos(r: redis.Redis):
    values = ((2.1909389952632, 41.433791470673, "place1") +
              (2.1873744593677, 41.406342043777, "place2",))
    r.geoadd("barcelona", values)
    # small errors may be introduced.
    assert r.geopos("barcelona", "place1", "place4", "place2") == [
        pytest.approx((2.1909389952632, 41.433791470673), 0.00001),
        None,
        pytest.approx((2.1873744593677, 41.406342043777), 0.00001),
    ]


def test_geodist(r: redis.Redis):
    values = ((2.1909389952632, 41.433791470673, "place1") +
              (2.1873744593677, 41.406342043777, "place2",))
    assert r.geoadd("barcelona", values) == 2
    assert r.geodist("barcelona", "place1", "place2") == pytest.approx(3067.4157, 0.0001)


def test_geodist_units(r: redis.Redis):
    values = ((2.1909389952632, 41.433791470673, "place1") +
              (2.1873744593677, 41.406342043777, "place2",))
    r.geoadd("barcelona", values)
    assert r.geodist("barcelona", "place1", "place2", "km") == pytest.approx(3.0674, 0.0001)
    assert r.geodist("barcelona", "place1", "place2", "mi") == pytest.approx(1.906, 0.0001)
    assert r.geodist("barcelona", "place1", "place2", "ft") == pytest.approx(10063.6998, 0.0001)
    with pytest.raises(redis.RedisError):
        assert r.geodist("x", "y", "z", "inches")


def test_geodist_missing_one_member(r: redis.Redis):
    values = (2.1909389952632, 41.433791470673, "place1")
    r.geoadd("barcelona", values)
    assert r.geodist("barcelona", "place1", "missing_member", "km") is None
