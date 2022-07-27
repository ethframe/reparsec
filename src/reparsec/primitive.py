"""
Primitive input-agnostic parsers.
"""

from typing import TypeVar

from .core import primitive
from .parser import TupleParser

__all__ = ("Pure", "PureFn")

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
