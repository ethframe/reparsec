from typing import TypeVar

from .core import layout
from .core.types import ParseObj
from .parser import FnParser, Parser

__all__ = ("block", "same", "indented")

S = TypeVar("S")
V = TypeVar("V")


def block(parser: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(layout.block(parser.to_fn()))


def same(parser: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(layout.same(parser.to_fn()))


def indented(delta: int, parser: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(layout.indented(delta, parser.to_fn()))
