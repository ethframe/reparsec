from typing import Callable, List, Optional, Tuple, TypeVar, Union

from .core import combinators
from .core.result import BaseRepair, Error, Ok, Result
from .core.state import Ctx, Loc
from .core.types import ParseFn, ParseObj, RecoveryMode
from .output import ErrorItem, ParseError, ParseResult

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")
X = TypeVar("X")


def _get_loc(loc: Loc, stream: S, pos: int) -> Loc:
    return Loc(pos, 0, 0)


def _fmt_loc(loc: Loc) -> str:
    return repr(loc.pos)


class Parser(ParseObj[S_contra, V_co]):
    def parse(
            self, stream: S_contra, recover: bool = False, *,
            get_loc: Callable[[Loc, S_contra, int], Loc] = _get_loc,
            fmt_loc: Callable[[Loc], str] = _fmt_loc
    ) -> ParseResult[V_co, S_contra]:
        ctx = Ctx(0, Loc(0, 0, 0), get_loc)
        result = self.parse_fn(stream, 0, ctx, True if recover else None)
        return _ParseResult(result, fmt_loc)

    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[S_contra, U]":
        return fmap(self, fn)

    def bind(
            self, fn: Callable[[V_co], ParseObj[S_contra, U]]
    ) -> "Parser[S_contra, U]":
        return bind(self, fn)

    def seql(self, other: ParseObj[S_contra, U]) -> "Parser[S_contra, V_co]":
        return seql(self, other)

    def seqr(self, other: ParseObj[S_contra, U]) -> "Parser[S_contra, U]":
        return seqr(self, other)

    def __lshift__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, V_co]":
        return seql(self, other)

    def __rshift__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, U]":
        return seqr(self, other)

    def __add__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, Tuple[V_co, U]]":
        return seq(self, other)

    def __or__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, Union[V_co, U]]":
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
            self, insert_fn: Callable[[S_contra, int], V_co],
            label: Optional[str] = None) -> "Parser[S_contra, V_co]":
        return insert_on_error(self, insert_fn, label)

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


def seq(
        parser: ParseObj[S, V],
        second: ParseObj[S, U]) -> Parser[S, Tuple[V, U]]:
    return FnParser(combinators.seq(parser.to_fn(), second.to_fn()))


def seql(parser: ParseObj[S, V], second: ParseObj[S, U]) -> Parser[S, V]:
    return FnParser(combinators.seql(parser.to_fn(), second.to_fn()))


def seqr(parser: ParseObj[S, V], second: ParseObj[S, U]) -> Parser[S, U]:
    return FnParser(combinators.seqr(parser.to_fn(), second.to_fn()))


def alt(
        parser: ParseObj[S, V],
        second: ParseObj[S, U]) -> Parser[S, Union[V, U]]:
    return FnParser(combinators.alt(parser.to_fn(), second.to_fn()))


def maybe(parser: ParseObj[S, V]) -> Parser[S, Optional[V]]:
    return FnParser(combinators.maybe(parser.to_fn()))


def many(parser: ParseObj[S, V]) -> Parser[S, List[V]]:
    return FnParser(combinators.many(parser.to_fn()))


def attempt(parser: ParseObj[S, V]) -> Parser[S, V]:
    return FnParser(combinators.attempt(parser.to_fn()))


def label(parser: ParseObj[S, V], expected: str) -> Parser[S, V]:
    return FnParser(combinators.label(parser.to_fn(), expected))


def insert_on_error(
        parser: ParseObj[S, V], insert_fn: Callable[[S, int], V],
        label: Optional[str] = None) -> Parser[S, V]:
    return FnParser(
        combinators.insert_on_error(parser.to_fn(), insert_fn, label)
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
        if self._defined:
            raise RuntimeError("Delayed parser was already defined")
        self._defined = True
        self._fn = parser.to_fn()

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        return self._fn(stream, pos, ctx, rm)

    def to_fn(self) -> ParseFn[S_contra, V_co]:
        if self._defined:
            return self._fn
        return super().to_fn()


def sep_by(parser: ParseObj[S, V], sep: ParseObj[S, U]) -> Parser[S, List[V]]:
    return maybe(seq(parser, many(seqr(sep, parser)))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


def between(
        open: ParseObj[S, U], close: ParseObj[S, X],
        parser: ParseObj[S, V]) -> Parser[S, V]:
    return seqr(open, seql(parser, close))


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


class _ParseResult(ParseResult[V_co, S]):
    def __init__(self, result: Result[V_co, S], fmt_loc: Callable[[Loc], str]):
        self._result = result
        self._fmt_loc = fmt_loc

    def fmap(self, fn: Callable[[V_co], U]) -> ParseResult[U, S]:
        return _ParseResult(self._result.fmap(fn), self._fmt_loc)

    def unwrap(self, recover: bool = False) -> V_co:
        if type(self._result) is Ok:
            return self._result.value

        if type(self._result) is Error:
            raise ParseError([
                ErrorItem(
                    self._result.loc,
                    self._fmt_loc(self._result.loc),
                    list(self._result.expected),
                )
            ])

        repair: Optional[BaseRepair[V_co, S]] = self._result.selected
        if repair is None:
            repair = self._result.pending
            if repair is None:
                raise ParseError([
                    ErrorItem(
                        self._result.loc,
                        self._fmt_loc(self._result.loc),
                        list(self._result.expected)
                    )
                ])
        if recover:
            return repair.value
        errors: List[ErrorItem] = [
            ErrorItem(
                self._result.loc, self._fmt_loc(self._result.loc),
                list(self._result.expected), repair.op
            )
        ]
        for item in repair.ops:
            errors.append(
                ErrorItem(
                    item.loc, self._fmt_loc(item.loc), list(item.expected),
                    item.op
                )
            )
        raise ParseError(errors)
