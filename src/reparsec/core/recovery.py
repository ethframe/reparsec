from typing import Callable, Iterable, List, Optional, Tuple, TypeVar, Union

from .chain import Append
from .repair import BaseRepair, OpItem, Pending, Selected, ops_prepend_expected
from .result import Error, Ok, Recovered, Result
from .types import Ctx, RecoveryMode, maybe_allow_recovery

S = TypeVar("S")
V = TypeVar("V")
U = TypeVar("U")
X = TypeVar("X")


ContinueFn = Callable[[V, S, int, Ctx[S], RecoveryMode], Result[U, S]]
MergeFn = Callable[[V, U], X]


def continue_parse(
        stream: S, ra: Recovered[V, S], rm: RecoveryMode,
        parse: ContinueFn[V, S, U], merge: MergeFn[V, U, X]) -> Result[X, S]:

    sa = ra.selected
    if sa is not None:
        ctx = sa.ctx.decrease_max_insertions(sa.count)
        rb = parse(
            sa.value, stream, sa.pos, ctx,
            maybe_allow_recovery(ctx, rm, sa.consumed)
        ).set_ctx(sa.ctx)
        selected = _append_selected(sa, rb, merge)
    else:
        selected = None

    pa = ra.pending
    if pa is not None:
        ctx = pa.ctx.decrease_max_insertions(pa.count)
        rb = parse(
            pa.value, stream, pa.pos, ctx,
            maybe_allow_recovery(ctx, rm, pa.consumed)
        ).set_ctx(pa.ctx)
        st, pending = _append_pending(pa, rb, merge)
        if selected is None or st is not None and (
                selected.selected > st.selected or
                selected.selected == st.selected and (
                    selected.prefix > st.prefix or
                    selected.prefix == st.prefix and
                    selected.count > st.count)):
            selected = st
    else:
        pending = None

    if selected is not None or pending is not None:
        return Recovered(selected, pending, ra.loc, ra.expected, ra.consumed)

    return Error(ra.loc, ra.expected, ra.consumed)


def _append_selected(
        rep: Selected[V, S], rb: Result[U, S],
        merge: MergeFn[V, U, X]) -> Optional[Selected[X, S]]:
    if type(rb) is Ok:
        return Selected(
            rep.selected, rep.prefix, 0, rep.ops,
            merge(rep.value, rb.value), rb.pos, rb.ctx,
            _append_expected(rep, rb.expected, rb.consumed),
            rep.consumed or rb.consumed,
        )
    elif type(rb) is Recovered:
        sb = rb.selected
        pb = rb.pending
        if pb is not None and (sb is None or sb.count > pb.count):
            return Selected(
                rep.selected, rep.prefix, rep.count + pb.count,
                _join_ops(rep, pb), merge(rep.value, pb.value), pb.pos, pb.ctx,
                _append_expected(rep, pb.expected, pb.consumed),
                rep.consumed or pb.consumed
            )
        if sb is not None:
            return Selected(
                rep.selected, rep.prefix, sb.count, _join_ops(rep, sb),
                merge(rep.value, sb.value), sb.pos, sb.ctx,
                _append_expected(rep, sb.expected, sb.consumed),
                rep.consumed or sb.consumed
            )
    return None


def _append_pending(
        rep: Pending[V, S], rb: Result[U, S],
        merge: MergeFn[V, U, X]) -> Tuple[
            Optional[Selected[X, S]], Optional[Pending[X, S]]]:
    if type(rb) is Ok:
        if rb.consumed:
            return (
                Selected(
                    rep.pos, rep.count, 0, rep.ops,
                    merge(rep.value, rb.value), rb.pos, rb.ctx,
                    _append_expected(rep, rb.expected, rb.consumed), True
                ),
                None
            )
        return (
            None,
            Pending(
                rep.count, rep.ops, merge(rep.value, rb.value), rb.pos, rb.ctx,
                _append_expected(rep, rb.expected, rb.consumed), rep.consumed
            )
        )
    elif type(rb) is Recovered:
        sb = rb.selected
        pb = rb.pending
        return (
            None if sb is None else Selected(
                sb.selected, rep.count + sb.prefix, sb.count,
                _join_ops(rep, sb), merge(rep.value, sb.value), sb.pos, sb.ctx,
                _append_expected(rep, sb.expected, sb.consumed),
                rep.consumed or sb.consumed
            ),
            None if pb is None else Pending(
                rep.count + pb.count, _join_ops(rep, pb),
                merge(rep.value, pb.value), pb.pos, pb.ctx,
                _append_expected(rep, pb.expected, pb.consumed),
                rep.consumed or pb.consumed
            )
        )
    return (None, None)


def join_repairs(
        ra: Recovered[V, S], rb: Recovered[U, S]) -> Recovered[Union[V, U], S]:
    selected: Optional[Selected[Union[V, U], S]] = ra.selected
    sb = rb.selected
    if selected is None or sb is not None and (
            selected.selected > sb.selected or
            selected.selected == sb.selected and (
                selected.prefix > sb.prefix or
                selected.prefix == sb.prefix and
                selected.count > sb.count)):
        selected = sb
    pending: Optional[Pending[Union[V, U], S]] = ra.pending
    pb = rb.pending
    if pending is None or pb is not None and pending.count > pb.count:
        pending = pb
    if ra.consumed:
        return Recovered(selected, pending, ra.loc, ra.expected, ra.consumed)
    elif rb.consumed:
        return Recovered(selected, pending, rb.loc, rb.expected, rb.consumed)
    return Recovered(
        selected, pending, ra.loc, Append(ra.expected, rb.expected),
        ra.consumed or rb.consumed
    )


def _join_ops(rep: BaseRepair[V, S], repb: BaseRepair[U, S]) -> List[OpItem]:
    ops = [OpItem(i.op, i.loc, i.expected, i.consumed) for i in rep.ops]
    ops_prepend_expected(repb.ops, rep.expected, rep.consumed)
    ops.extend(repb.ops)
    return ops


def _append_expected(
        ra: BaseRepair[V, S], expected: Iterable[str],
        consumed: bool) -> Iterable[str]:
    if consumed:
        return expected
    return Append(ra.expected, expected)
