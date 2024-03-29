import re
from typing import Match, Sequence

from reparsec import Delay, Parser
from reparsec.lexer import Token, parse, split_tokens, token
from reparsec.sequence import eof, sym

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


def punct(x: str) -> Parser[Sequence[Token], Token]:
    return sym(Token("punct", x), repr(x))


value = Delay[Sequence[Token], object]()

string = token("string").fmap(lambda t: unescape(t.value))
integer = token("integer").fmap(lambda t: int(t.value))
number = token("float").fmap(lambda t: float(t.value))
boolean = token("bool").fmap(lambda t: t.value == "true")
null = token("null").fmap(lambda t: None)
json_dict = (
    (string.recover_with("a", "'\"a\"'") << punct(":")) + value
).sep_by(punct(",")).fmap(lambda v: dict(v)).between(
    punct("{"), punct("}")
).label("object")
json_list = value.sep_by(punct(",")).between(
    punct("["), punct("]")
).label("list")

value.define(
    (
        (integer | number | boolean | null | string).recover_with(1)
        | json_dict.recover() | json_list.recover()
    ).label("value")
)

parser = value << eof()


def loads(src: str) -> object:
    return parse(parser, split_tokens(src, spec)).unwrap()
