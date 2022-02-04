from typing import Callable, Dict, List, Optional, Tuple, TypeVar

from ..chain import Chain, ChainL
from ..core import (
    ParseFn, ParseObj, RecoveryMode, disallow_recovery, maybe_allow_recovery
)
from ..result import Error, Ok, PrefixItem, Recovered, Repair, Result

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
P = TypeVar("P")
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")
X = TypeVar("X")


def fmap(parse_fn: ParseFn[S, P, V], fn: Callable[[V], U]) -> ParseFn[S, P, U]:
    def fmap(stream: S, pos: P, rm: RecoveryMode) -> Result[P, U]:
        return parse_fn(stream, pos, rm).fmap(fn)
    return fmap


def or_(
        parse_fn: ParseFn[S, P, V],
        second_fn: ParseFn[S, P, V]) -> ParseFn[S, P, V]:
    def or_(stream: S, pos: P, rm: RecoveryMode) -> Result[P, V]:
        ra = parse_fn(stream, pos, disallow_recovery(rm))
        if ra.consumed is True:
            return ra
        rb = second_fn(stream, pos, disallow_recovery(rm))
        if rb.consumed is True:
            return rb
        expected = Chain(ra.expected, rb.expected)
        if type(ra) is Ok:
            return ra.expect(expected)
        if type(rb) is Ok:
            return rb.expect(expected)
        if rm:
            ra = parse_fn(stream, pos, True)
            rb = second_fn(stream, pos, True)
            if type(ra) is Recovered:
                if type(rb) is Recovered:
                    return Recovered(
                        {**rb.repairs, **ra.repairs}, ra.pos, ra.expected
                    )
                return ra.expect(expected)
            if type(rb) is Recovered:
                return rb.expect(expected)
        return Error(pos, expected)

    return or_


def _continue_parse(
        stream: S, ra: Recovered[P, V],
        parse: Callable[[S, P, Repair[P, V]], Result[P, U]],
        merge: Callable[[V, U], X]) -> Result[P, X]:
    reps: Dict[P, Repair[P, X]] = {}
    for p, pa in ra.repairs.items():
        rb = parse(stream, p, pa)
        if type(rb) is Ok:
            if rb.pos not in reps or pa.cost < reps[rb.pos].cost:
                reps[rb.pos] = Repair(
                    pa.cost, merge(pa.value, rb.value), pa.op, pa.expected,
                    pa.consumed, pa.prefix
                )
        elif type(rb) is Recovered:
            for p, pb in rb.repairs.items():
                cost = pa.cost + pb.cost
                if p not in reps or cost < reps[p].cost:
                    reps[p] = Repair(
                        cost, merge(pa.value, pb.value), pb.op, pb.expected,
                        True,
                        Chain(
                            pa.prefix,
                            ChainL(PrefixItem(pa.op, pa.expected), pb.prefix)
                        )
                    )
    if reps:
        return Recovered(reps, ra.pos, ra.expected)
    return ra.to_error()


def bind(
        parse_fn: ParseFn[S, P, V],
        fn: Callable[[V], ParseObj[S, P, U]]) -> ParseFn[S, P, U]:
    def bind(stream: S, pos: P, rm: RecoveryMode) -> Result[P, U]:
        ra = parse_fn(stream, pos, rm)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return _continue_parse(
                stream, ra, lambda s, i, p: fn(p.value).parse_fn(s, i, True),
                lambda _, v: v
            )
        return fn(ra.value).parse_fn(
            stream, ra.pos, maybe_allow_recovery(rm, ra)
        ).merge_expected(ra.expected, ra.consumed)

    return bind


def _make_seq(
        parse_fn: ParseFn[S, P, V], second_fn: ParseFn[S, P, U],
        fn: Callable[[V, U], X]) -> ParseFn[S, P, X]:
    def seq(stream: S, pos: P, rm: RecoveryMode) -> Result[P, X]:
        ra = parse_fn(stream, pos, rm)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return _continue_parse(
                stream, ra, lambda s, i, p: second_fn(s, i, True), fn
            )
        va = ra.value
        return second_fn(stream, ra.pos, maybe_allow_recovery(rm, ra)).fmap(
            lambda vb: fn(va, vb)
        ).merge_expected(ra.expected, ra.consumed)

    return seq


