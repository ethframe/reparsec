from dataclasses import dataclass
from typing import Generic, Iterable, List, Optional, TypeVar, Union

from typing_extensions import final

from .chain import Append
from .types import Ctx, Loc

A = TypeVar("A")
A_co = TypeVar("A_co", covariant=True)
S = TypeVar("S")


@dataclass
@final
class Skip:
    count: int


@dataclass
@final
class Insert:
    label: str


RepairOp = Union[Skip, Insert]


@dataclass
class OpItem:
    op: RepairOp
    loc: Loc
    expected: Iterable[str] = ()
    consumed: bool = False


@dataclass
class Repair(Generic[A_co, S]):
    cost: int
    prio: Optional[int]
    ins: int
    ops: List[OpItem]
    value: A_co
    pos: int
    ctx: Ctx[S]
    expected: Iterable[str] = ()
    consumed: bool = False


def ops_set_expected(ops: List[OpItem], expected: Iterable[str]) -> None:
    for op in ops:
        if not op.consumed:
            op.expected = expected


def ops_prepend_expected(
        ops: List[OpItem], expected: Iterable[str], consumed: bool) -> None:
    for op in ops:
        if not op.consumed:
            op.expected = Append(expected, op.expected)
            op.consumed |= consumed


def make_insert(
        rem: int, value: A, pos: int, ctx: Ctx[S], loc: Loc, label: str,
        expected: Iterable[str] = ()) -> Repair[A, S]:
    return Repair(
        1, None, rem - 1, [OpItem(Insert(label), loc, expected)], value,
        pos, ctx, (), True
    )


def make_user_insert(
        rem: int, value: A, pos: int, ctx: Ctx[S], loc: Loc, label: str,
        expected: Iterable[str] = ()) -> Repair[A, S]:
    return Repair(
        1, 0, rem - 1, [OpItem(Insert(label), loc, expected)], value, pos, ctx,
        (), True
    )


def make_skip(
        ins: int, value: A, pos: int, ctx: Ctx[S], loc: Loc, skip: int,
        expected: Iterable[str] = ()) -> Repair[A, S]:
    return Repair(
        skip, False, ins, [OpItem(Skip(skip), loc, expected)], value, pos, ctx,
        (), True
    )


def make_pending_skip(
        ins: int, value: A, pos: int, ctx: Ctx[S], loc: Loc, skip: int,
        expected: Iterable[str] = ()) -> Repair[A, S]:
    return Repair(
        skip, False, ins, [OpItem(Skip(skip), loc, expected)], value, pos, ctx
    )
