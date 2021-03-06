"""
Primitive input-agnostic parsers.
"""

from typing import TypeVar

from .core import primitive
from .parser import TupleParser

__all__ = ("Pure", "PureFn", "InsertValue", "InsertFn")

S_contra = TypeVar("S_contra", contravariant=True)
V_co = TypeVar("V_co", covariant=True)


class Pure(primitive.Pure[S_contra, V_co], TupleParser[S_contra, V_co]):
    """
    Parser that always succeeds, consumes no input, and returns constant value.

    >>> from reparsec.primitive import Pure

    >>> Pure(0).parse("").unwrap()
    0

    :param x: Value to return
    """


class PureFn(primitive.PureFn[S_contra, V_co], TupleParser[S_contra, V_co]):
    """
    Parser that always succeeds, consumes no input, and returns the result of
    function.

    >>> from reparsec.primitive import PureFn

    >>> PureFn(lambda: list()).parse("").unwrap()
    []

    :param fn: Function that produces a value to return
    """


class InsertValue(
        primitive.InsertValue[S_contra, V_co], TupleParser[S_contra, V_co]):
    """
    Parser that consumes no input, fails when recovery is not allowed, and
    recovers with constant value.

    >>> from reparsec.primitive import InsertValue

    >>> parser = InsertValue(0, "zero")

    >>> parser.parse("").unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 0: unexpected input
    >>> parser.parse("", recover=True).unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 0: unexpected input (inserted zero)
    >>> parser.parse("", recover=True).unwrap(recover=True)
    0

    :param x: Value to return
    :param label: Label to use in the description of recovery operation
    """


class InsertFn(
        primitive.InsertFn[S_contra, V_co], TupleParser[S_contra, V_co]):
    """
    Parser that consumes no input, fails when recovery is not allowed, and
    recovers with constant value.

    >>> from reparsec.primitive import InsertFn

    >>> InsertFn(lambda: list()).parse("", recover=True).unwrap(recover=True)
    []

    :param fn: Function that produces a value to return
    :param label: Label to use in the description of recovery operation
    """
