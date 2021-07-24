# type: ignore [misc]
from ast import literal_eval
import re
from typing import List, Tuple

import pytest

from combinators.core import Delay, Parser, many, sep_by, sym, eof
from combinators.lexer import split_tokens, token, Token

spec = re.compile(r"""
[ \n\r\t]+
|(?P<punct>[{}:,[\]])
|(?P<bool>true|false)
|(?P<null>null)
|(?P<float>-?(?:[0-9]|[1-9][0-9]+)(?:
    (?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)|(?:\.[0-9]+)
))
|(?P<integer>-?(?:[0-9]|[1-9][0-9]+))
|(?P<string>"(?:
    [\x20\x21\x23-\x5B\x5D-\U0010FFFF]
    |\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4})
)+")
""", re.VERBOSE)

string: Parser[Token, str] = token("string").fmap(
    lambda t: literal_eval(t.value))
integer = token("integer").fmap(lambda t: int(t.value))
number = token("float").fmap(lambda t: float(t.value))
boolean = token("bool").fmap(lambda t: t.value == "true")
null = token("null").fmap(lambda t: None)


def punct(x: str) -> Parser[Token, Token]:
    return sym(Token("punct", x)).label(repr(x))


value: Delay[Token, object] = Delay()
value.define(
    integer | number | boolean | null | string |
    (
        punct("{") + sep_by(
            (string + punct(":") + value).fmap(lambda v: (v[0][0], v[1])),
            punct(",")
        ).fmap(lambda v: dict(v)) + punct("}")
    ).fmap(lambda v: v[0][1]) |
    (
        punct("[") + sep_by(value, punct(",")) + punct("]")
    ).fmap(lambda v: v[0][1])
)

json = (value + eof()).fmap(lambda v: v[0])

DATA_POSITIVE: List[Tuple[str, object]] = [
    (r"1", 1),
    (r"1.0", 1.0),
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
    assert json.parse(split_tokens(data, spec)).unwrap() == expected
