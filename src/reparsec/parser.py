from typing import (
    Callable, List, Optional, Sequence, Sized, Tuple, TypeVar, Union
)

from .core import ParseFn, ParseObj, RecoveryMode
from .impl import combinators, layout, primitive, scannerless, sequence
from .output import ParseResult
from .result import Result
from .state import Ctx, Loc

T = TypeVar("T")
S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V", bound=object)
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U", bound=object)
X = TypeVar("X", bound=object)


class Parser(ParseObj[S_contra, V_co]):
    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[S_contra, U]":
        return fmap(self, fn)

    def bind(
            self, fn: Callable[[V_co], ParseObj[S_contra, U]]
    ) -> "Parser[S_contra, U]":
        return bind(self, fn)

    def lseq(self, other: ParseObj[S_contra, U]) -> "Parser[S_contra, V_co]":
        return lseq(self, other)

    def rseq(self, other: ParseObj[S_contra, U]) -> "Parser[S_contra, U]":
        return rseq(self, other)

    def __lshift__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, V_co]":
        return lseq(self, other)

    def __rshift__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, U]":
        return rseq(self, other)

    def __add__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, Tuple[V_co, U]]":
        return seq(self, other)

    def __or__(
            self, other: ParseObj[S_contra, V_co]
    ) -> "Parser[S_contra, V_co]":
        return alt(self, other)

    def maybe(self) -> "Parser[S_contra, Optional[V_co]]":
        return maybe(self)

    def many(
            self: ParseObj[S_contra, V_co]
    ) -> "Parser[S_contra, List[V_co]]":
        return many(self)

    def attempt(self) -> "Parser[S_contra, V_co]":
        return attempt(self)

    def label(self, expected: str) -> "Parser[S_contra, V_co]":
        return label(self, expected)

    def sep_by(
            self, sep: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, List[V_co]]":
        return sep_by(self, sep)

    def between(
            self,
            open: ParseObj[S_contra, U],
            close: ParseObj[S_contra, X]
    ) -> "Parser[S_contra, V_co]":
        return between(open, close, self)


class FnParser(Parser[S_contra, V_co]):
    def __init__(self, fn: ParseFn[S_contra, V_co]):
        self._fn = fn

    def to_fn(self) -> ParseFn[S_contra, V_co]:
        return self._fn

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        return self._fn(stream, pos, ctx, rm)


def fmap(parser: ParseObj[S, V], fn: Callable[[V], U]) -> Parser[S, U]:
    return FnParser(combinators.fmap(parser.to_fn(), fn))


def bind(
        parser: ParseObj[S, V],
        fn: Callable[[V], ParseObj[S, U]]) -> Parser[S, U]:
    return FnParser(combinators.bind(parser.to_fn(), fn))


def lseq(parser: ParseObj[S, V], second: ParseObj[S, U]) -> Parser[S, V]:
    return FnParser(combinators.lseq(parser.to_fn(), second.to_fn()))


def rseq(parser: ParseObj[S, V], second: ParseObj[S, U]) -> Parser[S, U]:
    return FnParser(combinators.rseq(parser.to_fn(), second.to_fn()))


def seq(
        parser: ParseObj[S, V],
        second: ParseObj[S, U]) -> Parser[S, Tuple[V, U]]:
    return FnParser(combinators.seq(parser.to_fn(), second.to_fn()))


def alt(parser: ParseObj[S, V], second: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(combinators.alt(parser.to_fn(), second.to_fn()))


class Pure(primitive.Pure[S_contra, V_co], Parser[S_contra, V_co]):
    pass


class PureFn(primitive.PureFn[S_contra, V_co], Parser[S_contra, V_co]):
    pass


def eof() -> Parser[Sized, None]:
    return FnParser(sequence.eof())


def satisfy(test: Callable[[T], bool]) -> Parser[Sequence[T], T]:
    return FnParser(sequence.satisfy(test))


def sym(s: T) -> Parser[Sequence[T], T]:
    return FnParser(sequence.sym(s))


def maybe(parser: ParseObj[S, V]) -> Parser[S, Optional[V]]:
    return FnParser(combinators.maybe(parser.to_fn()))


def many(parser: ParseObj[S, V]) -> Parser[S, List[V]]:
    return FnParser(combinators.many(parser.to_fn()))


def attempt(parser: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(combinators.attempt(parser.to_fn()))


def label(parser: ParseObj[S, V], x: str) -> Parser[S, V]:
    return FnParser(combinators.label(parser.to_fn(), x))


class InsertValue(
        primitive.InsertValue[S_contra, V_co],
        Parser[S_contra, V_co]):
    pass


class InsertFn(primitive.InsertFn[S_contra, V_co], Parser[S_contra, V_co]):
    pass


class Delay(combinators.Delay[S_contra, V_co], Parser[S_contra, V_co]):
    def define(self, parser: ParseObj[S_contra, V_co]) -> None:
        self.define_fn(parser.to_fn())


def prefix(s: str) -> Parser[str, str]:
    return FnParser(scannerless.prefix(s))


def regexp(pat: str, group: Union[int, str] = 0) -> Parser[str, str]:
    return FnParser(scannerless.regexp(pat, group))


def sep_by(parser: ParseObj[S, V], sep: ParseObj[S, U]) -> Parser[S, List[V]]:
    return maybe(seq(parser, many(rseq(sep, parser)))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


def between(
        open: ParseObj[S, U], close: ParseObj[S, X],
        parser: ParseObj[S, V]) -> Parser[S, V]:
    return rseq(open, lseq(parser, close))


def block(parser: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(layout.block(parser.to_fn()))


def same(parser: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(layout.same(parser.to_fn()))


def indented(delta: int, parser: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(layout.indented(delta, parser.to_fn()))


letter: Parser[Sequence[str], str] = satisfy(str.isalpha).label("letter")
digit: Parser[Sequence[str], str] = satisfy(str.isdigit).label("digit")


def _run_parser(
        parser: Parser[S, V], stream: S, ctx: Ctx[S],
        recover: bool, fmt_loc: Callable[[Loc], str]) -> ParseResult[V, S]:
    return ParseResult(
        parser.parse_fn(stream, 0, ctx, True if recover else None), fmt_loc
    )


def run_c(
        parser: Parser[S, V], stream: S, ctx: Ctx[S],
        recover: bool = False) -> ParseResult[V, S]:
    return _run_parser(parser, stream, ctx, recover, lambda loc: repr(loc.pos))


class _PosCtx(Ctx[S_contra]):
    def get_loc(self, stream: S_contra, pos: int) -> Loc:
        return Loc(pos, 0, 0)

    def update_loc(self, stream: S_contra, pos: int) -> Ctx[S_contra]:
        return self

    def set_anchor(self, anchor: int) -> Ctx[S_contra]:
        return self


def run(
        parser: Parser[S, V], stream: S,
        recover: bool = False) -> ParseResult[V, S]:
    return run_c(parser, stream, _PosCtx(0, Loc(0, 0, 0)), recover)


def sl_run(
        parser: Parser[str, V], stream: str,
        recover: bool = False) -> ParseResult[V, str]:
    return _run_parser(
        parser, stream, scannerless.SlCtx(0, Loc(0, 0, 0)), recover,
        lambda l: "{!r}:{!r}".format(l.line + 1, l.col + 1)
    )
