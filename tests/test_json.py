from ast import literal_eval
import re
from typing import List, Tuple

import pytest

from combinators.core import Delay, ParseError, Parser, sym, eof
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


def punct(x: str) -> Parser[Token, Token]:
    return sym(Token("punct", x)).label(repr(x))


JsonParser = Parser[Token, object]

value: Delay[Token, object] = Delay()

string: JsonParser = token("string").fmap(lambda t: literal_eval(t.value))
integer: JsonParser = token("integer").fmap(lambda t: int(t.value))
number: JsonParser = token("float").fmap(lambda t: float(t.value))
boolean: JsonParser = token("bool").fmap(lambda t: t.value == "true")
null: JsonParser = token("null").fmap(lambda t: None)
json_dict: JsonParser = punct("{").rseq(
    (string.lseq(punct(":")) + value).sep_by(punct(",")).fmap(lambda v: dict(v))
).lseq(punct("}")).label("object")
json_list: JsonParser = punct("[").rseq(
    value.sep_by(punct(","))
).lseq(punct("]")).label("list")

value.define(
    (
        integer | number | boolean | null | string | json_dict | json_list
    ).label("value")
)

json = value.lseq(eof())

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


@pytest.mark.parametrize("data, expected", DATA_POSITIVE)  # type: ignore
def test_positive(data: str, expected: object) -> None:
    assert json.parse(split_tokens(data, spec)).unwrap() == expected


DATA_NEGATIVE = [
    ("", "at 0: expected value"),
    ("1 1", "at 1: expected end of file"),
    ("{", "at 1: expected string or '}'"),
    ('{"key"', "at 2: expected ':'"),
    ('{"key":', "at 3: expected value"),
    ('{"key": 0', "at 4: expected ',' or '}'"),
    ('{"key": 0,', "at 5: expected string"),
    ("[", "at 1: expected value or ']'"),
    ("[0", "at 2: expected ',' or ']'"),
    ("[0,", "at 3: expected value"),
]


@pytest.mark.parametrize("data, expected", DATA_NEGATIVE)  # type: ignore
def test_negative(data: str, expected: str) -> None:
    with pytest.raises(ParseError) as err:
        json.parse(split_tokens(data, spec)).unwrap()
    assert str(err.value) == expected
