from typing import List

import pytest

from reparsec.parser import Parser, digit, letter, sym
from reparsec.result import ParseError

ident = (
    (letter | sym("_")) + (letter | digit | sym("_")).many()
).fmap(lambda v: v[0] + "".join(v[1]))


DATA_POSITIVE = [
    (ident, "_def", "_def"),
]


@pytest.mark.parametrize("parser, data, value", DATA_POSITIVE)
def test_positive(parser: Parser[str, str], data: str, value: str) -> None:
    assert value == parser.parse(data).unwrap()


DATA_NEGATIVE = [
    (ident, "0_def", ["letter", "'_'"]),
]


@pytest.mark.parametrize("parser, data, expected", DATA_NEGATIVE)
def test_negative(
        parser: Parser[str, str], data: str, expected: List[str]) -> None:
    with pytest.raises(ParseError) as err:
        parser.parse(data).unwrap()
    assert expected == err.value.errors[0].expected
