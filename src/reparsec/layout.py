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

__all__ = ("block", "aligned", "indented")

S = TypeVar("S")
A = TypeVar("A")


def block(parser: ParseObj[S, A]) -> TupleParser[S, A]:
    """
    Applies parser with column mark set to current column.

    :param parser: Parser
    """

    return FnParser(layout.block(parser.to_fns()))


def aligned(parser: ParseObj[S, A]) -> TupleParser[S, A]:
    """
    Applies parser if column mark is equal to current column, otherwise fails.

    :param parser: Parser
    """

    return FnParser(layout.aligned(parser.to_fns()))


def indented(delta: int, parser: ParseObj[S, A]) -> TupleParser[S, A]:
    """
    If current column is greater than column mark by ``delta``, applies parser
    with column mark set to current column, otherwise fails.

    :param delta: Indentation size in columns
    :param parser: Parser
    """

    return FnParser(layout.indented(delta, parser.to_fns()))
