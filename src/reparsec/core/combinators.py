from typing import Callable, List, Optional, Tuple, TypeVar

from .chain import Append, Cons
from .result import Error, Ok, PrefixItem, Recovered, Repair, Result, Selected
from .state import Ctx
from .types import (
    ParseFn, ParseObj, RecoveryMode, disallow_recovery, maybe_allow_recovery
)

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

    def _handle_pending(rep: Repair[V, S]) -> Optional[Selected[X, S]]:
        rb = parse(rep.value, stream, rep.pos, rep.ctx)
        if type(rb) is Ok:
            if selected is None or selected.selected > rep.pos:
                return Selected(
                    rep.pos, merge(rep.value, rb.value), rb.pos, rb.ctx,
                    rep.op, rep.expected, rep.consumed or rb.consumed,
                    rep.prefix
                )
        elif type(rb) is Recovered:
            pending.extend(
                Repair(
                    merge(rep.value, pb.value), pb.pos, pb.ctx, pb.op,
                    pb.expected, pb.consumed,
                    Append(
                        rep.prefix,
                        Cons(PrefixItem(rep.op, rep.expected), pb.prefix)
                    )
                )
                for pb in rb.pending
            )
            if rb.selected is not None:
                repb = rb.selected
                if selected is None or selected.selected > repb.selected:
                    return Selected(
                        repb.selected, merge(rep.value, repb.value), repb.pos,
                        repb.ctx, repb.op, repb.expected, repb.consumed,
                        Append(
                            rep.prefix,
                            Cons(PrefixItem(rep.op, rep.expected), repb.prefix)
                        )
                    )
        return selected

    sel = ra.selected
    if sel is not None:
        rb = parse(sel.value, stream, sel.pos, sel.ctx)
        selected, pending = _merge_selected(sel, rb, merge)
    else:
        selected = None
        pending = []

    for pa in ra.pending:
        selected = _handle_pending(pa)

    if selected is not None or pending:
        return Recovered(selected, pending, ra.pos, ra.loc, ra.expected)

    return Error(ra.pos, ra.loc, ra.expected, True)


def _merge_selected(
        rep: Selected[V, S], rb: Result[U, S],
        merge: MergeFn[V, U, X]) -> Tuple[
            Optional[Selected[X, S]], List[Repair[X, S]]]:
    if type(rb) is Ok:
        return (
            Selected(
                rep.selected, merge(rep.value, rb.value), rb.pos, rb.ctx,
                rep.op, rep.expected, rep.consumed or rb.consumed, rep.prefix
            ),
            []
        )
    elif type(rb) is Recovered:
        pending = [
            Repair(
                merge(rep.value, pb.value), pb.pos, pb.ctx, pb.op,
                pb.expected, pb.consumed,
                Append(
                    rep.prefix,
                    Cons(PrefixItem(rep.op, rep.expected), pb.prefix)
                )
            )
            for pb in rb.pending
        ]
        if rb.selected is not None:
            repb = rb.selected
            return (
                Selected(
                    rep.selected, merge(rep.value, repb.value), repb.pos,
                    repb.ctx, repb.op, repb.expected, repb.consumed,
                    Append(
                        rep.prefix,
                        Cons(PrefixItem(rep.op, rep.expected), repb.prefix)
                    )
                ),
                pending
            )
        return None, pending
    return None, []


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
        expected = Append(ra.expected, rb.expected)
        if type(ra) is Ok:
            return ra.expect(expected)
        if type(rb) is Ok:
            return rb.expect(expected)
        if rm:
            rra = parse_fn(stream, pos, ctx, True)
            rrb = second_fn(stream, pos, ctx, True)
            if type(rra) is Recovered:
                if type(rrb) is Recovered:
                    return _merge_alt_recovered(rra, rrb).expect(expected)
                return rra.expect(expected)
            if type(rrb) is Recovered:
                return rrb.expect(expected)
        return Error(pos, ra.loc, expected)

    return alt


def _merge_alt_recovered(
        ra: Recovered[V, S], rb: Recovered[V, S]) -> Recovered[V, S]:
    selected = ra.selected
    if selected is None:
        selected = rb.selected
    else:
        selected_b = rb.selected
        if selected_b is not None and selected_b.selected < selected.selected:
            selected = selected_b
    return Recovered(
        selected, ra.pending + rb.pending, ra.pos, ra.loc, ra.expected
    )


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
            selected = r.selected
            return Recovered(
                None if selected is None else Selected(
                    selected.selected, selected.value, selected.pos,
                    selected.ctx, selected.op, selected.expected, False,
                    selected.prefix
                ),
                [
                    Repair(
                        r.value, r.pos, r.ctx, r.op, r.expected, False,
                        r.prefix
                    )
                    for r in r.pending
                ],
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
