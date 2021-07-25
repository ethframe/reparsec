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
V_co = TypeVar("V_co", covariant=True)
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


Value = Union[V_co, _Error]
ERROR: Final = _Error.error


class Result(Generic[V_co]):
    def __init__(
            self, value: Value[V_co], pos: int,
            expected: Iterable[str] = ()) -> None:
        self.value = value
        self.pos = pos
        self.expected = expected

    def unwrap(self) -> V_co:
        if self.value is ERROR:
            raise ParseError(self.pos, list(self.expected))
        return self.value


def merge_expected(pos: int, r1: Result[V], r2: Result[U]) -> Iterable[str]:
    if r1.pos != pos and r1.pos != r2.pos:
        return r2.expected
    return chain(r1.expected, r2.expected)


class Parser(Generic[T, V_co]):
    def parse(self, stream: Sequence[T]) -> Result[V_co]:
        return self(stream, 0)

    @abstractmethod
    def __call__(self, stream: Sequence[T], pos: int) -> Result[V_co]:
        ...

    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[T, U]":
        def fmap(stream: Sequence[T], pos: int) -> Result[U]:
            r = self(stream, pos)
            return Result(
                ERROR if r.value is ERROR else fn(r.value),
                r.pos, r.expected
            )

        return FnParser(fmap)

    def bind(self, fn: Callable[[V_co], "Parser[T, U]"]) -> "Parser[T, U]":
        def bind(stream: Sequence[T], pos: int) -> Result[U]:
            r1 = self(stream, pos)
            if r1.value is ERROR:
                return Result(ERROR, r1.pos, r1.expected)
            r2 = fn(r1.value)(stream, r1.pos)
            expected = merge_expected(pos, r1, r2)
            if r2.value is ERROR:
                return Result(ERROR, r2.pos, expected)
            return Result(r2.value, r2.pos, expected)

        return FnParser(bind)

    def lseq(self, other: "Parser[T, U]") -> "Parser[T, V_co]":
        def lseq(stream: Sequence[T], pos: int) -> Result[V_co]:
            r1 = self(stream, pos)
            if r1.value is ERROR:
                return Result(ERROR, r1.pos, r1.expected)
            r2 = other(stream, r1.pos)
            expected = merge_expected(pos, r1, r2)
            if r2.value is ERROR:
                return Result(ERROR, r2.pos, expected)
            return Result(r1.value, r2.pos, expected)

        return FnParser(lseq)

    def rseq(self, other: "Parser[T, U]") -> "Parser[T, U]":
        def rseq(stream: Sequence[T], pos: int) -> Result[U]:
            r1 = self(stream, pos)
            if r1.value is ERROR:
                return Result(ERROR, r1.pos, r1.expected)
            r2 = other(stream, r1.pos)
            expected = merge_expected(pos, r1, r2)
            if r2.value is ERROR:
                return Result(ERROR, r2.pos, expected)
            return Result(r2.value, r2.pos, expected)

        return FnParser(rseq)

    def __add__(self, other: "Parser[T, U]") -> "Parser[T, Tuple[V_co, U]]":
        def add(stream: Sequence[T], pos: int) -> Result[Tuple[V_co, U]]:
            r1 = self(stream, pos)
            if r1.value is ERROR:
                return Result(ERROR, r1.pos, r1.expected)
            r2 = other(stream, r1.pos)
            expected = merge_expected(pos, r1, r2)
            if r2.value is ERROR:
                return Result(ERROR, r2.pos, expected)
            return Result((r1.value, r2.value), r2.pos, expected)

        return FnParser(add)

    def __or__(self, other: "Parser[T, V_co]") -> "Parser[T, V_co]":
        def or_(stream: Sequence[T], pos: int) -> Result[V_co]:
            r1 = self(stream, pos)
            if r1.pos != pos:
                return r1
            r2 = other(stream, pos)
            if r2.pos != pos:
                return r2
            return Result(
                r2.value if r1.value is ERROR else r1.value,
                pos, chain(r1.expected, r2.expected)
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
    def __init__(self, fn: Callable[[Sequence[T], int], Result[V_co]]):
        self._fn = fn

    def __call__(self, stream: Sequence[T], pos: int) -> Result[V_co]:
        return self._fn(stream, pos)


class Pure(Parser[T, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def __call__(self, stream: Sequence[T], pos: int) -> Result[V_co]:
        return Result(self._x, pos)


pure = Pure


class Eof(Parser[T, None]):
    def __call__(self, stream: Sequence[T], pos: int) -> Result[None]:
        if pos == len(stream):
            return Result(None, pos)
        return Result(ERROR, pos, ["end of file"])


eof = Eof


def satisfy(test: Callable[[T], bool]) -> Parser[T, T]:
    def satisfy(stream: Sequence[T], pos: int) -> Result[T]:
        if pos < len(stream):
            tok = stream[pos]
            if test(tok):
                return Result(tok, pos + 1)
        return Result(ERROR, pos)

    return FnParser(satisfy)


def sym(s: T) -> Parser[T, T]:
    def sym(stream: Sequence[T], pos: int) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Result(t, pos + 1)
        return Result(ERROR, pos, [repr(s)])

    return FnParser(sym)


def maybe(parser: Parser[T, V_co]) -> Parser[T, Optional[V_co]]:
    def maybe(stream: Sequence[T], pos: int) -> Result[Optional[V_co]]:
        r1 = parser(stream, pos)
        if r1.pos != pos:
            return r1
        if r1.value is ERROR:
            return Result(None, pos, r1.expected)
        return Result(r1.value, pos, r1.expected)

    return FnParser(maybe)


def many(parser: Parser[T, V_co]) -> Parser[T, List[V_co]]:
    def many(stream: Sequence[T], pos: int) -> Result[List[V_co]]:
        value: List[V_co] = []
        r = parser(stream, pos)
        while r.value is not ERROR:
            value.append(r.value)
            pos = r.pos
            r = parser(stream, pos)
        if r.pos != pos:
            return Result(ERROR, r.pos, r.expected)
        return Result(value, pos, r.expected)

    return FnParser(many)


def label(parser: Parser[T, V_co], expected: str) -> Parser[T, V_co]:
    def label(stream: Sequence[T], pos: int) -> Result[V_co]:
        r = parser(stream, pos)
        if r.pos != pos:
            return r
        return Result(r.value, r.pos, [expected])

    return FnParser(label)


class Delay(Parser[T, V_co]):
    def __init__(self) -> None:
        def _undefined(stream: Sequence[T], pos: int) -> Result[V_co]:
            raise RuntimeError("Delayed parser was not defined")

        self._parser: Parser[T, V_co] = FnParser(_undefined)

    def define(self, parser: Parser[T, V_co]) -> None:
        self._parser = parser

    def __call__(self, stream: Sequence[T], pos: int) -> Result[V_co]:
        return self._parser(stream, pos)


def sep_by(parser: Parser[T, V_co], sep: Parser[T, U]) -> Parser[T, List[V_co]]:
    return maybe(parser + many(sep.rseq(parser))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


letter: Parser[str, str] = satisfy(str.isalpha).label("letter")
digit: Parser[str, str] = satisfy(str.isdigit).label("digit")
