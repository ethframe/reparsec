from typing import Callable, List, Optional, Tuple, TypeVar

from .core import combinators
from .core.result import Result
from .core.state import Ctx, Loc
from .core.types import ParseFn, ParseObj, RecoveryMode
from .output import ParseResult

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

    def many(self) -> "Parser[S_contra, List[V_co]]":
        return many(self)

    def attempt(self) -> "Parser[S_contra, V_co]":
        return attempt(self)

    def label(self, expected: str) -> "Parser[S_contra, V_co]":
        return label(self, expected)

    def insert_on_error(
            self, insert_fn: Callable[[S_contra, int], V_co], label: str
    ) -> "Parser[S_contra, V_co]":
        return insert_on_error(insert_fn, label, self)

    def sep_by(
            self,
            sep: ParseObj[S_contra, U]) -> "Parser[S_contra, List[V_co]]":
        return sep_by(self, sep)

    def between(
            self, open: ParseObj[S_contra, U],
            close: ParseObj[S_contra, X]) -> "Parser[S_contra, V_co]":
        return between(open, close, self)

    def chainl1(
            self, op: ParseObj[S_contra, Callable[[V_co, V_co], V_co]]
    ) -> "Parser[S_contra, V_co]":
        return chainl1(self, op)

    def chainr1(
            self, op: ParseObj[S_contra, Callable[[V_co, V_co], V_co]]
    ) -> "Parser[S_contra, V_co]":
        return chainr1(self, op)


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


def maybe(parser: ParseObj[S, V]) -> Parser[S, Optional[V]]:
    return FnParser(combinators.maybe(parser.to_fn()))


def many(parser: ParseObj[S, V]) -> Parser[S, List[V]]:
    return FnParser(combinators.many(parser.to_fn()))


def attempt(parser: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(combinators.attempt(parser.to_fn()))


def label(parser: ParseObj[S, V], x: str) -> Parser[S, V]:
    return FnParser(combinators.label(parser.to_fn(), x))


def insert_on_error(
        insert_fn: Callable[[S, int], V], label: str,
        parser: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(
        combinators.insert_on_error(insert_fn, label, parser.to_fn())
    )


class Delay(Parser[S_contra, V_co]):
    def __init__(self) -> None:
        def _fn(
                stream: S_contra, pos: int, ctx: Ctx[S_contra],
                rm: RecoveryMode) -> Result[V_co, S_contra]:
            raise RuntimeError("Delayed parser was not defined")

        self._defined = False
        self._fn: ParseFn[S_contra, V_co] = _fn

    def define(self, parser: ParseObj[S_contra, V_co]) -> None:
        self.define_fn(parser.to_fn())

    def define_fn(self, parse_fn: ParseFn[S_contra, V_co]) -> None:
        if self._defined:
            raise RuntimeError("Delayed parser was already defined")
        self._defined = True
        self._fn = parse_fn

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        return self._fn(stream, pos, ctx, rm)

    def to_fn(self) -> ParseFn[S_contra, V_co]:
        if self._defined:
            return self._fn
        return super().to_fn()


def sep_by(parser: ParseObj[S, V], sep: ParseObj[S, U]) -> Parser[S, List[V]]:
    return maybe(seq(parser, many(rseq(sep, parser)))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


def between(
        open: ParseObj[S, U], close: ParseObj[S, X],
        parser: ParseObj[S, V]) -> Parser[S, V]:
    return rseq(open, lseq(parser, close))


def chainl1(
        arg: ParseObj[S, V],
        op: ParseObj[S, Callable[[V, V], V]]) -> Parser[S, V]:
    def reducer(v: Tuple[V, List[Tuple[Callable[[V, V], V], V]]]) -> V:
        res, tail = v
        for op, arg in tail:
            res = op(res, arg)
        return res

    return fmap(seq(arg, many(seq(op, arg))), reducer)


def chainr1(
        arg: ParseObj[S, V],
        op: ParseObj[S, Callable[[V, V], V]]) -> Parser[S, V]:
    def reducer(v: Tuple[V, List[Tuple[Callable[[V, V], V], V]]]) -> V:
        res, tail = v
        rassoc: List[Tuple[V, Callable[[V, V], V]]] = []
        for op, arg in tail:
            rassoc.append((res, op))
            res = arg
        for arg, op in reversed(rassoc):
            res = op(arg, res)
        return res

    return fmap(seq(arg, many(seq(op, arg))), reducer)


def run_c(
        parser: Parser[S, V], stream: S,
        get_loc: Callable[[Loc, S, int], Loc], fmt_loc: Callable[[Loc], str],
        recover: bool = False) -> ParseResult[V, S]:
    return ParseResult(
        parser.parse_fn(
            stream, 0, Ctx(0, Loc(0, 0, 0), get_loc), True if recover else None
        ),
        fmt_loc
    )


def run(
        parser: Parser[S, V], stream: S,
        recover: bool = False) -> ParseResult[V, S]:
    return run_c(
        parser, stream, lambda _, __, p: Loc(p, 0, 0), lambda l: repr(l.pos),
        recover
    )
