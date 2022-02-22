from typing import Callable, List, Optional, Tuple, TypeVar

from .chain import Append, Cons
from .result import Error, Ok, PrefixItem, Recovered, Repair, Result, Selected
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
        selected, pending = _append_selected(sel, rb, merge)
    else:
        selected = None
        pending = []

    for pa in ra.pending:
        selected = _handle_pending(pa)

    if selected is not None or pending:
        return Recovered(selected, pending, ra.pos, ra.loc, ra.expected)

    return Error(ra.pos, ra.loc, ra.expected, True)


def _append_selected(
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


def join_repairs(ra: Recovered[V, S], rb: Recovered[V, S]) -> Recovered[V, S]:
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
