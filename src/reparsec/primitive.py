"""
Primitive input-agnostic parsers.
"""

from typing import TypeVar

from .core import primitive
from .parser import FnParser, TupleParser

__all__ = ("Pure", "PureFn", "unexpected")

S_contra = TypeVar("S_contra", contravariant=True)
A_co = TypeVar("A_co", covariant=True)


class Pure(primitive.Pure[S_contra, A_co], TupleParser[S_contra, A_co]):
    """
    Parser that always succeeds, consumes no input, and returns constant value.

    >>> from reparsec.primitive import Pure

    >>> Pure(0).parse("").unwrap()
    0

    :param x: Value to return
    """


class PureFn(primitive.PureFn[S_contra, A_co], TupleParser[S_contra, A_co]):
    """
    Parser that always succeeds, consumes no input, and returns the result of
    function.

    >>> from reparsec.primitive import PureFn

    >>> PureFn(lambda: list()).parse("").unwrap()
    []

    :param fn: Function that produces a value to return
    """


def unexpected(expected: str) -> TupleParser[object, None]:
    """
    Parser that always fails and consumes no input.

    >>> from reparsec.primitive import unexpected

    >>> unexpected("a").parse("").unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 0: expected a

    :param expected: Error label
    """

    return FnParser(primitive.unexpected(expected))
