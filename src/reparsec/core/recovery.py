from typing import Callable, Iterable, List, TypeVar, Union

from .chain import Append
from .repair import OpItem, Repair, ops_prepend_expected
from .result import Ok, Recovered, Result
from .types import Ctx

S = TypeVar("S")
A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")


ContinueFn = Callable[[A, int, Ctx[S], int], Result[B, S]]
MergeFn = Callable[[A, B], C]


def continue_parse(
        ra: Recovered[A, S], ins: int, parse: ContinueFn[A, S, B],
        merge: MergeFn[A, B, C]) -> Result[C, S]:

    reps: List[Repair[C, S]] = []
    for r in ra.repairs:
        rb = parse(r.value, r.pos, r.ctx, r.ins)
        if type(rb) is Ok:
            reps.append(
                Repair(
                    r.cost, r.prio, r.ins if r.pos == rb.pos else ins, r.ops,
                    merge(r.value, rb.value), rb.pos, rb.ctx,
                    _append_expected(r, rb.expected, rb.consumed),
                    r.consumed or rb.consumed
                )
            )
        elif type(rb) is Recovered:
            for rr in rb.repairs:
                reps.append(
                    Repair(
                        r.cost + rr.cost, r.prio, rr.ins, _join_ops(r, rr),
                        merge(r.value, rr.value), rr.pos, rr.ctx,
                        _append_expected(r, rr.expected, rr.consumed),
                        r.consumed or rr.consumed
                    )
                )

    return Recovered(reps, ra.min_prio, ra.loc, ra.expected, ra.consumed)


def join_repairs(
        ra: Recovered[A, S], rb: Recovered[B, S]) -> Recovered[Union[A, B], S]:
    reps: List[Repair[Union[A, B], S]] = list(ra.repairs)
    min_prio = ra.min_prio
    if min_prio is not None:
        reps.extend(
            r for r in rb.repairs if r.prio is not None and r.prio < min_prio
        )
        if rb.min_prio is not None and rb.min_prio < min_prio:
            min_prio = rb.min_prio
    else:
        reps.extend(r for r in rb.repairs if r.prio is not None)
        min_prio = rb.min_prio
    if ra.consumed:
        return Recovered(reps, min_prio, ra.loc, ra.expected, True)
    if rb.consumed:
        return Recovered(reps, min_prio, rb.loc, rb.expected, True)
    return Recovered(
        reps, min_prio, ra.loc, Append(ra.expected, rb.expected),
        ra.consumed or rb.consumed
    )


def _join_ops(rep: Repair[A, S], repb: Repair[B, S]) -> List[OpItem]:
    ops = [OpItem(i.op, i.loc, i.expected, i.consumed) for i in rep.ops]
    ops_prepend_expected(repb.ops, rep.expected, rep.consumed)
    ops.extend(repb.ops)
    return ops


def _append_expected(
        ra: Repair[A, S], expected: Iterable[str],
        consumed: bool) -> Iterable[str]:
    if consumed:
        return expected
    return Append(ra.expected, expected)
