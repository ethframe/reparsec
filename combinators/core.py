from abc import abstractmethod
from enum import Enum
from itertools import chain
from typing import (
    Any, Callable, Generic, Iterable, List, Optional, Sequence, Tuple, Type, TypeVar,
    Union
)

from typing_extensions import Final

T = TypeVar("T")
V = TypeVar("V")
U = TypeVar("U")


class ParseError(Exception):
    def __init__(self, pos: int, expected: List[str]):
        super().__init__(pos, expected)
        self.pos = pos
        self.expected = expected

    def __str__(self) -> str:
        if not self.expected:
            return "at {}: unexpected input".format(self.pos)
        if len(self.expected) == 1:
            return "at {}: expected {}".format(self.pos, self.expected[0])
        return "at {}: expected {} or {}".format(
            self.pos, ', '.join(self.expected[:-1]), self.expected[-1]
        )


class _Error(int, Enum):
    error = 0


Value = Union[V, _Error]
ERROR: Final = _Error.error


class Result(Generic[V]):
    def __init__(
            self, pos: int, value: Value[V],
            expected: Iterable[str] = ()) -> None:
        self.pos = pos
        self.value = value
        self.expected = expected

    def unwrap(self) -> V:
        if self.value is ERROR:
            raise ParseError(self.pos, list(self.expected))
        return self.value


class Parser(Generic[T, V]):
    def parse(self, stream: Sequence[T]) -> Result[V]:
        return self(0, stream)

    @abstractmethod
    def __call__(self, pos: int, stream: Sequence[T]) -> Result[V]:
        ...

    def fmap(self, fn: Callable[[V], U]) -> "Parser[T, U]":
        def fmap(pos: int, stream: Sequence[T]) -> Result[U]:
            r = self(pos, stream)
            return Result(
                r.pos,
                ERROR if r.value is ERROR else fn(r.value),
                r.expected
            )

        return FnParser(fmap)

    def bind(self, fn: Callable[[V], "Parser[T, U]"]) -> "Parser[T, U]":
        def bind(pos: int, stream: Sequence[T]) -> Result[U]:
            r1 = self(pos, stream)
            if r1.value is ERROR:
                return Result(r1.pos, ERROR, r1.expected)
            return fn(r1.value)(r1.pos, stream)

        return FnParser(bind)

    def label(self, expected: str) -> "Parser[T, V]":
        return label(self, expected)

    def __add__(self, other: "Parser[T, U]") -> "Parser[T, Tuple[V, U]]":
        def add(pos: int, stream: Sequence[T]) -> Result[Tuple[V, U]]:
            r1 = self(pos, stream)
            if r1.value is ERROR:
                return Result(r1.pos, ERROR, r1.expected)
            r2 = other(r1.pos, stream)
            return Result(
                r2.pos,
                ERROR if r2.value is ERROR else (r1.value, r2.value),
                chain(r1.expected, r2.expected)
                if r1.pos == pos else r1.expected
            )

        return FnParser(add)

    def __or__(self, other: "Parser[T, V]") -> "Parser[T, V]":
        def or_(pos: int, stream: Sequence[T]) -> Result[V]:
            r1 = self(pos, stream)
            if r1.pos != pos:
                return r1
            r2 = other(pos, stream)
            if r1.value is ERROR or r2.pos != pos:
                r2.expected = chain(r1.expected, r2.expected)
                return r2
            r1.expected = chain(r1.expected, r2.expected)
            return r1

        return FnParser(or_)


class FnParser(Parser[T, V]):
    def __init__(self, fn: Callable[[int, Sequence[T]], Result[V]]):
        self._fn = fn

    def __call__(self, pos: int, stream: Sequence[T]) -> Result[V]:
        return self._fn(pos, stream)


class Pure(Parser[T, V]):
    def __init__(self, x: V):
        self._x = x

    def __call__(self, pos: int, stream: Sequence[T]) -> Result[V]:
        return Result(pos, self._x)


pure = Pure


class Eof(Parser[T, None]):
    def __call__(self, pos: int, stream: Sequence[T]) -> Result[None]:
        if pos == len(stream):
            return Result(pos, None)
        return Result(pos, ERROR, ["end of file"])


eof = Eof


def satisfy(test: Callable[[T], bool]) -> Parser[T, T]:
    def satisfy(pos: int, stream: Sequence[T]) -> Result[T]:
        if pos < len(stream):
            c = stream[pos]
            if test(c):
                return Result(pos + 1, c)
        return Result(pos, ERROR)

    return FnParser(satisfy)


def maybe(parser: Parser[T, V]) -> Parser[T, Optional[V]]:
    def maybe(pos: int, stream: Sequence[T]) -> Result[Optional[V]]:
        r = parser(pos, stream)
        if r.value is ERROR and r.pos == pos:
            return Result(pos, None)
        return Result(r.pos, r.value, r.expected)

    return FnParser(maybe)


def many(parser: Parser[T, V]) -> Parser[T, List[V]]:
    def many(pos: int, stream: Sequence[T]) -> Result[List[V]]:
        value: List[V] = []
        r = parser(pos, stream)
        while r.value is not ERROR:
            value.append(r.value)
            pos = r.pos
            r = parser(pos, stream)
        return Result(pos, value)

    return FnParser(many)


def label(parser: Parser[T, V], expected: str) -> Parser[T, V]:
    def label(pos: int, stream: Sequence[T]) -> Result[V]:
        r = parser(pos, stream)
        if r.pos == pos:
            r.expected = [expected]
        return r

    return FnParser(label)


def sym(s: T) -> Parser[T, T]:
    def sym(pos: int, stream: Sequence[T]) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Result(pos + 1, t)
        return Result(pos, ERROR, [repr(s)])

    return FnParser(sym)


letter: Parser[str, str] = satisfy(str.isalpha).label("letter")
digit: Parser[str, str] = satisfy(str.isdigit).label("digit")


class Delay(Parser[T, V]):
    def __init__(self) -> None:
        def _undefined(pos: int, stream: Sequence[T]) -> Result[V]:
            raise RuntimeError("Delayed parser was not defined")

        self._parser: Parser[T, V] = FnParser(_undefined)

    def define(self, parser: Parser[T, V]) -> None:
        self._parser = parser

    def __call__(self, pos: int, stream: Sequence[T]) -> Result[V]:
        return self._parser(pos, stream)


def sep_by(parser: Parser[T, V], sep: Parser[T, U]) -> Parser[T, List[V]]:
    return maybe(parser + many((sep + parser).fmap(lambda v: v[1]))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )
