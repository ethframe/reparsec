from dataclasses import dataclass
from typing import Generic, Iterable, List, TypeVar, Union

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
class BaseRepair(Generic[V_co, S]):
    count: int
    ops: List[OpItem]
    value: V_co
    pos: int
    ctx: Ctx[S]
    expected: Iterable[str] = ()
    consumed: bool = False


class Pending(BaseRepair[V_co, S]):
    pass


@dataclass
class _Selected:
    selected: int
    prefix: int


@dataclass
class Selected(BaseRepair[V_co, S], _Selected):
    pass


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
        value: V, pos: int, ctx: Ctx[S], loc: Loc,
        label: str, expected: Iterable[str] = ()) -> Pending[V, S]:
    return Pending(
        1, [OpItem(Insert(label), loc, expected)], value, pos, ctx,
        consumed=True
    )


def make_skip(
        selected: int, value: V, pos: int, ctx: Ctx[S], loc: Loc, skip: int,
        expected: Iterable[str] = ()) -> Selected[V, S]:
    return Selected(
        selected, 0, 0, [OpItem(Skip(skip), loc, expected)], value, pos, ctx,
        consumed=True
    )


def make_pending_skip(
        value: V, pos: int, ctx: Ctx[S], loc: Loc, skip: int,
        expected: Iterable[str] = ()) -> Pending[V, S]:
    return Pending(0, [OpItem(Skip(skip), loc, expected)], value, pos, ctx)
