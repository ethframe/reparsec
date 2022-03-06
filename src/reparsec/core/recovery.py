from typing import Callable, Optional, Tuple, TypeVar

from .chain import Append, Cons
from .result import Error, Ok, Pending, PrefixItem, Recovered, Result, Selected
from .state import Ctx

S = TypeVar("S")
V = TypeVar("V")
U = TypeVar("U")
X = TypeVar("X")


ContinueFn = Callable[[V, S, int, Ctx[S]], Result[U, S]]
MergeFn = Callable[[V, U], X]


def continue_parse(
        stream: S, ra: Recovered[V, S], parse: ContinueFn[V, S, U],
        merge: MergeFn[V, U, X]) -> Result[X, S]:

    sa = ra.selected
    if sa is not None:
        rb = parse(sa.value, stream, sa.pos, sa.ctx)
        selected = _append_selected(sa, rb, merge)
    else:
        selected = None

    pa = ra.pending
    if pa is not None:
        rb = parse(pa.value, stream, ra.pos, pa.ctx)
        st, pending = _append_pending(pa, ra.pos, rb, merge)
        if selected is None or st is not None and (
                selected.selected > st.selected or
                selected.selected == st.selected and
                selected.iprefix + selected.isuffix > st.iprefix + st.isuffix):
            selected = st
    else:
        pending = None

    if selected is not None or pending is not None:
        return Recovered(selected, pending, ra.pos, ra.loc, ra.expected)

    return Error(ra.pos, ra.loc, ra.expected, True)


def _append_selected(
        rep: Selected[V, S], rb: Result[U, S],
        merge: MergeFn[V, U, X]) -> Optional[Selected[X, S]]:
    if type(rb) is Ok:
        return Selected(
            rep.selected, rep.iprefix, 0, rb.pos, merge(rep.value, rb.value),
            rb.ctx, rep.op, rep.expected, rep.consumed or rb.consumed,
            rep.prefix
        )
    elif type(rb) is Recovered:
        sb = rb.selected
        if sb is not None:
            return Selected(
                rep.selected, rep.iprefix, sb.isuffix, sb.pos,
                merge(rep.value, sb.value), sb.ctx, sb.op, sb.expected,
                sb.consumed,
                Append(
                    rep.prefix,
                    Cons(PrefixItem(rep.op, rep.expected), sb.prefix)
                )
            )
        pb = rb.pending
        if pb is not None:
            return Selected(
                rep.selected, rep.iprefix, pb.inserted, rep.pos,
                merge(rep.value, pb.value), pb.ctx, pb.op, pb.expected,
                pb.consumed,
                Append(
                    rep.prefix,
                    Cons(PrefixItem(rep.op, rep.expected), pb.prefix)
                )
            )
        raise RuntimeError("Invalid recovered result")
    return None


def _append_pending(
        rep: Pending[V, S], pos: int, rb: Result[U, S],
        merge: MergeFn[V, U, X]) -> Tuple[
            Optional[Selected[X, S]], Optional[Pending[X, S]]]:
    if type(rb) is Ok:
        if rb.consumed:
            return (
                Selected(
                    pos, rep.inserted, 0, rb.pos, merge(rep.value, rb.value),
                    rb.ctx, rep.op, rep.expected, True, rep.prefix
                ),
                None
            )
        return (
            None,
            Pending(
                rep.inserted, merge(rep.value, rb.value), rb.ctx, rep.op,
                rep.expected, rep.consumed, rep.prefix
            )
        )
    elif type(rb) is Recovered:
        sb = rb.selected
        pb = rb.pending
        return (
            None if sb is None else Selected(
                sb.pos, rep.inserted + sb.iprefix, sb.isuffix, sb.pos,
                merge(rep.value, sb.value), sb.ctx, sb.op, sb.expected,
                sb.consumed,
                Append(
                    rep.prefix,
                    Cons(PrefixItem(rep.op, rep.expected), sb.prefix)
                )
            ),
            None if pb is None else Pending(
                rep.inserted + pb.inserted, merge(rep.value, pb.value), pb.ctx,
                pb.op, pb.expected, pb.consumed,
                Append(
                    rep.prefix,
                    Cons(PrefixItem(rep.op, rep.expected), pb.prefix)
                )
            )
        )
    return (None, None)


def join_repairs(ra: Recovered[V, S], rb: Recovered[V, S]) -> Recovered[V, S]:
    selected = ra.selected
    sb = rb.selected
    if selected is None or sb is not None and selected.selected > sb.selected:
        selected = sb
    pending = ra.pending
    pb = rb.pending
    if pending is None or pb is not None and pending.inserted > pb.inserted:
        pending = pb
    return Recovered(selected, pending, ra.pos, ra.loc, ra.expected)
