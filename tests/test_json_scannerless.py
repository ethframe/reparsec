from typing import List, Tuple

import pytest

from reparsec import ParseError
from reparsec.scannerless import run

from .parsers import json_scannerless

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
    assert json_scannerless.loads(data) == expected


DATA_NEGATIVE = [
    ("", "at 1:1: expected value"),
    ("1 1", "at 1:3: expected end of file"),
    ("{", "at 1:2: expected string or '}'"),
    ('{"key"', "at 1:7: expected ':'"),
    ('{"key":', "at 1:8: expected value"),
    ('{"key": 0', "at 1:10: expected ',' or '}'"),
    ('{"key": 0,', "at 1:11: expected string"),
    ("[", "at 1:2: expected value or ']'"),
    ("[0", "at 1:3: expected ',' or ']'"),
    ("[0,", "at 1:4: expected value"),
]


@pytest.mark.parametrize("data, expected", DATA_NEGATIVE)
def test_negative(data: str, expected: str) -> None:
    with pytest.raises(ParseError) as err:
        json_scannerless.loads(data)
    assert str(err.value) == expected


DATA_RECOVERY: List[Tuple[str, object, str]] = [
    ("1 1", 1, "at 1:3: expected end of file (skipped 1 token)"),
    ("{", {}, "at 1:2: expected string or '}' (inserted '}')"),
    ("[1 2]", [1], "at 1:4: expected ',' or ']' (skipped 1 token)"),
    ("[1, , 2]", [1, 1, 2], "at 1:5: expected value (inserted 1)"),
    (
        "[1, [{, 2]", [1, [{}, 2]],
        "at 1:7: expected string or '}' (inserted '}'), " +
        "at 1:11: expected ']' (inserted ']')"
    ),
    ("[1, }, 2]", [1, {}, 2], "at 1:5: expected '{' (inserted '{')"),
    ('{"key": }', {"key": 1}, "at 1:9: expected value (inserted 1)"),
    (
        '{"key": ]', {"key": []},
        "at 1:9: expected '[' (inserted '['), " +
        "at 1:10: expected '}' (inserted '}')"
    ),
    (
        '{"key": 2]', {"key": 2},
        "at 1:10: expected ',' or '}' (inserted '}'), " +
        "at 1:10: expected end of file (skipped 1 token)"
    ),
    (
        '{"key": 0,', {"key": 0, "a": 1},
        "at 1:11: expected string (inserted '\"a\"'), " +
        "at 1:11: expected ':' (inserted ':'), " +
        "at 1:11: expected value (inserted 1), " +
        "at 1:11: expected '}' (inserted '}')"
    ),
    (
        '{"key": 0, ]', {"key": 0, "a": []},
        "at 1:12: expected string (inserted '\"a\"'), " +
        "at 1:12: expected ':' (inserted ':'), " +
        "at 1:12: expected '[' (inserted '['), " +
        "at 1:13: expected '}' (inserted '}')"
    ),
    (
        '{"key": @}', {"key": 1},
        "at 1:9: expected value (inserted 1), " +
        "at 1:9: expected '}' (skipped 1 token)"
    ),
]


@pytest.mark.parametrize("data, value, expected", DATA_RECOVERY)
def test_recovery(data: str, value: str, expected: str) -> None:
    r = run(json_scannerless.parser, data, recover=True)
    assert r.unwrap(recover=True) == value
    with pytest.raises(ParseError) as err:
        r.unwrap()
    assert str(err.value) == expected
