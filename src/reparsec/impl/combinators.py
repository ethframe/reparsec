from typing import Callable, Dict, List, Optional, Tuple, TypeVar

from ..chain import Chain, ChainL
from ..core import (
    ParseFn, ParseObj, RecoveryMode, disallow_recovery, maybe_allow_recovery
)
from ..result import Error, Ok, PrefixItem, Recovered, Repair, Result
from ..state import Ctx

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")
X = TypeVar("X")


ContinueFn = Callable[[V, S, int, Ctx[S]], Result[U, S]]
MergeFn = Callable[[V, U], X]


def continue_parse(
        stream: S, ra: Recovered[V, S], parse: ContinueFn[V, S, U],
        merge: MergeFn[V, U, X]) -> Result[X, S]:
    reps: Dict[int, Repair[X, S]] = {}
    for p, pa in ra.repairs.items():
        rb = parse(pa.value, stream, p, pa.ctx)
        if type(rb) is Ok:
            if rb.pos not in reps or pa.cost < reps[rb.pos].cost:
                reps[rb.pos] = Repair(
                    pa.cost, merge(pa.value, rb.value), rb.ctx, pa.op,
                    pa.expected, pa.consumed, pa.prefix
                )
        elif type(rb) is Recovered:
            for p, pb in rb.repairs.items():
                cost = pa.cost + pb.cost
                if p not in reps or cost < reps[p].cost:
                    reps[p] = Repair(
                        cost, merge(pa.value, pb.value), pb.ctx, pb.op,
                        pb.expected, True,
                        Chain(
                            pa.prefix,
                            ChainL(PrefixItem(pa.op, pa.expected), pb.prefix)
                        )
                    )
    if reps:
        return Recovered(reps, ra.pos, ra.loc, ra.expected)
    return Error(ra.pos, ra.loc, ra.expected, True)


def fmap(parse_fn: ParseFn[S, V], fn: Callable[[V], U]) -> ParseFn[S, U]:
    def fmap(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[U, S]:
        return parse_fn(stream, pos, ctx, rm).fmap(fn)
    return fmap


def alt(parse_fn: ParseFn[S, V], second_fn: ParseFn[S, V]) -> ParseFn[S, V]:
    def alt(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[V, S]:
        ra = parse_fn(stream, pos, ctx, disallow_recovery(rm))
        if ra.consumed is True:
            return ra
        rb = second_fn(stream, pos, ctx, disallow_recovery(rm))
        if rb.consumed is True:
            return rb
        expected = Chain(ra.expected, rb.expected)
        if type(ra) is Ok:
            return ra.expect(expected)
        if type(rb) is Ok:
            return rb.expect(expected)
        if rm:
            rra = parse_fn(stream, pos, ctx, True)
            rrb = second_fn(stream, pos, ctx, True)
            if type(rra) is Recovered:
                if type(rrb) is Recovered:
                    return Recovered(
                        {**rrb.repairs, **rra.repairs}, rra.pos, rra.loc,
                        rra.expected
                    )
                return ra.expect(expected)
            if type(rrb) is Recovered:
                return rrb.expect(expected)
        return Error(pos, ra.loc, expected)

    return alt


def bind(
        parse_fn: ParseFn[S, V],
        fn: Callable[[V], ParseObj[S, U]]) -> ParseFn[S, U]:
    def bind(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[U, S]:
        ra = parse_fn(stream, pos, ctx, rm)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return continue_parse(
                stream, ra, lambda v, s, p, c: fn(v).parse_fn(s, p, c, True),
                lambda _, v: v
            )
        return fn(ra.value).parse_fn(
            stream, ra.pos, ra.ctx, maybe_allow_recovery(rm, ra)
        ).merge_expected(ra.expected, ra.consumed)

    return bind


def _seq(
        parse_fn: ParseFn[S, V], second_fn: ParseFn[S, U],
        merge: MergeFn[V, U, X]) -> ParseFn[S, X]:
    def seq(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[X, S]:
        ra = parse_fn(stream, pos, ctx, rm)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return continue_parse(
                stream, ra, lambda _, s, p, c: second_fn(s, p, c, True), merge
            )
        va = ra.value
        return second_fn(
            stream, ra.pos, ra.ctx, maybe_allow_recovery(rm, ra)
        ).fmap(
            lambda vb: merge(va, vb)
        ).merge_expected(ra.expected, ra.consumed)

    return seq


def lseq(
        parse_fn: ParseFn[S, V],
        second_fn: ParseFn[S, U]) -> ParseFn[S, V]:
    return _seq(parse_fn, second_fn, lambda l, _: l)


def rseq(
        parse_fn: ParseFn[S, V],
        second_fn: ParseFn[S, U]) -> ParseFn[S, U]:
    return _seq(parse_fn, second_fn, lambda _, r: r)


def seq(
        parse_fn: ParseFn[S, V],
        second_fn: ParseFn[S, U]) -> ParseFn[S, Tuple[V, U]]:
    return _seq(parse_fn, second_fn, lambda l, r: (l, r))


def maybe(parse_fn: ParseFn[S, V]) -> ParseFn[S, Optional[V]]:
    def maybe(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[Optional[V], S]:
        r = parse_fn(stream, pos, ctx, disallow_recovery(rm))
        if r.consumed is True or type(r) is Ok:
            return r
        return Ok(None, pos, ctx, r.expected)

    return maybe


def many(parse_fn: ParseFn[S, V]) -> ParseFn[S, List[V]]:
    def many(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[List[V], S]:
        rm = disallow_recovery(rm)
        consumed = False
        value: List[V] = []
        r = parse_fn(stream, pos, ctx, rm)
        while type(r) is Ok:
            consumed |= r.consumed
            value.append(r.value)
            ctx = r.ctx
            r = parse_fn(stream, r.pos, ctx, rm)
        if type(r) is Recovered:
            return continue_parse(
                stream, r, parse, lambda a, b: [*value, a, *b]
            )
        if r.consumed:
            return r
        return Ok(value, r.pos, ctx, r.expected, consumed)

    def parse(_: V, stream: S, pos: int, ctx: Ctx[S]) -> Result[List[V], S]:
        r = many(stream, pos, ctx, True)
        if type(r) is Error and r.consumed is False:
            return Ok[List[V], S]([], pos, ctx, r.expected)
        return r

    return many


def attempt(
        parse_fn: ParseFn[S, V]) -> ParseFn[S, V]:
    def attempt(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[V, S]:
        r = parse_fn(stream, pos, ctx, rm if rm else None)
        if type(r) is Error:
            return Error(r.pos, r.loc, r.expected)
        if type(r) is Recovered:
            return Recovered(
                {
                    p: Repair(
                        r.cost, r.value, r.ctx, r.op, r.expected, False,
                        r.prefix
                    )
                    for p, r in r.repairs.items()
                },
                r.pos, r.loc, r.expected
            )
        return r

    return attempt


def label(parse_fn: ParseFn[S, V], x: str) -> ParseFn[S, V]:
    expected = [x]

    def label(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[V, S]:
        return parse_fn(stream, pos, ctx, rm).expect(expected)

    return label


class Delay(ParseObj[S_contra, V_co]):
    def __init__(self) -> None:
        def _fn(
                stream: S_contra, pos: int, ctx: Ctx[S_contra],
                rm: RecoveryMode) -> Result[V_co, S_contra]:
            raise RuntimeError("Delayed parser was not defined")

        self._defined = False
        self._fn: ParseFn[S_contra, V_co] = _fn

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
