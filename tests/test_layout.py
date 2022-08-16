from typing import List

import pytest

from reparsec import ParseError, Parser
from reparsec.layout import aligned, block, indented
from reparsec.scannerless import parse, regexp
from reparsec.sequence import eof, sym

a = sym("a")
ws = regexp(r"\s+")

DATA_POSITIVE = [
    (block(a), "a", "a"),
    (aligned(a), "a", "a"),
    (block(aligned(a)), "a", "a"),
    (ws >> indented(2, a), "  a", "a"),
]


@pytest.mark.parametrize("parser, data, expected", DATA_POSITIVE)
@pytest.mark.parametrize("recover", [False, True])
def test_recovery(
        parser: Parser[str, object], data: str, expected: object,
        recover: bool) -> None:
    assert parse(parser << eof(), data, recover=recover).unwrap() == expected


DATA_NEGATIVE = [
    (ws >> indented(2, a), " a", ["indentation"]),
    (ws >> aligned(a), " a", ["indentation"]),
]


@pytest.mark.parametrize("parser, data, expected", DATA_NEGATIVE)
@pytest.mark.parametrize("recover", [False, True])
def test_negative(
        parser: Parser[str, str], data: str, expected: List[str],
        recover: bool) -> None:
    with pytest.raises(ParseError) as err:
        parse(parser, data, recover=recover).unwrap()
    assert err.value.errors[0].expected == expected
