from typing import Callable, List, Optional, Sequence, Tuple, TypeVar

from . import core
from .core import ParseFn, ParseObj, RecoveryMode
from .result import Result

T = TypeVar("T", bound=object)
V = TypeVar("V", bound=object)
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U", bound=object)
X = TypeVar("X", bound=object)


class Parser(ParseObj[T, V_co]):
    def parse(
            self, stream: Sequence[T], recover: bool = False) -> Result[V_co]:
        return self.parse_fn(stream, 0, True if recover else None)

    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[T, U]":
        return FnParser(core.fmap(self.to_fn(), fn))

    def bind(self, fn: Callable[[V_co], ParseObj[T, U]]) -> "Parser[T, U]":
        return bind(self, fn)

    def lseq(self, other: ParseObj[T, U]) -> "Parser[T, V_co]":
        return lseq(self, other)

    def rseq(self, other: ParseObj[T, U]) -> "Parser[T, U]":
        return rseq(self, other)

    def __lshift__(self, other: ParseObj[T, U]) -> "Parser[T, V_co]":
        return lseq(self, other)

    def __rshift__(self, other: ParseObj[T, U]) -> "Parser[T, U]":
        return rseq(self, other)

    def __add__(self, other: ParseObj[T, U]) -> "Parser[T, Tuple[V_co, U]]":
        return seq(self, other)

    def __or__(self, other: ParseObj[T, V_co]) -> "Parser[T, V_co]":
        return FnParser(core.or_(self.to_fn(), other.to_fn()))

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
    def __init__(self, fn: ParseFn[T, V_co]):
        self._fn = fn

    def to_fn(self) -> ParseFn[T, V_co]:
        return self._fn

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        return self._fn(stream, pos, rm)


def bind(
        parser: ParseObj[T, V],
        fn: Callable[[V], ParseObj[T, U]]) -> Parser[T, U]:
    return FnParser(core.bind(parser.to_fn(), fn))


def lseq(parser: ParseObj[T, V], second: ParseObj[T, U]) -> Parser[T, V]:
    return FnParser(core.lseq(parser.to_fn(), second.to_fn()))


def rseq(parser: ParseObj[T, V], second: ParseObj[T, U]) -> Parser[T, U]:
    return FnParser(core.rseq(parser.to_fn(), second.to_fn()))


def seq(
        parser: ParseObj[T, V],
        second: ParseObj[T, U]) -> Parser[T, Tuple[V, U]]:
    return FnParser(core.seq(parser.to_fn(), second.to_fn()))


class Pure(core.Pure[T, V_co], Parser[T, V_co]):
    pass


pure = Pure


class PureFn(core.Pure[T, V_co], Parser[T, V_co]):
    pass


pure_fn = PureFn


class Eof(core.Eof[T], Parser[T, None]):
    pass


eof = Eof


def satisfy(test: Callable[[T], bool]) -> Parser[T, T]:
    return FnParser(core.satisfy(test))


def sym(s: T) -> Parser[T, T]:
    return FnParser(core.sym(s))


def maybe(parser: ParseObj[T, V]) -> Parser[T, Optional[V]]:
    return FnParser(core.maybe(parser.to_fn()))


def many(parser: ParseObj[T, V]) -> Parser[T, List[V]]:
    return FnParser(core.many(parser.to_fn()))


def label(parser: ParseObj[T, V], x: str) -> Parser[T, V]:
    return FnParser(core.label(parser.to_fn(), x))


class RecoverValue(core.RecoverValue[T, V_co], Parser[T, V_co]):
    pass


recover_value = RecoverValue


class RecoverFn(core.RecoverFn[T, V_co], Parser[T, V_co]):
    pass


recover_fn = RecoverFn


class Delay(core.Delay[T, V_co], Parser[T, V_co]):
    def define(self, parser: ParseObj[T, V_co]) -> None:
        self.define_fn(parser.to_fn())


def sep_by(parser: ParseObj[T, V], sep: ParseObj[T, U]) -> Parser[T, List[V]]:
    return maybe(seq(parser, many(rseq(sep, parser)))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


def between(
        open: ParseObj[T, U], close: ParseObj[T, X],
        parser: ParseObj[T, V]) -> Parser[T, V]:
    return rseq(open, lseq(parser, close))


letter: Parser[str, str] = satisfy(str.isalpha).label("letter")
digit: Parser[str, str] = satisfy(str.isdigit).label("digit")
