from typing import List, Tuple

import pytest

from reparsec import json_scannerless
from reparsec.parser import run
from reparsec.result import ParseError

DATA_POSITIVE: List[Tuple[str, object]] = [
    (r"1", 1),
    (r"12", 12),
    (r"-1", -1),
    (r"1.0", 1.0),
    (r"10.0", 10.0),
    (r"1.0e2", 100.0),
    (r"-1.0", -1.0),
    (r"true", True),
    (r"false", False),
    (r"null", None),
    (r'"string\nvalue"', "string\nvalue"),
    (r'{}', {}),
    (r'{"bool": true, "number": 1}', {"bool": True, "number": 1}),
    (r'{"nested": {"bool": false}}', {"nested": {"bool": False}}),
    (r'[1, 2, 3]', [1, 2, 3]),
    (r'[1, [2, 3]]', [1, [2, 3]]),
]


@pytest.mark.parametrize("data, expected", DATA_POSITIVE)
def test_positive(data: str, expected: object) -> None:
    assert expected == json_scannerless.parse(data)


DATA_NEGATIVE = [
    ("", "at 0: expected value"),
    ("1 1", "at 2: expected end of file"),
    ("{", "at 1: expected string or '}'"),
    ('{"key"', "at 6: expected ':'"),
    ('{"key":', "at 7: expected value"),
    ('{"key": 0', "at 9: expected ',' or '}'"),
    ('{"key": 0,', "at 10: expected string"),
    ("[", "at 1: expected value or ']'"),
    ("[0", "at 2: expected ',' or ']'"),
    ("[0,", "at 3: expected value"),
]


@pytest.mark.parametrize("data, expected", DATA_NEGATIVE)
def test_negative(data: str, expected: str) -> None:
    with pytest.raises(ParseError) as err:
        json_scannerless.parse(data)
    assert expected == str(err.value)


DATA_RECOVERY: List[Tuple[str, object, str]] = [
    ("1 1", 1, "at 2: expected end of file"),
    ("{", {}, "at 1: expected string or '}'"),
    ("[1 2]", [1], "at 3: expected ',' or ']'"),
    ("[1, , 2]", [1, 1, 2], "at 3: expected value"),
    (
        "[1, [{, 2]", [1, [{}, 2]],
        "at 6: expected string or '}', at 10: expected ']'"
    ),
    ("[1, }, 2]", [1, {}, 2], "at 4: expected value"),
    ('{"key": }', {"key": 1}, "at 7: expected value"),
    ('{"key": ]', {"key": []}, "at 8: expected value, at 9: expected '}'"),
    (
        '{"key": 2]', {"key": 2},
        "at 9: expected ',' or '}', at 9: expected end of file"
    ),
    (
        '{"key": 0,', {"key": 0, "a": 1},
        "at 10: expected string, at 10: expected ':', " +
        "at 10: expected value, at 10: expected '}'"
    ),
    (
        '{"key": 0, ]', {"key": 0, "a": []},
        "at 10: expected string, at 11: expected ':', " +
        "at 11: expected value, at 12: expected '}'"
    ),
    ('{"key": @}', {"key": 1}, "at 7: expected value, at 8: expected '}'"),
]


@pytest.mark.parametrize("data, value, expected", DATA_RECOVERY)
def test_recovery(data: str, value: str, expected: str) -> None:
    r = run(json_scannerless.json, data, recover=True)
    assert value == r.unwrap(recover=True)
    with pytest.raises(ParseError) as err:
        r.unwrap()
    assert expected == str(err.value)
