from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Optional, TypeVar, Union

from typing_extensions import final

from .chain import Append
from .state import Ctx, Loc

V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")
S = TypeVar("S")


@final
class Ok(Generic[V_co, S]):
    __slots__ = "value", "pos", "ctx", "expected", "consumed"

    def __init__(
            self, value: V_co, pos: int, ctx: Ctx[S],
            expected: Iterable[str] = (), consumed: bool = False):
        self.value = value
        self.pos = pos
        self.ctx = ctx
        self.expected = expected
        self.consumed = consumed

    def __repr__(self) -> str:
        return (
            "Ok(value={!r}, pos={!r}, ctx={!r}, expected={!r}, consumed={!r})"
        ).format(self.value, self.pos, self.ctx, self.expected, self.consumed)

    def fmap(self, fn: Callable[[V_co], U]) -> "Ok[U, S]":
        return Ok(
            fn(self.value), self.pos, self.ctx, self.expected, self.consumed
        )

    def with_ctx(self, ctx: Ctx[S]) -> "Ok[V_co, S]":
        self.ctx = ctx
        return self

    def expect(self, expected: Iterable[str]) -> "Ok[V_co, S]":
        if not self.consumed:
            self.expected = expected
        return self

    def merge_expected(
            self, expected: Iterable[str], consumed: bool) -> "Ok[V_co, S]":
        if not self.consumed:
            self.expected = Append(expected, self.expected)
            self.consumed |= consumed
        return self


@final
class Error:
    __slots__ = "pos", "loc", "expected", "consumed"

    def __init__(
            self, pos: int, loc: Loc, expected: Iterable[str] = (),
            consumed: bool = False):
        self.pos = pos
        self.loc = loc
        self.expected = expected
        self.consumed = consumed

    def __repr__(self) -> str:
        return (
            "Error(pos={!r}, loc={!r}, expected={!r}, consumed={!r})"
        ).format(self.pos, self.loc, self.expected, self.consumed)

    def fmap(self, fn: object) -> "Error":
        return self

    def with_ctx(self, ctx: object) -> "Error":
        return self

    def expect(self, expected: Iterable[str]) -> "Error":
        if not self.consumed:
            self.expected = expected
        return self

    def merge_expected(
            self, expected: Iterable[str], consumed: bool) -> "Error":
        if not self.consumed:
            self.expected = Append(expected, self.expected)
            self.consumed |= consumed
        return self


@dataclass
@final
class Skip:
    count: int
    loc: Loc


@dataclass
@final
class Insert:
    label: str
    loc: Loc


RepairOp = Union[Skip, Insert]


@dataclass
class OpItem:
    op: RepairOp
    expected: Iterable[str]


@dataclass
class BaseRepair(Generic[V_co, S]):
    count: int
    value: V_co
    ctx: Ctx[S]
    op: RepairOp
    expected: Iterable[str] = ()
    consumed: bool = False
    ops: Iterable[OpItem] = ()


class Pending(BaseRepair[V_co, S]):
    pass


@dataclass
class _Selected:
    selected: int
    prefix: int
    pos: int


@dataclass
class Selected(BaseRepair[V_co, S], _Selected):
    pass


@final
class Recovered(Generic[V_co, S]):
    __slots__ = "selected", "pending", "pos", "loc", "expected", "consumed"

    def __init__(
            self, selected: Optional[Selected[V_co, S]],
            pending: Optional[Pending[V_co, S]], pos: int, loc: Loc,
            expected: Iterable[str] = (), consumed: bool = False):
        self.selected = selected
        self.pending = pending
        self.pos = pos
        self.loc = loc
        self.expected = expected
        self.consumed = consumed

    def __repr__(self) -> str:
        return (
            "Recovered(selected={!r}, pending={!r}, pos={!r}, loc={!r}, " +
            "expected={!r}, consumed={!r})"
        ).format(
            self.selected, self.pending, self.pos, self.loc, self.expected,
            self.consumed
        )

    def fmap(self, fn: Callable[[V_co], U]) -> "Recovered[U, S]":
        selected = self.selected
        pending = self.pending
        return Recovered(
            None if selected is None else Selected(
                selected.selected, selected.prefix, selected.pos,
                selected.count, fn(selected.value), selected.ctx, selected.op,
                selected.expected, selected.consumed, selected.ops
            ),
            None if pending is None else Pending(
                pending.count, fn(pending.value), pending.ctx, pending.op,
                pending.expected, pending.consumed, pending.ops
            ),
            self.pos, self.loc, self.expected, self.consumed
        )

    def with_ctx(self, ctx: Ctx[S]) -> "Recovered[V_co, S]":
        selected = self.selected
        if selected is not None:
            selected.ctx = ctx
        pending = self.pending
        if pending is not None:
            pending.ctx = ctx
        return self

    def expect(self, expected: Iterable[str]) -> "Recovered[V_co, S]":
        selected = self.selected
        if selected is not None and not selected.consumed:
            selected.expected = expected
        pending = self.pending
        if pending is not None and not pending.consumed:
            pending.expected = expected
        if not self.consumed:
            self.expected = expected
        return self

    def merge_expected(
            self, expected: Iterable[str],
            consumed: bool) -> "Recovered[V_co, S]":
        if not self.consumed:
            self.expected = Append(expected, self.expected)
            self.consumed |= consumed
        selected = self.selected
        if selected is not None and not selected.consumed:
            selected.expected = Append(expected, selected.expected)
            selected.consumed |= consumed
        pending = self.pending
        if pending is not None and not pending.consumed:
            pending.expected = Append(expected, pending.expected)
            pending.consumed |= consumed
        return self


Result = Union[Recovered[V, S], Ok[V, S], Error]
