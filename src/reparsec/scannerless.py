from typing import TypeVar, Union

from .core import scannerless
from .core.state import Loc
from .output import ParseResult
from .parser import FnParser, Parser, run_c

V = TypeVar("V", bound=object)


def literal(s: str) -> Parser[str, str]:
    return FnParser(scannerless.literal(s))


def regexp(pat: str, group: Union[int, str] = 0) -> Parser[str, str]:
    return FnParser(scannerless.regexp(pat, group))


def run(
        parser: Parser[str, V], stream: str,
        recover: bool = False) -> ParseResult[V, str]:
    return run_c(
        parser, stream, scannerless.SlCtx(0, Loc(0, 0, 0)), recover
    )
