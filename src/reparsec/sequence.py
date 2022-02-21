from typing import Callable, Sequence, Sized, TypeVar

from .core import sequence
from .parser import FnParser, Parser

T = TypeVar("T")


def eof() -> Parser[Sized, None]:
    return FnParser(sequence.eof())


def satisfy(test: Callable[[T], bool]) -> Parser[Sequence[T], T]:
    return FnParser(sequence.satisfy(test))


def sym(s: T) -> Parser[Sequence[T], T]:
    return FnParser(sequence.sym(s))


letter: Parser[Sequence[str], str] = satisfy(str.isalpha).label("letter")
digit: Parser[Sequence[str], str] = satisfy(str.isdigit).label("digit")
