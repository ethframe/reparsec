from typing import (
    AnyStr, Callable, List, Optional, Sequence, Sized, Tuple, TypeVar, Union
)

from .core import ParseFn, ParseObj, RecoveryMode
from .impl import combinators, primitive, scannerless, sequence
from .result import Result

T = TypeVar("T")
S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
P = TypeVar("P")
V = TypeVar("V", bound=object)
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U", bound=object)
X = TypeVar("X", bound=object)


class Parser(ParseObj[S_contra, P, V_co]):
    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[S_contra, P, U]":
        return FnParser(combinators.fmap(self.to_fn(), fn))

    def bind(
            self, fn: Callable[[V_co], ParseObj[S_contra, P, U]]
    ) -> "Parser[S_contra, P, U]":
        return bind(self, fn)

    def lseq(
            self,
            other: ParseObj[S_contra, P, U]) -> "Parser[S_contra, P, V_co]":
        return lseq(self, other)

    def rseq(
            self,
            other: ParseObj[S_contra, P, U]) -> "Parser[S_contra, P, U]":
        return rseq(self, other)

    def __lshift__(
            self,
            other: ParseObj[S_contra, P, U]) -> "Parser[S_contra, P, V_co]":
        return lseq(self, other)

    def __rshift__(
            self, other: ParseObj[S_contra, P, U]) -> "Parser[S_contra, P, U]":
        return rseq(self, other)

    def __add__(
            self, other: ParseObj[S_contra, P, U]
    ) -> "Parser[S_contra, P, Tuple[V_co, U]]":
        return seq(self, other)

    def __or__(
            self,
            other: ParseObj[S_contra, P, V_co]) -> "Parser[S_contra, P, V_co]":
        return FnParser(combinators.or_(self.to_fn(), other.to_fn()))

    def maybe(self) -> "Parser[S_contra, P, Optional[V_co]]":
        return maybe(self)

    def many(self) -> "Parser[S_contra, P, List[V_co]]":
        return many(self)

    def attempt(self) -> "Parser[S_contra, P, V_co]":
        return attempt(self)

    def label(self, expected: str) -> "Parser[S_contra, P, V_co]":
        return label(self, expected)

    def sep_by(
            self, sep: "Parser[S_contra, P, U]"
    ) -> "Parser[S_contra, P, List[V_co]]":
        return sep_by(self, sep)

    def between(
            self, open: "Parser[S_contra, P, U]",
            close: "Parser[S_contra, P, X]") -> "Parser[S_contra, P, V_co]":
        return between(open, close, self)


class FnParser(Parser[S_contra, P, V_co]):
    def __init__(self, fn: ParseFn[S_contra, P, V_co]):
        self._fn = fn

    def to_fn(self) -> ParseFn[S_contra, P, V_co]:
        return self._fn

    def parse_fn(
            self, stream: S_contra, pos: P,
            rm: RecoveryMode) -> Result[P, V_co]:
        return self._fn(stream, pos, rm)


def bind(
        parser: ParseObj[S, P, V],
        fn: Callable[[V], ParseObj[S, P, U]]) -> Parser[S, P, U]:
    return FnParser(combinators.bind(parser.to_fn(), fn))


def lseq(
        parser: ParseObj[S, P, V],
        second: ParseObj[S, P, U]) -> Parser[S, P, V]:
    return FnParser(combinators.lseq(parser.to_fn(), second.to_fn()))


def rseq(
        parser: ParseObj[S, P, V],
        second: ParseObj[S, P, U]) -> Parser[S, P, U]:
    return FnParser(combinators.rseq(parser.to_fn(), second.to_fn()))


def seq(
        parser: ParseObj[S, P, V],
        second: ParseObj[S, P, U]) -> Parser[S, P, Tuple[V, U]]:
    return FnParser(combinators.seq(parser.to_fn(), second.to_fn()))


class Pure(primitive.Pure[S_contra, P, V_co], Parser[S_contra, P, V_co]):
    pass


pure = Pure


class PureFn(primitive.PureFn[S_contra, P, V_co], Parser[S_contra, P, V_co]):
    pass


pure_fn = PureFn


def eof() -> Parser[Sized, int, None]:
    return FnParser(sequence.eof())


def satisfy(test: Callable[[T], bool]) -> Parser[Sequence[T], int, T]:
    return FnParser(sequence.satisfy(test))


def sym(s: T) -> Parser[Sequence[T], int, T]:
    return FnParser(sequence.sym(s))


def maybe(parser: ParseObj[S, P, V]) -> Parser[S, P, Optional[V]]:
    return FnParser(combinators.maybe(parser.to_fn()))


def many(parser: ParseObj[S, P, V]) -> Parser[S, P, List[V]]:
    return FnParser(combinators.many(parser.to_fn()))


def attempt(parser: ParseObj[S, P, V]) -> Parser[S, P, V]:
    return FnParser(combinators.attempt(parser.to_fn()))


def label(parser: ParseObj[S, P, V], x: str) -> Parser[S, P, V]:
    return FnParser(combinators.label(parser.to_fn(), x))


class InsertValue(
        primitive.InsertValue[S_contra, P, V_co], Parser[S_contra, P, V_co]):
    pass


insert = InsertValue


class InsertFn(
        primitive.InsertFn[S_contra, P, V_co], Parser[S_contra, P, V_co]):
    pass


insert_fn = InsertFn


class Delay(combinators.Delay[S_contra, P, V_co], Parser[S_contra, P, V_co]):
    def define(self, parser: ParseObj[S_contra, P, V_co]) -> None:
        self.define_fn(parser.to_fn())


def prefix(s: AnyStr) -> Parser[AnyStr, int, AnyStr]:
    return FnParser(scannerless.prefix(s))


def regexp(
        pat: AnyStr,
        group: Union[int, str] = 0) -> Parser[AnyStr, int, AnyStr]:
    return FnParser(scannerless.regexp(pat, group))


def sep_by(
        parser: ParseObj[S, P, V],
        sep: ParseObj[S, P, U]) -> Parser[S, P, List[V]]:
    return maybe(seq(parser, many(rseq(sep, parser)))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


def between(
        open: ParseObj[S, P, U], close: ParseObj[S, P, X],
        parser: ParseObj[S, P, V]) -> Parser[S, P, V]:
    return rseq(open, lseq(parser, close))


letter: Parser[Sequence[str], int, str] = satisfy(str.isalpha).label("letter")
digit: Parser[Sequence[str], int, str] = satisfy(str.isdigit).label("digit")


def run(
        parser: Parser[S, int, V], stream: S,
        recover: bool = False) -> Result[int, V]:
    return parser.parse_fn(stream, 0, True if recover else None)
