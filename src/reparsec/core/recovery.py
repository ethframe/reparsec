from typing import Callable, Dict, Iterable, List, Optional, TypeVar, Union

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

    reps: Dict[int, Repair[C, S]] = {}

    for pos, r in ra.repairs.items():
        rb = parse(r.value, pos, r.ctx, r.ins)
        if type(rb) is Ok:
            if _good_repair(reps, rb.pos, r.cost, r.prio):
                reps[rb.pos] = Repair(
                    r.cost, r.prio, r.ins if pos == rb.pos else ins, r.ops,
                    merge(r.value, rb.value), rb.ctx,
                    _append_expected(r, rb.expected, rb.consumed),
                    r.consumed or rb.consumed
                )
        elif type(rb) is Recovered:
            for rpos, rr in rb.repairs.items():
                if _good_repair(reps, rpos, r.cost + rr.cost, r.prio):
                    reps[rpos] = Repair(
                        r.cost + rr.cost, r.prio, rr.ins, _join_ops(r, rr),
                        merge(r.value, rr.value), rr.ctx,
                        _append_expected(r, rr.expected, rr.consumed),
                        r.consumed or rr.consumed
                    )

    return Recovered(reps, ra.min_prio, ra.loc, ra.expected, ra.consumed)


def _good_repair(
        reps: Dict[int, Repair[A, S]], pos: int, cost: int,
        prio: Optional[int]) -> bool:
    if pos not in reps:
        return True
    rep = reps[pos]
    return (
        cost < rep.cost or
        cost == rep.cost and (
            prio is not None and (rep.prio is None or prio < rep.prio)
        )
    )


def join_repairs(
        ra: Recovered[A, S], rb: Recovered[B, S]) -> Recovered[Union[A, B], S]:

    reps: Dict[int, Repair[Union[A, B], S]] = dict(ra.repairs)

    min_prio = ra.min_prio
    if min_prio is not None:
        for pos, r in rb.repairs.items():
            if pos not in reps and r.prio is not None and r.prio < min_prio:
                reps[pos] = r
        if rb.min_prio is not None and rb.min_prio < min_prio:
            min_prio = rb.min_prio
    else:
        for pos, r in rb.repairs.items():
            if pos not in reps and r.prio is not None:
                reps[pos] = r
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
