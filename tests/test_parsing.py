# type: ignore [misc]

from typing import List

import pytest

from combinators.core import (
    ERROR, Parser, StringLexer, char, digit, letter, many
)

ident = (
    (letter | char("_")) + many(letter | digit | char("_"))
).fmap(lambda v: v[0] + "".join(v[1]))


DATA_POSITIVE = [
    (ident, "_def", "_def"),
]


@pytest.mark.parametrize("parser, data, value", DATA_POSITIVE)
def test_positive(parser: Parser[str, str], data: str, value: str) -> None:
    result = parser(StringLexer(data, 0))
    assert result.value == value


DATA_NEGATIVE = [
    (ident, "0_def", ["letter", "'_'"]),
]


@pytest.mark.parametrize("parser, data, expected", DATA_NEGATIVE)
def test_negative(
        parser: Parser[str, str], data: str, expected: List[str]) -> None:
    result = parser(StringLexer(data, 0))
    assert result.value is ERROR
    assert list(result.expected) == expected
