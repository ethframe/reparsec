from typing import TypeVar, Union

from .core import scannerless
from .output import ParseResult
from .parser import FnParser, Parser, run_c

__all__ = ("literal", "regexp", "run")

V = TypeVar("V", bound=object)


def literal(s: str) -> Parser[str, str]:
    return FnParser(scannerless.literal(s))


def regexp(pat: str, group: Union[int, str] = 0) -> Parser[str, str]:
    return FnParser(scannerless.regexp(pat, group))


def run(
        parser: Parser[str, V], stream: str,
        recover: bool = False) -> ParseResult[V, str]:
    return run_c(
        parser, stream, scannerless.get_loc,
        lambda l: "{}:{}".format(l.line + 1, l.col + 1), recover
    )