def lseq(
        parse_fn: ParseFn[S, P, V],
        second_fn: ParseFn[S, P, U]) -> ParseFn[S, P, V]:
    return _make_seq(parse_fn, second_fn, lambda l, _: l)


def rseq(
        parse_fn: ParseFn[S, P, V],
        second_fn: ParseFn[S, P, U]) -> ParseFn[S, P, U]:
    return _make_seq(parse_fn, second_fn, lambda _, r: r)


def seq(
        parse_fn: ParseFn[S, P, V],
        second_fn: ParseFn[S, P, U]) -> ParseFn[S, P, Tuple[V, U]]:
    return _make_seq(parse_fn, second_fn, lambda l, r: (l, r))


def maybe(parse_fn: ParseFn[S, P, V]) -> ParseFn[S, P, Optional[V]]:
    def maybe(stream: S, pos: P, rm: RecoveryMode) -> Result[P, Optional[V]]:
        r = parse_fn(stream, pos, disallow_recovery(rm))
        if r.consumed is True or type(r) is Ok:
            return r
        return Ok(None, pos, r.expected)

    return maybe


def many(parse_fn: ParseFn[S, P, V]) -> ParseFn[S, P, List[V]]:
    def many(stream: S, pos: P, rm: RecoveryMode) -> Result[P, List[V]]:
        rm = disallow_recovery(rm)
        consumed = False
        value: List[V] = []
        r = parse_fn(stream, pos, rm)
        while type(r) is Ok:
            consumed |= r.consumed
            value.append(r.value)
            r = parse_fn(stream, r.pos, rm)
        if type(r) is Recovered:
            return _continue_parse(
                stream, r, parse, lambda a, b: [*value, a, *b]
            )
        if r.consumed:
            return r
        return Ok(value, r.pos, r.expected, consumed)

    def parse(stream: S, pos: P, p: Repair[P, V]) -> Result[P, List[V]]:
        r = many(stream, pos, True)
        if type(r) is Error and r.consumed is False:
            return Ok[P, List[V]]([], r.pos, r.expected)
        return r

    return many


def attempt(parse_fn: ParseFn[S, P, V]) -> ParseFn[S, P, V]:
    def attempt(stream: S, pos: P, rm: RecoveryMode) -> Result[P, V]:
        r = parse_fn(stream, pos, rm if rm else None)
        if type(r) is Error:
            return Error(r.pos, r.expected)
        if type(r) is Recovered:
            return Recovered(
                {
                    p: Repair(
                        r.cost, r.value, r.op, r.expected, False, r.prefix
                    )
                    for p, r in r.repairs.items()
                },
                r.pos, r.expected
            )
        return r

    return attempt


def label(parse_fn: ParseFn[S, P, V], x: str) -> ParseFn[S, P, V]:
    expected = [x]

    def label(stream: S, pos: P, rm: RecoveryMode) -> Result[P, V]:
        return parse_fn(stream, pos, rm).expect(expected)

    return label


class Delay(ParseObj[S_contra, P, V_co]):
    def __init__(self) -> None:
        def _fn(stream: S_contra, pos: P, rm: RecoveryMode) -> Result[P, V_co]:
            raise RuntimeError("Delayed parser was not defined")

        self._defined = False
        self._fn: ParseFn[S_contra, P, V_co] = _fn

    def define_fn(self, parse_fn: ParseFn[S_contra, P, V_co]) -> None:
        if self._defined:
            raise RuntimeError("Delayed parser was already defined")
        self._defined = True
        self._fn = parse_fn

    def to_fn(self) -> ParseFn[S_contra, P, V_co]:
        if self._defined:
            return self._fn
        return super().to_fn()

    def parse_fn(
            self, stream: S_contra, pos: P,
            rm: RecoveryMode) -> Result[P, V_co]:
        return self._fn(stream, pos, rm)
