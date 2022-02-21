from dataclasses import dataclass
from typing import Callable, Generic, Iterable, List, Optional, TypeVar, Union

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
class Skip:
    count: int
    loc: Loc


@dataclass
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
    pos: int
    ctx: Ctx[S]
    op: RepairOp
    expected: Iterable[str] = ()
    consumed: bool = False
    prefix: Iterable[PrefixItem] = ()


@dataclass
class Repair(BaseRepair[V_co, S]):
    pass


@dataclass
class _Selected(Generic[V_co, S]):
    selected: int


@dataclass
class Selected(BaseRepair[V_co, S], _Selected[V_co, S]):
    pass


@final
class Recovered(Generic[V_co, S]):
    __slots__ = "selected", "pending", "pos", "loc", "expected", "consumed"

    consumed: Literal[True]

    def __init__(
            self, selected: Optional[Selected[V_co, S]],
            pending: List[Repair[V_co, S]], pos: int, loc: Loc,
            expected: Iterable[str] = ()):
        self.selected = selected
        self.pending = pending
        self.pos = pos
        self.loc = loc
        self.expected = expected
        self.consumed = True

    def fmap(self, fn: Callable[[V_co], U]) -> "Recovered[U, S]":
        selected = self.selected
        return Recovered(
            None if selected is None else Selected(
                selected.selected, fn(selected.value), selected.pos,
                selected.ctx, selected.op, selected.expected,
                selected.consumed, selected.prefix
            ),
            [
                Repair(
                    fn(r.value), r.pos, r.ctx, r.op, r.expected, r.consumed,
                    r.prefix
                )
                for r in self.pending
            ],
            self.pos, self.loc, self.expected
        )

    def with_ctx(self, ctx: Ctx[S]) -> "Recovered[V_co, S]":
        selected = self.selected
        return Recovered(
            None if selected is None else Selected(
                selected.selected, selected.value, selected.pos, ctx,
                selected.op, selected.expected, selected.consumed,
                selected.prefix
            ),
            [
                Repair(
                    r.value, r.pos, ctx, r.op, r.expected, r.consumed, r.prefix
                )
                for r in self.pending
            ],
            self.pos, self.loc, self.expected
        )

    def expect(self, expected: Iterable[str]) -> "Recovered[V_co, S]":
        selected = self.selected
        return Recovered(
            None if selected is None else Selected(
                selected.selected, selected.value, selected.pos,
                selected.ctx, selected.op,
                selected.expected if selected.consumed else expected,
                selected.consumed, selected.prefix
            ),
            [
                Repair(
                    r.value, r.pos, r.ctx, r.op,
                    r.expected if r.consumed else expected, r.consumed,
                    r.prefix
                )
                for r in self.pending
            ],
            self.pos, self.loc, self.expected
        )

    def merge_expected(
            self, expected: Iterable[str],
            consumed: bool) -> "Recovered[V_co, S]":
        selected = self.selected
        return Recovered(
            None if selected is None else Selected(
                selected.selected, selected.value, selected.pos, selected.ctx,
                selected.op,
                selected.expected if consumed and selected.consumed
                else Append(expected, selected.expected),
                consumed or selected.consumed, selected.prefix
            ),
            [
                Repair(
                    r.value, r.pos, r.ctx, r.op,
                    r.expected if consumed and r.consumed
                    else Append(expected, r.expected),
                    consumed or r.consumed, r.prefix
                )
                for r in self.pending
            ],
            self.pos, self.loc, self.expected
        )


Result = Union[Recovered[V, S], Ok[V, S], Error]
