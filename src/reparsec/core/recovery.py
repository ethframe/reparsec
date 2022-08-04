from typing import Callable, Iterable, List, TypeVar, Union

from .chain import Append
from .repair import OpItem, Repair, ops_prepend_expected
from .result import Ok, Recovered, Result
from .types import Ctx, RecoveryState

S = TypeVar("S")
V = TypeVar("V")
U = TypeVar("U")
X = TypeVar("X")


ContinueFn = Callable[[V, S, int, Ctx[S], RecoveryState], Result[U, S]]
MergeFn = Callable[[V, U], X]


def continue_parse(
        stream: S, ra: Recovered[V, S], parse: ContinueFn[V, S, U],
        merge: MergeFn[V, U, X]) -> Result[X, S]:

    reps: List[Repair[X, S]] = []
    for r in ra.repairs:
        rb = parse(r.value, stream, r.pos, r.ctx, (r.ins,))
        if type(rb) is Ok:
            reps.append(
                Repair(
                    r.skip, r.auto, rb.ctx.ins if rb.consumed else r.ins,
                    r.ops, merge(r.value, rb.value), rb.pos, rb.ctx,
                    _append_expected(r, rb.expected, rb.consumed),
                    r.consumed or rb.consumed
                )
            )
        elif type(rb) is Recovered:
            for rr in rb.repairs:
                reps.append(
                    Repair(
                        r.skip, r.auto, rr.ins, _join_ops(r, rr),
                        merge(r.value, rr.value), rr.pos, rr.ctx,
                        _append_expected(r, rr.expected, rr.consumed),
                        r.consumed or rr.consumed
                    )
                )

    return Recovered(reps, ra.min_skip, ra.loc, ra.expected, ra.consumed)


def join_repairs(
        ra: Recovered[V, S], rb: Recovered[U, S]) -> Recovered[Union[V, U], S]:
    reps: List[Repair[Union[V, U], S]] = list(ra.repairs)
    min_skip = ra.min_skip
    if min_skip is not None:
        reps.extend(
            r for r in rb.repairs
            if not r.auto or r.skip is not None and r.skip < min_skip
        )
        if rb.min_skip is not None and rb.min_skip < min_skip:
            min_skip = rb.min_skip
    else:
        reps.extend(r for r in rb.repairs if not r.auto or r.skip is not None)
        min_skip = rb.min_skip
    if ra.consumed:
        return Recovered(reps, min_skip, ra.loc, ra.expected, True)
    if rb.consumed:
        return Recovered(reps, min_skip, rb.loc, rb.expected, True)
    return Recovered(
        reps, min_skip, ra.loc, Append(ra.expected, rb.expected),
        ra.consumed or rb.consumed
    )


def _join_ops(rep: Repair[V, S], repb: Repair[U, S]) -> List[OpItem]:
    ops = [OpItem(i.op, i.loc, i.expected, i.consumed) for i in rep.ops]
    ops_prepend_expected(repb.ops, rep.expected, rep.consumed)
    ops.extend(repb.ops)
    return ops


def _append_expected(
        ra: Repair[V, S], expected: Iterable[str],
        consumed: bool) -> Iterable[str]:
    if consumed:
        return expected
    return Append(ra.expected, expected)
