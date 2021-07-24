from abc import abstractmethod
from enum import Enum
from itertools import chain
from typing import (
    Callable, Generic, Iterable, List, Optional, Sequence, Tuple, TypeVar,
    Union
)

from typing_extensions import Final

T = TypeVar("T")
V = TypeVar("V")
U = TypeVar("U")


class _Error(int, Enum):
    error = 0


Value = Union[V, _Error]
ERROR: Final = _Error.error


class Result(Generic[T, V]):
    __slots__ = ("pos", "value", "expected")

    def __init__(
            self, pos: int, value: Value[V],
            expected: Iterable[str] = ()) -> None:
        self.pos = pos
        self.value = value
        self.expected = expected

    def __repr__(self) -> str:
        self.expected = list(self.expected)
        return "<Result(pos={!r}, value={!r}, expected={!r})>".format(
            self.pos, self.value, self.expected
        )

    def fmap(self, fn: Callable[[V], U]) -> "Result[T, U]":
        return Result(
            self.pos,
            ERROR if self.value is ERROR else fn(self.value),
            self.expected
        )


class Parser(Generic[T, V]):
    @abstractmethod
    def __call__(self, pos: int, stream: Sequence[T]) -> Result[T, V]:
        ...

    def fmap(self, fn: Callable[[V], U]) -> "Parser[T, U]":
        return _FnWrapper(lambda p, s: self(p, s).fmap(fn))

    def bind(self, fn: Callable[[V], "Parser[T, U]"]) -> "Parser[T, U]":
        def bind(pos: int, stream: Sequence[T]) -> Result[T, U]:
            r1 = self(pos, stream)
            if r1.value is ERROR:
                return Result(r1.pos, ERROR, r1.expected)
            return fn(r1.value)(r1.pos, stream)

        return _FnWrapper(bind)

    def __add__(self, other: "Parser[T, U]") -> "Parser[T, Tuple[V, U]]":
        def add(pos: int, stream: Sequence[T]) -> Result[T, Tuple[V, U]]:
            r1 = self(pos, stream)
            if r1.value is ERROR:
                return Result(r1.pos, ERROR, r1.expected)
            r2 = other(r1.pos, stream)
            if r1.pos != pos:
                r2.expected = r1.expected
            else:
                r2.expected = chain(r1.expected, r2.expected)
            v = r1.value
            return r2.fmap(lambda u: (v, u))

        return _FnWrapper(add)

    def __or__(self, other: "Parser[T, V]") -> "Parser[T, V]":
        def or_(pos: int, stream: Sequence[T]) -> Result[T, V]:
            r1 = self(pos, stream)
            if r1.pos != pos:
                return r1
            r2 = other(pos, stream)
            if r1.value is ERROR or r2.pos != pos:
                r2.expected = chain(r1.expected, r2.expected)
                return r2
            r1.expected = chain(r1.expected, r2.expected)
            return r1

        return _FnWrapper(or_)


class _FnWrapper(Parser[T, V]):
    __slots__ = ("_fn",)

    def __init__(self, fn: Callable[[int, Sequence[T]], Result[T, V]]):
        self._fn = fn

    def __call__(self, pos: int, stream: Sequence[T]) -> Result[T, V]:
        return self._fn(pos, stream)


class Pure(Parser[T, V]):
    __slots__ = ("_x",)

    def __init__(self, x: V):
        self._x = x

    def __call__(self, pos: int, stream: Sequence[T]) -> Result[T, V]:
        return Result(pos, self._x)


pure = Pure


def satisfy(test: Callable[[T], bool]) -> Parser[T, T]:
    def satisfy(pos: int, stream: Sequence[T]) -> Result[T, T]:
        if pos < len(stream):
            c = stream[pos]
            if test(c):
                return Result(pos + 1, c)
        return Result(pos, ERROR)
    return _FnWrapper(satisfy)


def maybe(parser: Parser[T, V]) -> Parser[T, Optional[V]]:
    def maybe(pos: int, stream: Sequence[T]) -> Result[T, Optional[V]]:
        r = parser(pos, stream)
        if r.value is ERROR:
            return Result(pos, None)
        return Result(r.pos, r.value, r.expected)
    return _FnWrapper(maybe)


def many(parser: Parser[T, V]) -> Parser[T, List[V]]:
    def many(pos: int, stream: Sequence[T]) -> Result[T, List[V]]:
        value: List[V] = []
        r = parser(pos, stream)
        while r.value is not ERROR:
            value.append(r.value)
            pos = r.pos
            r = parser(pos, stream)
        return Result(pos, value)
    return _FnWrapper(many)


def label(parser: Parser[T, V], expected: str) -> Parser[T, V]:
    def label(pos: int, stream: Sequence[T]) -> Result[T, V]:
        r = parser(pos, stream)
        if r.pos == pos:
            r.expected = [expected]
        return r
    return _FnWrapper(label)


def char(c: str) -> Parser[str, str]:
    return label(satisfy(lambda v: v == c), repr(c))


letter: Parser[str, str] = label(satisfy(lambda v: v.isalpha()), "letter")
digit: Parser[str, str] = label(satisfy(lambda v: v.isdigit()), "digit")
