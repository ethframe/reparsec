from typing import TypeVar, Union

from .core import scannerless
from .output import ParseResult
from .parser import FnParser, Parser

__all__ = ("literal", "regexp", "parse")

V = TypeVar("V")


def literal(s: str) -> Parser[str, str]:
    return FnParser(scannerless.literal(s))


def regexp(pat: str, group: Union[int, str] = 0) -> Parser[str, str]:
    return FnParser(scannerless.regexp(pat, group))


def parse(
        parser: Parser[str, V], stream: str,
        recover: bool = False) -> ParseResult[V, str]:
    return parser.parse(
        stream, recover,
        get_loc=scannerless.get_loc,
        fmt_loc=lambda l: "{}:{}".format(l.line + 1, l.col + 1)
    )
