from abc import abstractmethod
from enum import Enum
from itertools import chain
from typing import (
    Callable, Generic, Iterable, List, Optional, Sequence, Tuple, TypeVar,
    Union
)

from typing_extensions import Final

T = TypeVar("T")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")
X = TypeVar("X")


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


Value = Union[V_co, _Error]
ERROR: Final = _Error.error


class Result(Generic[V_co]):
    def __init__(
            self, pos: int, value: Value[V_co],
            expected: Iterable[str] = ()) -> None:
        self.pos = pos
        self.value = value
        self.expected = expected

    def unwrap(self) -> V_co:
        if self.value is ERROR:
            raise ParseError(self.pos, list(self.expected))
        return self.value


class Parser(Generic[T, V_co]):
    def parse(self, stream: Sequence[T]) -> Result[V_co]:
        return self(0, stream)

    @abstractmethod
    def __call__(self, pos: int, stream: Sequence[T]) -> Result[V_co]:
        ...

    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[T, U]":
        def fmap(pos: int, stream: Sequence[T]) -> Result[U]:
            r = self(pos, stream)
            return Result(
                r.pos,
                ERROR if r.value is ERROR else fn(r.value),
                r.expected
            )

        return FnParser(fmap)

    def bind(self, fn: Callable[[V_co], "Parser[T, U]"]) -> "Parser[T, U]":
        def bind(pos: int, stream: Sequence[T]) -> Result[U]:
            r1 = self(pos, stream)
            if r1.value is ERROR:
                return Result(r1.pos, ERROR, r1.expected)
            r2 = fn(r1.value)(r1.pos, stream)
            if r1.pos != pos and r1.pos != r2.pos:
                expected = r2.expected
            else:
                expected = chain(r1.expected, r2.expected)
            if r2.value is ERROR:
                return Result(r2.pos, ERROR, expected)
            return Result(r2.pos, r2.value, expected)

        return FnParser(bind)

    def lseq(self, other: "Parser[T, U]") -> "Parser[T, V_co]":
        def lseq(pos: int, stream: Sequence[T]) -> Result[V_co]:
            r1 = self(pos, stream)
            if r1.value is ERROR:
                return Result(r1.pos, ERROR, r1.expected)
            r2 = other(r1.pos, stream)
            if r1.pos != pos and r1.pos != r2.pos:
                expected = r2.expected
            else:
                expected = chain(r1.expected, r2.expected)
            if r2.value is ERROR:
                return Result(r2.pos, ERROR, expected)
            return Result(r2.pos, r1.value, expected)

        return FnParser(lseq)

    def rseq(self, other: "Parser[T, U]") -> "Parser[T, U]":
        def rseq(pos: int, stream: Sequence[T]) -> Result[U]:
            r1 = self(pos, stream)
            if r1.value is ERROR:
                return Result(r1.pos, ERROR, r1.expected)
            r2 = other(r1.pos, stream)
            if r1.pos != pos and r1.pos != r2.pos:
                expected = r2.expected
            else:
                expected = chain(r1.expected, r2.expected)
            if r2.value is ERROR:
                return Result(r2.pos, ERROR, expected)
            return Result(r2.pos, r2.value, expected)

        return FnParser(rseq)

    def __add__(self, other: "Parser[T, U]") -> "Parser[T, Tuple[V_co, U]]":
        def add(pos: int, stream: Sequence[T]) -> Result[Tuple[V_co, U]]:
            r1 = self(pos, stream)
            if r1.value is ERROR:
                return Result(r1.pos, ERROR, r1.expected)
            r2 = other(r1.pos, stream)
            if r1.pos != pos and r1.pos != r2.pos:
                expected = r2.expected
            else:
                expected = chain(r1.expected, r2.expected)
            if r2.value is ERROR:
                return Result(r2.pos, ERROR, expected)
            return Result(r2.pos, (r1.value, r2.value), expected)

        return FnParser(add)

    def __or__(self, other: "Parser[T, V_co]") -> "Parser[T, V_co]":
        def or_(pos: int, stream: Sequence[T]) -> Result[V_co]:
            r1 = self(pos, stream)
            if r1.pos != pos:
                return r1
            r2 = other(pos, stream)
            if r2.pos != pos:
                return r2
            return Result(
                r1.pos,
                r2.value if r1.value is ERROR else r1.value,
                chain(r1.expected, r2.expected)
            )

        return FnParser(or_)

    def maybe(self) -> "Parser[T, Optional[V_co]]":
        return maybe(self)

    def many(self) -> "Parser[T, List[V_co]]":
        return many(self)

    def label(self, expected: str) -> "Parser[T, V_co]":
        return label(self, expected)

    def sep_by(self, sep: "Parser[T, U]") -> "Parser[T, List[V_co]]":
        return sep_by(self, sep)


class FnParser(Parser[T, V_co]):
    def __init__(self, fn: Callable[[int, Sequence[T]], Result[V_co]]):
        self._fn = fn

    def __call__(self, pos: int, stream: Sequence[T]) -> Result[V_co]:
        return self._fn(pos, stream)


class Pure(Parser[T, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def __call__(self, pos: int, stream: Sequence[T]) -> Result[V_co]:
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


def sym(s: T) -> Parser[T, T]:
    def sym(pos: int, stream: Sequence[T]) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Result(pos + 1, t)
        return Result(pos, ERROR, [repr(s)])

    return FnParser(sym)


def maybe(parser: Parser[T, V_co]) -> Parser[T, Optional[V_co]]:
    def maybe(pos: int, stream: Sequence[T]) -> Result[Optional[V_co]]:
        r1 = parser(pos, stream)
        if r1.pos != pos:
            return r1
        if r1.value is ERROR:
            return Result(pos, None, r1.expected)
        return Result(pos, r1.value, r1.expected)

    return FnParser(maybe)


def many(parser: Parser[T, V_co]) -> Parser[T, List[V_co]]:
    def many(pos: int, stream: Sequence[T]) -> Result[List[V_co]]:
        value: List[V_co] = []
        r = parser(pos, stream)
        while r.value is not ERROR:
            value.append(r.value)
            pos = r.pos
            r = parser(pos, stream)
        if r.pos != pos:
            return Result(r.pos, ERROR, r.expected)
        return Result(pos, value, r.expected)

    return FnParser(many)


def label(parser: Parser[T, V_co], expected: str) -> Parser[T, V_co]:
    def label(pos: int, stream: Sequence[T]) -> Result[V_co]:
        r = parser(pos, stream)
        if r.pos == pos:
            r.expected = [expected]
        return r

    return FnParser(label)


class Delay(Parser[T, V_co]):
    def __init__(self) -> None:
        def _undefined(pos: int, stream: Sequence[T]) -> Result[V_co]:
            raise RuntimeError("Delayed parser was not defined")

        self._parser: Parser[T, V_co] = FnParser(_undefined)

    def define(self, parser: Parser[T, V_co]) -> None:
        self._parser = parser

    def __call__(self, pos: int, stream: Sequence[T]) -> Result[V_co]:
        return self._parser(pos, stream)


def sep_by(parser: Parser[T, V_co], sep: Parser[T, U]) -> Parser[T, List[V_co]]:
    return maybe(parser + many(sep.rseq(parser))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


letter: Parser[str, str] = satisfy(str.isalpha).label("letter")
digit: Parser[str, str] = satisfy(str.isdigit).label("digit")
