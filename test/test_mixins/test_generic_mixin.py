def test_randomkey_returns_none_on_empty_db(r):
    assert r.randomkey() is None


def test_randomkey_returns_existing_key(r):
    r.set("foo", 1)
    r.set("bar", 2)
    r.set("baz", 3)
    assert r.randomkey().decode() in ("foo", "bar", "baz")
