from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Optional, TypeVar, Union

from typing_extensions import Literal, final

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
        return Ok(self.value, self.pos, ctx, self.expected, self.consumed)

    def expect(self, expected: Iterable[str]) -> "Ok[V_co, S]":
        if self.consumed:
            return self
        return Ok(self.value, self.pos, self.ctx, expected, self.consumed)

    def merge_expected(
            self, expected: Iterable[str], consumed: bool) -> "Ok[V_co, S]":
        if consumed and self.consumed:
            return self
        return Ok(
            self.value, self.pos, self.ctx, Append(expected, self.expected),
            consumed or self.consumed
        )


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
        if self.consumed:
            return self
        return Error(self.pos, self.loc, expected, self.consumed)

    def merge_expected(
            self, expected: Iterable[str], consumed: bool) -> "Error":
        if consumed and self.consumed:
            return self
        return Error(
            self.pos, self.loc, Append(expected, self.expected),
            consumed or self.consumed
        )


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
class PrefixItem:
    op: RepairOp
    expected: Iterable[str]


@dataclass
class BaseRepair(Generic[V_co, S]):
    value: V_co
    ctx: Ctx[S]
    op: RepairOp
    expected: Iterable[str] = ()
    consumed: bool = False
    prefix: Iterable[PrefixItem] = ()


@dataclass
class _Pending:
    inserted: int


@dataclass
class Pending(BaseRepair[V_co, S], _Pending):
    pass


@dataclass
class _Selected:
    selected: int
    iprefix: int
    isuffix: int
    pos: int


@dataclass
class Selected(BaseRepair[V_co, S], _Selected):
    pass


@final
class Recovered(Generic[V_co, S]):
    __slots__ = "selected", "pending", "pos", "loc", "expected", "consumed"

    consumed: Literal[True]

    def __init__(
            self, selected: Optional[Selected[V_co, S]],
            pending: Optional[Pending[V_co, S]], pos: int, loc: Loc,
            expected: Iterable[str] = ()):
        self.selected = selected
        self.pending = pending
        self.pos = pos
        self.loc = loc
        self.expected = expected
        self.consumed = True

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
                selected.selected, selected.iprefix, selected.isuffix,
                selected.pos, fn(selected.value), selected.ctx, selected.op,
                selected.expected, selected.consumed, selected.prefix
            ),
            None if pending is None else Pending(
                pending.inserted, fn(pending.value), pending.ctx, pending.op,
                pending.expected, pending.consumed, pending.prefix
            ),
            self.pos, self.loc, self.expected
        )

    def with_ctx(self, ctx: Ctx[S]) -> "Recovered[V_co, S]":
        selected = self.selected
        pending = self.pending
        return Recovered(
            None if selected is None else Selected(
                selected.selected, selected.iprefix, selected.isuffix,
                selected.pos, selected.value, ctx, selected.op,
                selected.expected, selected.consumed, selected.prefix
            ),
            None if pending is None else Pending(
                pending.inserted, pending.value, ctx, pending.op,
                pending.expected, pending.consumed, pending.prefix
            ),
            self.pos, self.loc, self.expected
        )

    def expect(self, expected: Iterable[str]) -> "Recovered[V_co, S]":
        selected = self.selected
        pending = self.pending
        return Recovered(
            None if selected is None else Selected(
                selected.selected, selected.iprefix, selected.isuffix,
                selected.pos, selected.value, selected.ctx, selected.op,
                selected.expected if selected.consumed else expected,
                selected.consumed, selected.prefix
            ),
            None if pending is None else Pending(
                pending.inserted, pending.value, pending.ctx, pending.op,
                pending.expected if pending.consumed else expected,
                pending.consumed, pending.prefix
            ),
            self.pos, self.loc, self.expected
        )

    def merge_expected(
            self, expected: Iterable[str],
            consumed: bool) -> "Recovered[V_co, S]":
        selected = self.selected
        pending = self.pending
        return Recovered(
            None if selected is None else Selected(
                selected.selected, selected.iprefix, selected.isuffix,
                selected.pos, selected.value, selected.ctx, selected.op,
                selected.expected if consumed and selected.consumed
                else Append(expected, selected.expected),
                consumed or selected.consumed, selected.prefix
            ),
            None if pending is None else Pending(
                pending.inserted, pending.value, pending.ctx, pending.op,
                pending.expected if consumed and pending.consumed
                else Append(expected, pending.expected),
                consumed or pending.consumed, pending.prefix
            ),
            self.pos, self.loc, self.expected
        )


Result = Union[Recovered[V, S], Ok[V, S], Error]
