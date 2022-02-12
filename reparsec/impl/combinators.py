from typing import Callable, Dict, List, Optional, Tuple, TypeVar

from ..chain import Chain, ChainL
from ..core import (
    ParseFnC, ParseObjC, RecoveryMode, disallow_recovery, maybe_allow_recovery
)
from ..result import Error, Ok, PrefixItem, Recovered, Repair, Result

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
P = TypeVar("P")
C = TypeVar("C")
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")
X = TypeVar("X")


ContinueFn = Callable[[V, S, P, C], Result[P, C, U]]
MergeFn = Callable[[V, U], X]


def continue_parse(
        stream: S, ra: Recovered[P, C, V],
        parse: ContinueFn[V, S, P, C, U],
        merge: MergeFn[V, U, X]) -> Result[P, C, X]:
    reps: Dict[P, Repair[P, C, X]] = {}
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
        return Recovered(reps, ra.pos, ra.expected)
    return Error(ra.pos, ra.expected, True)


def fmap(
        parse_fn: ParseFnC[S, P, C, V],
        fn: Callable[[V], U]) -> ParseFnC[S, P, C, U]:
    def fmap(stream: S, pos: P, ctx: C, rm: RecoveryMode) -> Result[P, C, U]:
        return parse_fn(stream, pos, ctx, rm).fmap(fn)
    return fmap


def alt(
        parse_fn: ParseFnC[S, P, C, V],
        second_fn: ParseFnC[S, P, C, V]) -> ParseFnC[S, P, C, V]:
    def alt(stream: S, pos: P, ctx: C, rm: RecoveryMode) -> Result[P, C, V]:
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
            ra = parse_fn(stream, pos, ctx, True)
            rb = second_fn(stream, pos, ctx, True)
            if type(ra) is Recovered:
                if type(rb) is Recovered:
                    return Recovered(
                        {**rb.repairs, **ra.repairs}, ra.pos, ra.expected
                    )
                return ra.expect(expected)
            if type(rb) is Recovered:
                return rb.expect(expected)
        return Error(pos, expected)

    return alt


def bind(
        parse_fn: ParseFnC[S, P, C, V],
        fn: Callable[[V], ParseObjC[S, P, C, U]]) -> ParseFnC[S, P, C, U]:
    def bind(stream: S, pos: P, ctx: C, rm: RecoveryMode) -> Result[P, C, U]:
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
        parse_fn: ParseFnC[S, P, C, V], second_fn: ParseFnC[S, P, C, U],
        merge: MergeFn[V, U, X]) -> ParseFnC[S, P, C, X]:
    def seq(stream: S, pos: P, ctx: C, rm: RecoveryMode) -> Result[P, C, X]:
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
        parse_fn: ParseFnC[S, P, C, V],
        second_fn: ParseFnC[S, P, C, U]) -> ParseFnC[S, P, C, V]:
    return _seq(parse_fn, second_fn, lambda l, _: l)


def rseq(
        parse_fn: ParseFnC[S, P, C, V],
        second_fn: ParseFnC[S, P, C, U]) -> ParseFnC[S, P, C, U]:
    return _seq(parse_fn, second_fn, lambda _, r: r)


def seq(
        parse_fn: ParseFnC[S, P, C, V],
        second_fn: ParseFnC[S, P, C, U]) -> ParseFnC[S, P, C, Tuple[V, U]]:
    return _seq(parse_fn, second_fn, lambda l, r: (l, r))


def maybe(parse_fn: ParseFnC[S, P, C, V]) -> ParseFnC[S, P, C, Optional[V]]:
    def maybe(
            stream: S, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, Optional[V]]:
        r = parse_fn(stream, pos, ctx, disallow_recovery(rm))
        if r.consumed is True or type(r) is Ok:
            return r
        return Ok(None, pos, ctx, r.expected)

    return maybe


def many(parse_fn: ParseFnC[S, P, C, V]) -> ParseFnC[S, P, C, List[V]]:
    def many(
            stream: S, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, List[V]]:
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

    def parse(_: V, stream: S, pos: P, ctx: C) -> Result[P, C, List[V]]:
        r = many(stream, pos, ctx, True)
        if type(r) is Error and r.consumed is False:
            return Ok[P, C, List[V]]([], pos, ctx, r.expected)
        return r

    return many


def attempt(
        parse_fn: ParseFnC[S, P, C, V]) -> ParseFnC[S, P, C, V]:
    def attempt(
            stream: S, pos: P, ctx: C, rm: RecoveryMode) -> Result[P, C, V]:
        r = parse_fn(stream, pos, ctx, rm if rm else None)
        if type(r) is Error:
            return Error(r.pos, r.expected)
        if type(r) is Recovered:
            return Recovered(
                {
                    p: Repair(
                        r.cost, r.value, r.ctx, r.op, r.expected, False,
                        r.prefix
                    )
                    for p, r in r.repairs.items()
                },
                r.pos, r.expected
            )
        return r

    return attempt


def label(parse_fn: ParseFnC[S, P, C, V], x: str) -> ParseFnC[S, P, C, V]:
    expected = [x]

    def label(
            stream: S, pos: P, ctx: C, rm: RecoveryMode) -> Result[P, C, V]:
        return parse_fn(stream, pos, ctx, rm).expect(expected)

    return label


class DelayC(ParseObjC[S_contra, P, C, V_co]):
    def __init__(self) -> None:
        def _fn(
                stream: S_contra, pos: P, ctx: C,
                rm: RecoveryMode) -> Result[P, C, V_co]:
            raise RuntimeError("Delayed parser was not defined")

        self._defined = False
        self._fn: ParseFnC[S_contra, P, C, V_co] = _fn

    def define_fn(self, parse_fn: ParseFnC[S_contra, P, C, V_co]) -> None:
        if self._defined:
            raise RuntimeError("Delayed parser was already defined")
        self._defined = True
        self._fn = parse_fn

    def parse_fn(
            self, stream: S_contra, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, V_co]:
        return self._fn(stream, pos, ctx, rm)

    def to_fn(self) -> ParseFnC[S_contra, P, C, V_co]:
        if self._defined:
            return self._fn
        return super().to_fn()


Delay = DelayC[S_contra, P, None, V_co]
