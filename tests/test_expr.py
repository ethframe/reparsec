from typing import List, Tuple

import pytest

from reparsec import ParseError
from reparsec.scannerless import parse

from .parsers import expr

DATA_POSITIVE: List[Tuple[str, int]] = [
    ("1", 1),
    ("1 + 2", 3),
    ("2 - 1", 1),
    ("2 * 3", 6),
    ("1 + 2 * 3", 7),
    ("(1 + 2) * 3", 9),
    ("((1) + (2))", 3),
]


@pytest.mark.parametrize("data, expected", DATA_POSITIVE)
def test_positive(data: str, expected: int) -> None:
    assert expr.eval(data) == expected


DATA_NEGATIVE = [
    ("", "at 1:1: expected '('"),
    ("1 1", "at 1:3: expected end of file"),
    ("1 +", "at 1:4: expected '('"),
    ("1 )", "at 1:3: expected end of file"),
    ("1 + 2 * * (3 + 4)", "at 1:9: expected '('"),
]


@pytest.mark.parametrize("data, expected", DATA_NEGATIVE)
def test_negative(data: str, expected: str) -> None:
    with pytest.raises(ParseError) as err:
        expr.eval(data)
    assert str(err.value) == expected


DATA_RECOVERY: List[Tuple[str, int, str]] = [
    ("1 1", 1, "at 1:3: expected end of file (skipped 1 token)"),
    ("1 )", 1, "at 1:3: expected end of file (skipped 1 token)"),
    (
        "1 + 2 * * (3 + 4 5)", 15,
        "at 1:9: expected '(' (skipped 2 tokens), " +
        "at 1:18: expected ')' (skipped 1 token)"
    ),
]


@pytest.mark.parametrize("data, value, expected", DATA_RECOVERY)
def test_recovery(data: str, value: int, expected: str) -> None:
    r = parse(expr.parser, data, recover=True)
    assert r.unwrap(recover=True) == value
    with pytest.raises(ParseError) as err:
        r.unwrap()
    assert str(err.value) == expected
