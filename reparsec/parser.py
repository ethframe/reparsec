from typing import (
    Callable, List, Optional, Sequence, Sized, Tuple, TypeVar, Union
)

from .core import ParseFnC, ParseObjC, RecoveryMode
from .impl import combinators, layout, primitive, scannerless, sequence
from .impl.layout import Ctx as Ctx
from .impl.layout import GetLevelFn as GetLevelFn
from .impl.scannerless import Pos as Pos
from .output import FmtPos, ParseResult
from .result import Result

T = TypeVar("T")
S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
P = TypeVar("P")
C = TypeVar("C")
V = TypeVar("V", bound=object)
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U", bound=object)
X = TypeVar("X", bound=object)


class ParserC(ParseObjC[S_contra, P, C, V_co]):
    def fmap(self, fn: Callable[[V_co], U]) -> "ParserC[S_contra, P, C, U]":
        return fmap(self, fn)

    def bind(
            self, fn: Callable[[V_co], ParseObjC[S_contra, P, C, U]]
    ) -> "ParserC[S_contra, P, C, U]":
        return bind(self, fn)

    def lseq(
            self, other: ParseObjC[S_contra, P, C, U]
    ) -> "ParserC[S_contra, P, C, V_co]":
        return lseq(self, other)

    def rseq(
            self, other: ParseObjC[S_contra, P, C, U]
    ) -> "ParserC[S_contra, P, C, U]":
        return rseq(self, other)

    def __lshift__(
            self, other: ParseObjC[S_contra, P, C, U]
    ) -> "ParserC[S_contra, P, C, V_co]":
        return lseq(self, other)

    def __rshift__(
            self, other: ParseObjC[S_contra, P, C, U]
    ) -> "ParserC[S_contra, P, C, U]":
        return rseq(self, other)

    def __add__(
            self, other: ParseObjC[S_contra, P, C, U]
    ) -> "ParserC[S_contra, P, C, Tuple[V_co, U]]":
        return seq(self, other)

    def __or__(
            self, other: ParseObjC[S_contra, P, C, V_co]
    ) -> "ParserC[S_contra, P, C, V_co]":
        return alt(self, other)

    def maybe(self) -> "ParserC[S_contra, P, C, Optional[V_co]]":
        return maybe(self)

    def many(
            self: ParseObjC[S_contra, P, C, V_co]
    ) -> "ParserC[S_contra, P, C, List[V_co]]":
        return many(self)

    def attempt(self) -> "ParserC[S_contra, P, C, V_co]":
        return attempt(self)

    def label(self, expected: str) -> "ParserC[S_contra, P, C, V_co]":
        return label(self, expected)

    def sep_by(
            self, sep: ParseObjC[S_contra, P, C, U]
    ) -> "ParserC[S_contra, P, C, List[V_co]]":
        return sep_by(self, sep)

    def between(
            self,
            open: ParseObjC[S_contra, P, C, U],
            close: ParseObjC[S_contra, P, C, X]
    ) -> "ParserC[S_contra, P, C, V_co]":
        return between(open, close, self)


Parser = ParserC[S_contra, P, None, V_co]


class FnParserC(ParserC[S_contra, P, C, V_co]):
    def __init__(self, fn: ParseFnC[S_contra, P, C, V_co]):
        self._fn = fn

    def to_fn(self) -> ParseFnC[S_contra, P, C, V_co]:
        return self._fn

    def parse_fn(
            self, stream: S_contra, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, V_co]:
        return self._fn(stream, pos, ctx, rm)


FnParser = FnParserC[S_contra, P, None, V_co]


def fmap(
        parser: ParseObjC[S, P, C, V],
        fn: Callable[[V], U]) -> ParserC[S, P, C, U]:
    return FnParserC(combinators.fmap(parser.to_fn(), fn))


def bind(
        parser: ParseObjC[S, P, C, V],
        fn: Callable[[V], ParseObjC[S, P, C, U]]) -> ParserC[S, P, C, U]:
    return FnParserC(combinators.bind(parser.to_fn(), fn))


def lseq(
        parser: ParseObjC[S, P, C, V],
        second: ParseObjC[S, P, C, U]) -> ParserC[S, P, C, V]:
    return FnParserC(combinators.lseq(parser.to_fn(), second.to_fn()))


def rseq(
        parser: ParseObjC[S, P, C, V],
        second: ParseObjC[S, P, C, U]) -> ParserC[S, P, C, U]:
    return FnParserC(combinators.rseq(parser.to_fn(), second.to_fn()))


def seq(
        parser: ParseObjC[S, P, C, V],
        second: ParseObjC[S, P, C, U]
) -> ParserC[S, P, C, Tuple[V, U]]:
    return FnParserC(combinators.seq(parser.to_fn(), second.to_fn()))


def alt(
        parser: ParseObjC[S, P, C, V],
        second: ParseObjC[S, P, C, V]) -> ParserC[S, P, C, V]:
    return FnParserC(combinators.alt(parser.to_fn(), second.to_fn()))


class PureC(
        primitive.PureC[S_contra, P, C, V_co], ParserC[S_contra, P, C, V_co]):
    pass


Pure = PureC[S_contra, P, None, V_co]


class PureFnC(
        primitive.PureFnC[S_contra, P, C, V_co],
        ParserC[S_contra, P, C, V_co]):
    pass


