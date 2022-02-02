import re
from typing import Match

from .parser import Delay, Parser, eof, recover_value, regexp

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


def token(pat: str) -> Parser[str, str]:
    return regexp(r"[ \n\r\t]*" + pat, 1)


def punct(p: str) -> Parser[str, str]:
    return (
        regexp(r"[ \n\r\t]*({})".format(re.escape(p)), 1).label(repr(p)) |
        recover_value(p)
    )


JsonParser = Parser[str, object]

value: Delay[str, object] = Delay()

string: JsonParser = token(
    r'"(?P<string>(?:[\x20\x21\x23-\x5B\x5D-\U0010FFFF]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))+)"'
).label("string").fmap(unescape)
integer: JsonParser = token(
    r"(-?(?:0|[1-9][0-9]*))").label("integer").fmap(int)
number: JsonParser = token(
    r"(-?(?:0|[1-9][0-9]*)(?:(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)|(?:\.[0-9]+)))"
).label("number").fmap(float)
boolean: JsonParser = token(r"(true|false)").label("bool").fmap(
    lambda s: s == "true")
null: JsonParser = token(r"(null)").label("null").fmap(lambda _: None)
json_dict: JsonParser = (
    ((string | recover_value("a")) << punct(":")) + value
).sep_by(punct(",")).fmap(lambda v: dict(v)).between(
    punct("{"), punct("}")
).label("object")
json_list: JsonParser = value.sep_by(punct(",")).between(
    punct("["), punct("]")
).label("list")

value.define(
    (
        number | integer | boolean | null | string | recover_value(1)
        | json_dict | json_list
    ).label("value")
)

json = value << regexp(r"[ \n\r\t]*") << eof()


def parse(src: str) -> object:
    return json.parse(src).unwrap()
