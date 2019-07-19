import pytest

from git_backup import config


@pytest.mark.parametrize('base, update, expected', [
    ({'one': 1, 'two': 2}, {'three': 3}, {'one': 1, 'two': 2, 'three': 3}),
    ({'one': 1, 'two': 2}, {'two': -2}, {'one': 1, 'two': -2}),
    ({'a': {'one': 1, 'two': 2}, 'b': {'four': 4}},
     {'a': {'three': 3}}, {'a': {'one': 1, 'two': 2, 'three': 3}, 'b': {'four': 4}}),
    ({}, {}, {}),
    ({}, {'a': {'one': 1, 'two': 2}}, {'a': {'one': 1, 'two': 2}}),
])
def test_merge_dict(base, update, expected):
    config.merge_dicts(base, update)
    assert base == expected


@pytest.mark.parametrize('container, keys, expected', [
    ({'x': 1, 'y': 2}, ['x'], 1),
    ({'x': {'xx': 1}, 'y': 2}, ['x', 'xx'], 1),
    ({'x': {'xx': 1}, 'y': 2}, ['x', 'xy', 'y'], None),
])
def test_get_deep(container, keys, expected):
    value = config.get_deep(container, *keys)
    assert value == expected


@pytest.mark.parametrize('container, keys, value, expected', [
    ({'x': 1, 'y': 2}, ['x'], -1,
     {'x': -1, 'y': 2}),
    ({'x': {'xx': 1}, 'y': 2}, ['x', 'xx'], -1,
     {'x': {'xx': -1}, 'y': 2}),
    ({'x': {'xx': 1}, 'y': 2}, ['x', 'xy', 'y'], 42,
     {'x': {'xx': 1, 'xy': {'y': 42}}, 'y': 2}),
])
def test_set_deep(container, keys, value, expected):
    config.set_deep(container, *keys, value=value)
    assert container == expected
