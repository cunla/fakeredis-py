import pytest
import redis


def test_bf_add(r: redis.Redis):
    assert r.bf().add('key', 'value') == 1
    assert r.bf().add('key', 'value') == 0

    r.set('key1', 'value')
    with pytest.raises(redis.exceptions.ResponseError):
        r.bf().add('key1', 'v')


def test_bf_madd(r: redis.Redis):
    assert r.bf().madd('key', 'v1', 'v2', 'v2') == [1, 1, 0]
    assert r.bf().madd('key', 'v1', 'v2', 'v4') == [0, 0, 1]

    r.set('key1', 'value')
    with pytest.raises(redis.exceptions.ResponseError):
        r.bf().add('key1', 'v')


def test_bf_card(r: redis.Redis):
    assert r.bf().madd('key', 'v1', 'v2', 'v3') == [1, 1, 1]
    assert r.bf().card('key') == 3
    assert r.bf().card('key-new') == 0

    r.set('key1', 'value')
    with pytest.raises(redis.exceptions.ResponseError):
        r.bf().card('key1')


def test_bf_exists(r: redis.Redis):
    assert r.bf().madd('key', 'v1', 'v2', 'v3') == [1, 1, 1]
    assert r.bf().exists('key', 'v1') == 1
    assert r.bf().exists('key', 'v5') == 0
    assert r.bf().exists('key-new', 'v5') == 0

    r.set('key1', 'value')
    with pytest.raises(redis.exceptions.ResponseError):
        r.bf().add('key1', 'v')


def test_bf_mexists(r: redis.Redis):
    assert r.bf().madd('key', 'v1', 'v2', 'v3') == [1, 1, 1]
    assert r.bf().mexists('key', 'v1') == [1, ]
    assert r.bf().mexists('key', 'v1', 'v5') == [1, 0]
    assert r.bf().mexists('key-new', 'v5') == [0, ]

    r.set('key1', 'value')
    with pytest.raises(redis.exceptions.ResponseError):
        r.bf().add('key1', 'v')