PureFn = PureFnC[S_contra, P, None, V_co]


class EofC(sequence.EofC[C], ParserC[Sized, int, C, None]):
    pass


def eof() -> Parser[Sized, int, None]:
    return EofC[None]()


class SatisfyC(sequence.SatisfyC[T, C], ParserC[Sequence[T], int, C, T]):
    pass


def satisfy(test: Callable[[T], bool]) -> Parser[Sequence[T], int, T]:
    return SatisfyC[T, None](test)


class SymC(sequence.SymC[T, C], ParserC[Sequence[T], int, C, T]):
    pass


Sym = SymC[T, None]


def sym(s: T) -> Parser[Sequence[T], int, T]:
    return Sym[T](s)


def maybe(parser: ParseObjC[S, P, C, V]) -> ParserC[S, P, C, Optional[V]]:
    return FnParserC(combinators.maybe(parser.to_fn()))


def many(parser: ParseObjC[S, P, C, V]) -> ParserC[S, P, C, List[V]]:
    return FnParserC(combinators.many(parser.to_fn()))


def attempt(
        parser: ParseObjC[S, P, C, V]) -> ParserC[S, P, C, V]:
    return FnParserC(combinators.attempt(parser.to_fn()))


def label(
        parser: ParseObjC[S, P, C, V],
        x: str) -> ParserC[S, P, C, V]:
    return FnParserC(combinators.label(parser.to_fn(), x))


class InsertValueC(
        primitive.InsertValueC[S_contra, P, C, V_co],
        ParserC[S_contra, P, C, V_co]):
    pass


InsertValue = InsertValueC[S_contra, P, None, V_co]


class InsertFnC(
        primitive.InsertFnC[S_contra, P, C, V_co],
        ParserC[S_contra, P, C, V_co]):
    pass


InsertFn = InsertFnC[S_contra, P, None, V_co]


class DelayC(
        combinators.DelayC[S_contra, P, C, V_co],
        ParserC[S_contra, P, C, V_co]):
    def define(self, parser: ParseObjC[S_contra, P, C, V_co]) -> None:
        self.define_fn(parser.to_fn())


Delay = DelayC[S_contra, P, None, V_co]


class SlEofC(scannerless.EofC[C], ParserC[str, Pos, C, None]):
    pass


def sl_eof() -> Parser[str, Pos, None]:
    return SlEofC()


class PrefixC(scannerless.PrefixC[C], ParserC[str, Pos, C, str]):
    pass


def prefix(s: str) -> Parser[str, Pos, str]:
    return PrefixC(s)


class RegexpC(scannerless.RegexpC[C], ParserC[str, Pos, C, str]):
    pass


def regexp(pat: str, group: Union[int, str] = 0) -> Parser[str, Pos, str]:
    return RegexpC(pat, group)


def sep_by(
        parser: ParseObjC[S, P, C, V],
        sep: ParseObjC[S, P, C, U]) -> ParserC[S, P, C, List[V]]:
    return maybe(seq(parser, many(rseq(sep, parser)))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


def between(
        open: ParseObjC[S, P, C, U], close: ParseObjC[S, P, C, X],
        parser: ParseObjC[S, P, C, V]) -> ParserC[S, P, C, V]:
    return rseq(open, lseq(parser, close))


def block(
        parser: ParseObjC[S, P, Ctx, V],
        fn: GetLevelFn[S, P]) -> ParserC[S, P, Ctx, V]:
    return FnParserC(layout.block(parser.to_fn(), fn))


def same(
        parser: ParseObjC[S, P, Ctx, V],
        fn: GetLevelFn[S, P]) -> ParserC[S, P, Ctx, V]:
    return FnParserC(layout.same(parser.to_fn(), fn))


def indented(
        delta: int, parser: ParseObjC[S, P, Ctx, V],
        fn: GetLevelFn[S, P]) -> ParserC[S, P, Ctx, V]:
    return FnParserC(layout.indented(delta, parser.to_fn(), fn))


letter: Parser[Sequence[str], int, str] = satisfy(str.isalpha).label("letter")
digit: Parser[Sequence[str], int, str] = satisfy(str.isdigit).label("digit")


def _run_parser(
        parser: ParserC[S, P, C, V], stream: S, pos: P, ctx: C,
        recover: bool, fmt_pos: FmtPos[P]) -> ParseResult[P, C, V]:
    return ParseResult(
        parser.parse_fn(stream, pos, ctx, True if recover else None), fmt_pos
    )


def run_c(
        parser: ParserC[S, int, C, V], stream: S, ctx: C,
        recover: bool = False) -> ParseResult[int, C, V]:
    return _run_parser(parser, stream, 0, ctx, recover, repr)


def run(
        parser: Parser[S, int, V], stream: S,
        recover: bool = False) -> ParseResult[int, None, V]:
    return run_c(parser, stream, None, recover)


def sl_run_c(
        parser: ParserC[str, Pos, C, V], stream: str, ctx: C,
        recover: bool = False) -> ParseResult[Pos, C, V]:
    return _run_parser(
        parser, stream, scannerless.start(), ctx, recover,
        lambda p: "{!r}:{!r}".format(p[1] + 1, p[2] + 1)
    )


def sl_run(
        parser: Parser[str, Pos, V], stream: str,
        recover: bool = False) -> ParseResult[Pos, None, V]:
    return sl_run_c(parser, stream, None, recover)
