from typing import TypeVar, Union

from .core import scannerless
from .core.state import Loc
from .output import ParseResult
from .parser import FnParser, Parser, _run_parser

V = TypeVar("V", bound=object)


def prefix(s: str) -> Parser[str, str]:
    return FnParser(scannerless.prefix(s))


def regexp(pat: str, group: Union[int, str] = 0) -> Parser[str, str]:
    return FnParser(scannerless.regexp(pat, group))


def run(
        parser: Parser[str, V], stream: str,
        recover: bool = False) -> ParseResult[V, str]:
    return _run_parser(
        parser, stream, scannerless.SlCtx(0, Loc(0, 0, 0)), recover,
        lambda l: "{!r}:{!r}".format(l.line + 1, l.col + 1)
    )
