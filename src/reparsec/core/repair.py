from dataclasses import dataclass
from typing import Generic, Iterable, List, Optional, Tuple, TypeVar, Union

from typing_extensions import final

from .chain import Append
from .types import Ctx, Loc

V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
S = TypeVar("S")


@dataclass
@final
class Skip:
    count: int

    def cost(self) -> int:
        return self.count


@dataclass
@final
class Insert:
    label: str

    def cost(self) -> int:
        return 1


RepairOp = Union[Skip, Insert]


@dataclass
class OpItem:
    op: RepairOp
    loc: Loc
    expected: Iterable[str] = ()
    consumed: bool = False


@dataclass
class Repair(Generic[V_co, S]):
    skip: Optional[int]
    auto: bool
    ins: int
    ops: List[OpItem]
    value: V_co
    pos: int
    ctx: Ctx[S]
    expected: Iterable[str] = ()
    consumed: bool = False

    def cost(self) -> Tuple[int, int, int]:
        return sum(op.op.cost() for op in self.ops), -self.pos, int(self.auto)


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
        ins: int, value: V, pos: int, ctx: Ctx[S], loc: Loc, label: str,
        expected: Iterable[str] = ()) -> Repair[V, S]:
    return Repair(
        None, True, ins - 1, [OpItem(Insert(label), loc, expected)], value,
        pos, ctx, (), True
    )


def make_skip(
        ins: int, value: V, pos: int, ctx: Ctx[S], loc: Loc, skip: int,
        expected: Iterable[str] = ()) -> Repair[V, S]:
    return Repair(
        skip, True, ins, [OpItem(Skip(skip), loc, expected)], value, pos, ctx,
        (), True
    )


def make_pending_skip(
        ins: int, value: V, pos: int, ctx: Ctx[S], loc: Loc, skip: int,
        expected: Iterable[str] = ()) -> Repair[V, S]:
    return Repair(
        None, True, ins, [OpItem(Skip(skip), loc, expected)], value, pos, ctx
    )
