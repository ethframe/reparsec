"""
Combinators for layout-sensitive parsing. They relies on line and colun
tracking, and should be used with proper ``get_col`` function passed to
:meth:`Parser.parse`, e.g. the one that is passed by
:func:`reparsec.scannerless.parse` or :func:`reparsec.lexer.parse`.
"""

from typing import TypeVar

from .core import layout
from .core.parser import ParseObj
from .parser import FnParser, TupleParser

__all__ = ("block", "same", "indented")

S = TypeVar("S")
V = TypeVar("V")


def block(parser: ParseObj[S, V]) -> TupleParser[S, V]:
    """
    Applies parser with anchor set to current column.

    :param parser: Parser
    """

    return FnParser(layout.block(parser.to_fn()))


def same(parser: ParseObj[S, V]) -> TupleParser[S, V]:
    """
    Applies parser if anchor is equal to current column, otherwise fails.

    :param parser: Parser
    """

    return FnParser(layout.same(parser.to_fn()))


def indented(delta: int, parser: ParseObj[S, V]) -> TupleParser[S, V]:
    """
    If current column is greater than anchor by ``delta``, applies parser with
    anchor set to current column, otherwise fails.

    :param delta: Indentation size in columns
    :param parser: Parser
    """

    return FnParser(layout.indented(delta, parser.to_fn()))
