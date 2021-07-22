from abc import abstractmethod
from itertools import chain
from typing import (
    Callable, Generic, Iterable, List, Optional, Tuple, TypeVar, Union
)

from typing_extensions import Protocol

T = TypeVar("T")


class Stream(Protocol[T]):
    def peek(self) -> Optional[T]:
        ...

    def advance(self) -> "Stream[T]":
        ...


V = TypeVar("V")
U = TypeVar("U")


class Ok(Generic[T, V]):
    __slots__ = ("consumed", "value", "stream", "expected")

    def __init__(
            self, consumed: bool, value: V, stream: Stream[T],
            expected: Iterable[str] = ()) -> None:
        self.consumed = consumed
        self.value = value
        self.stream = stream
        self.expected = expected

    def __repr__(self) -> str:
        self.expected = list(self.expected)
        return "<Ok(consumed={!r}, value={!r}, stream={!r}, expected={!r})>".format(
            self.consumed, self.value, self.stream, self.expected
        )

    def fmap(self, fn: Callable[[V], U]) -> "Result[T, U]":
        return Ok(self.consumed, fn(self.value), self.stream, self.expected)


class Error(Generic[T, V]):
    __slots__ = ("consumed", "expected")

    def __init__(self, consumed: bool, expected: Iterable[str] = ()) -> None:
        self.consumed = consumed
        self.expected = expected

    def __repr__(self) -> str:
        self.expected = list(self.expected)
        return "<Error(consumed={!r}, expected={!r})>".format(self.consumed, self.expected)

    def fmap(self, fn: Callable[[V], U]) -> "Result[T, U]":
        return Error(self.consumed, self.expected)


Result = Union[Ok[T, V], Error[T, V]]


class Parser(Protocol[T, V]):
    def __call__(self, stream: Stream[T]) -> Result[T, V]:
        ...

    def fmap(self, fn: Callable[[V], U]) -> "Parser[T, U]":
        ...

    def bind(self, fn: Callable[[V], "Parser[T, U]"]) -> "Parser[T, U]":
        ...

    def __add__(self, other: "Parser[T, U]") -> "Parser[T, Tuple[V, U]]":
        ...

    def __or__(self, other: "Parser[T, V]") -> "Parser[T, V]":
        ...


class _Parser(Generic[T, V]):
    @abstractmethod
    def __call__(self, stream: Stream[T]) -> Result[T, V]:
        ...

    def fmap(self, fn: Callable[[V], U]) -> Parser[T, U]:
        return _FnWrapper(lambda s: self(s).fmap(fn))

    def bind(self, fn: Callable[[V], Parser[T, U]]) -> Parser[T, U]:
        def bind(stream: Stream[T]) -> Result[T, U]:
            r1 = self(stream)
            if isinstance(r1, Error):
                return Error(r1.consumed, r1.expected)
            r2 = fn(r1.value)(r1.stream)
            if r1.consumed:
                r2.consumed = True
            return r2

        return _FnWrapper(bind)

    def __add__(self, other: Parser[T, U]) -> Parser[T, Tuple[V, U]]:
        def add(stream: Stream[T]) -> Result[T, Tuple[V, U]]:
            r1 = self(stream)
            if isinstance(r1, Error):
                return Error(r1.consumed, r1.expected)
            r2 = other(r1.stream)
            if r1.consumed:
                r2.consumed = True
                r2.expected = r1.expected
            else:
                r2.expected = chain(r1.expected, r2.expected)
            v = r1.value
            return r2.fmap(lambda u: (v, u))

        return _FnWrapper(add)  # type: ignore

    def __or__(self, other: Parser[T, V]) -> Parser[T, V]:
        def or_(stream: Stream[T]) -> Result[T, V]:
            r1 = self(stream)
            if r1.consumed:
                return r1
            r2 = other(stream)
            if isinstance(r1, Error) or r2.consumed:
                r2.expected = chain(r1.expected, r2.expected)
                return r2
            r1.expected = chain(r1.expected, r2.expected)
            return r1

        return _FnWrapper(or_)


class _FnWrapper(_Parser[T, V]):
    __slots__ = ("_fn",)

    def __init__(self, fn: Callable[[Stream[T]], Result[T, V]]):
        self._fn = fn

    def __call__(self, stream: Stream[T]) -> Result[T, V]:
        return self._fn(stream)


class Pure(_Parser[T, V]):
    __slots__ = ("_x",)

    def __init__(self, x: V):
        self._x = x

    def __call__(self, stream: Stream[T]) -> Result[T, V]:
        return Ok(False, self._x, stream)


pure = Pure


def satisfy(test: Callable[[T], bool]) -> Parser[T, T]:
    def satisfy(stream: Stream[T]) -> Result[T, T]:
        c = stream.peek()
        if c is None or not test(c):
            return Error(False)
        return Ok(True, c, stream.advance())
    return _FnWrapper(satisfy)


def maybe(parser: Parser[T, V]) -> Parser[T, Optional[V]]:
    def maybe(stream: Stream[T]) -> Result[T, Optional[V]]:
        r = parser(stream)
        if isinstance(r, Ok):
            return Ok(r.consumed, r.value, r.stream)
        return Ok(r.consumed, None, stream)
    return _FnWrapper(maybe)


def many(parser: Parser[T, V]) -> Parser[T, List[V]]:
    def many(stream: Stream[T]) -> Result[T, List[V]]:
        value: List[V] = []
        r = parser(stream)
        consumed = r.consumed
        while isinstance(r, Ok):
            stream = r.stream
            value.append(r.value)
            r = parser(stream)
            if r.consumed:
                consumed = True
        return Ok(consumed, value, stream)
    return _FnWrapper(many)


def label(parser: Parser[T, V], expected: str) -> Parser[T, V]:
    def label(stream: Stream[T]) -> Result[T, V]:
        r = parser(stream)
        if not r.consumed:
            r.expected = [expected]
        return r
    return _FnWrapper(label)


class StringLexer:
    __slots__ = ("_s", "_p")

    def __init__(self, s: str, p: int):
        self._s = s
        self._p = p

    def peek(self) -> Optional[str]:
        if self._p >= len(self._s):
            return None
        return self._s[self._p]

    def advance(self) -> Stream[str]:
        return StringLexer(self._s, self._p + 1)


def char(c: str) -> Parser[str, str]:
    return label(satisfy(lambda v: v == c), repr(c))


letter: Parser[str, str] = label(satisfy(lambda v: v.isalpha()), "letter")
digit: Parser[str, str] = label(satisfy(lambda v: v.isdigit()), "digit")
