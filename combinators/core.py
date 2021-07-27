from abc import abstractmethod
from itertools import chain
from typing import (
    Callable, Generic, Iterable, List, NoReturn, Optional, Sequence, Tuple,
    TypeVar, Union
)

T = TypeVar("T")
V = TypeVar("V", bound=object)
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U", bound=object)
X = TypeVar("X", bound=object)


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


class Ok(Generic[V_co]):
    def __init__(
            self, value: V_co, pos: int,
            expected: Iterable[str] = ()) -> None:
        self.value = value
        self.pos = pos
        self.expected = expected

    def unwrap(self) -> V_co:
        return self.value


class Error:
    def __init__(self, pos: int, expected: Iterable[str] = ()) -> None:
        self.pos = pos
        self.expected = expected

    def unwrap(self) -> NoReturn:
        raise ParseError(self.pos, list(self.expected))


Result = Union[Ok[V], Error]


def merge_expected(pos: int, ra: Result[V], rb: Result[U]) -> Iterable[str]:
    if ra.pos != pos and ra.pos != rb.pos:
        return rb.expected
    return chain(ra.expected, rb.expected)


class Parser(Generic[T, V_co]):
    def parse(self, stream: Sequence[T]) -> Result[V_co]:
        return self(stream, 0)

    @abstractmethod
    def __call__(self, stream: Sequence[T], pos: int) -> Result[V_co]:
        ...

    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[T, U]":
        def fmap(stream: Sequence[T], pos: int) -> Result[U]:
            r = self(stream, pos)
            if isinstance(r, Error):
                return r
            return Ok(fn(r.value), r.pos, r.expected)

        return FnParser(fmap)

    def bind(self, fn: Callable[[V_co], "Parser[T, U]"]) -> "Parser[T, U]":
        def bind(stream: Sequence[T], pos: int) -> Result[U]:
            ra = self(stream, pos)
            if isinstance(ra, Error):
                return ra
            rb = fn(ra.value)(stream, ra.pos)
            expected = merge_expected(pos, ra, rb)
            if isinstance(rb, Error):
                return Error(rb.pos, expected)
            return Ok(rb.value, rb.pos, expected)

        return FnParser(bind)

    def lseq(self, other: "Parser[T, U]") -> "Parser[T, V_co]":
        def lseq(stream: Sequence[T], pos: int) -> Result[V_co]:
            ra = self(stream, pos)
            if isinstance(ra, Error):
                return ra
            rb = other(stream, ra.pos)
            expected = merge_expected(pos, ra, rb)
            if isinstance(rb, Error):
                return Error(rb.pos, expected)
            return Ok(ra.value, rb.pos, expected)

        return FnParser(lseq)

    def rseq(self, other: "Parser[T, U]") -> "Parser[T, U]":
        def rseq(stream: Sequence[T], pos: int) -> Result[U]:
            ra = self(stream, pos)
            if isinstance(ra, Error):
                return Error(ra.pos, ra.expected)
            rb = other(stream, ra.pos)
            expected = merge_expected(pos, ra, rb)
            if isinstance(rb, Error):
                return Error(rb.pos, expected)
            return Ok(rb.value, rb.pos, expected)

        return FnParser(rseq)

    def __add__(self, other: "Parser[T, U]") -> "Parser[T, Tuple[V_co, U]]":
        def add(stream: Sequence[T], pos: int) -> Result[Tuple[V_co, U]]:
            ra = self(stream, pos)
            if isinstance(ra, Error):
                return ra
            rb = other(stream, ra.pos)
            expected = merge_expected(pos, ra, rb)
            if isinstance(rb, Error):
                return Error(rb.pos, expected)
            return Ok((ra.value, rb.value), rb.pos, expected)

        return FnParser(add)

    def __or__(self, other: "Parser[T, V_co]") -> "Parser[T, V_co]":
        def or_(stream: Sequence[T], pos: int) -> Result[V_co]:
            ra = self(stream, pos)
            if ra.pos != pos:
                return ra
            rb = other(stream, pos)
            if rb.pos != pos:
                return rb
            expected = chain(ra.expected, rb.expected)
            if isinstance(ra, Ok):
                return Ok(ra.value, pos, expected)
            if isinstance(rb, Ok):
                return Ok(rb.value, pos, expected)
            return Error(pos, expected)

        return FnParser(or_)

    def maybe(self) -> "Parser[T, Optional[V_co]]":
        return maybe(self)

    def many(self) -> "Parser[T, List[V_co]]":
        return many(self)

    def label(self, expected: str) -> "Parser[T, V_co]":
        return label(self, expected)

    def sep_by(self, sep: "Parser[T, U]") -> "Parser[T, List[V_co]]":
        return sep_by(self, sep)

    def between(
            self, open: "Parser[T, U]",
            close: "Parser[T, X]") -> "Parser[T, V_co]":
        return between(open, close, self)


class FnParser(Parser[T, V_co]):
    def __init__(self, fn: Callable[[Sequence[T], int], Result[V_co]]):
        self._fn = fn

    def __call__(self, stream: Sequence[T], pos: int) -> Result[V_co]:
        return self._fn(stream, pos)


class Pure(Parser[T, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def __call__(self, stream: Sequence[T], pos: int) -> Result[V_co]:
        return Ok(self._x, pos)


pure = Pure


class Eof(Parser[T, None]):
    def __call__(self, stream: Sequence[T], pos: int) -> Result[None]:
        if pos == len(stream):
            return Ok(None, pos)
        return Error(pos, ["end of file"])


eof = Eof


def satisfy(test: Callable[[T], bool]) -> Parser[T, T]:
    def satisfy(stream: Sequence[T], pos: int) -> Result[T]:
        if pos < len(stream):
            tok = stream[pos]
            if test(tok):
                return Ok(tok, pos + 1)
        return Error(pos)

    return FnParser(satisfy)


def sym(s: T) -> Parser[T, T]:
    def sym(stream: Sequence[T], pos: int) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Ok(t, pos + 1)
        return Error(pos, [repr(s)])

    return FnParser(sym)


def maybe(parser: Parser[T, V]) -> Parser[T, Optional[V]]:
    def maybe(stream: Sequence[T], pos: int) -> Result[Optional[V]]:
        r = parser(stream, pos)
        if r.pos != pos:
            return r
        if isinstance(r, Error):
            return Ok(None, pos, r.expected)
        return r

    return FnParser(maybe)


def many(parser: Parser[T, V]) -> Parser[T, List[V]]:
    def many(stream: Sequence[T], pos: int) -> Result[List[V]]:
        value: List[V] = []
        r = parser(stream, pos)
        while not isinstance(r, Error):
            value.append(r.value)
            pos = r.pos
            r = parser(stream, pos)
        if r.pos != pos:
            return r
        return Ok(value, pos, r.expected)

    return FnParser(many)


def label(parser: Parser[T, V], expected: str) -> Parser[T, V]:
    def label(stream: Sequence[T], pos: int) -> Result[V]:
        r = parser(stream, pos)
        if r.pos != pos:
            return r
        if isinstance(r, Error):
            return Error(pos, [expected])
        return Ok(r.value, pos, [expected])

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


def sep_by(parser: Parser[T, V], sep: Parser[T, U]) -> Parser[T, List[V]]:
    return maybe(parser + many(sep.rseq(parser))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


def between(
        open: Parser[T, U], close: Parser[T, X],
        parser: Parser[T, V]) -> Parser[T, V]:
    return open.rseq(parser).lseq(close)


letter: Parser[str, str] = satisfy(str.isalpha).label("letter")
digit: Parser[str, str] = satisfy(str.isdigit).label("digit")
