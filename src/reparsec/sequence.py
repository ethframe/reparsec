"""
Parsers for arbitrary sequences.
"""

from typing import Callable, Optional, Sequence, Sized, TypeVar

from .core import sequence
from .parser import FnParser, TupleParser

__all__ = ("eof", "satisfy", "sym", "letter", "digit")

A = TypeVar("A")


def eof() -> TupleParser[Sized, None]:
    """
    Succeeds at the end of the input.

    >>> from reparsec.sequence import eof

    >>> eof().parse("").unwrap()
    >>> eof().parse("a").unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 0: expected end of file
    """

    return FnParser(sequence.eof())


def satisfy(test: Callable[[A], bool]) -> TupleParser[Sequence[A], A]:
    """
    Succeeds for sequence element for which ``test`` returns ``True`` and
    returns that element.

    >>> from reparsec.sequence import satisfy

    >>> parser = satisfy(lambda c: c.isalpha())

    >>> parser.parse("a").unwrap()
    'a'
    >>> parser.parse("0").unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 0: unexpected input

    :param test: Predicate for sequence elements
    """

    return FnParser(sequence.satisfy(test))


def sym(s: A, label: Optional[str] = None) -> TupleParser[Sequence[A], A]:
    """
    Parses ``s`` and returns the parsed element.

    >>> from reparsec.sequence import sym

    >>> sym("a").parse("a").unwrap()
    'a'
    >>> sym("a").parse("0").unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 0: expected 'a'

    :param s: Value to parse
    :param label: Label to use instead of ``repr(s)``
    """

    return FnParser(sequence.sym(s, label))


letter: TupleParser[Sequence[str], str] = satisfy(str.isalpha).label("letter")
digit: TupleParser[Sequence[str], str] = satisfy(str.isdigit).label("digit")
