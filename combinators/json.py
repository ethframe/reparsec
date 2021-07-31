import re
from typing import Match

from .core import Delay, Parser, eof, sym
from .lexer import Token, split_tokens, token_ins

spec = re.compile(r"""
[ \n\r\t]+
|(?P<punct>[{}:,[\]])
|(?P<bool>true|false)
|(?P<null>null)
|(?P<float>-?(?:0|[1-9][0-9]*)(?:
    (?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)|(?:\.[0-9]+)
))
|(?P<integer>-?(?:0|[1-9][0-9]*))
|"(?P<string>(?:
    [\x20\x21\x23-\x5B\x5D-\U0010FFFF]
    |\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4})
)+)"
|(?P<_>.)
""", re.VERBOSE)


escape = re.compile(r"""
\\(?:(?P<simple>["\\/bfnrt])|u(?P<unicode>[0-9a-fA-F]{4}))
""", re.VERBOSE)

simple = {
    '"': '"', "\\": "\\", "/": "/",
    "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"
}


def unescape(s: str) -> str:
    def sub(m: Match[str]) -> str:
        if m.lastgroup == "unicode":
            return chr(int(m.group("unicode"), 16))
        return simple[m.group("simple")]

    return escape.sub(sub, s)


def punct(x: str) -> Parser[Token, Token]:
    return sym(Token("punct", x)).label(repr(x))


JsonParser = Parser[Token, object]

value: Delay[Token, object] = Delay()

string: JsonParser = token_ins("string", "a").fmap(lambda t: unescape(t.value))
integer: JsonParser = token_ins("integer", "1").fmap(lambda t: int(t.value))
number: JsonParser = token_ins("float", "1.0").fmap(lambda t: float(t.value))
boolean: JsonParser = token_ins("bool", "true").fmap(
    lambda t: t.value == "true"
)
null: JsonParser = token_ins("null", "null").fmap(lambda t: None)
json_dict: JsonParser = (string.lseq(punct(":")) + value).sep_by(
    punct(",")
).fmap(lambda v: dict(v)).between(punct("{"), punct("}")).label("object")
json_list: JsonParser = value.sep_by(punct(",")).between(
    punct("["), punct("]")
).label("list")

value.define(
    (
        integer | number | boolean | null | string | json_dict | json_list
    ).label("value")
)

json = value.lseq(eof())


def parse(src: str) -> object:
    return json.parse(split_tokens(src, spec)).unwrap()
