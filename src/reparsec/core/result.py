from typing import Callable, Generic, Iterable, Optional, TypeVar, Union

from typing_extensions import final

from .chain import Append
from .repair import Pending, Selected, ops_prepend_expected, ops_set_expected
from .types import Ctx, Loc

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

    def set_ctx(self, ctx: Ctx[S]) -> "Ok[V_co, S]":
        self.ctx = ctx
        return self

    def set_expected(self, expected: Iterable[str]) -> "Ok[V_co, S]":
        if not self.consumed:
            self.expected = expected
        return self

    def prepend_expected(
            self, expected: Iterable[str], consumed: bool) -> "Ok[V_co, S]":
        if not self.consumed:
            self.expected = Append(expected, self.expected)
            self.consumed |= consumed
        return self


@final
class Error:
    __slots__ = "loc", "expected", "consumed"

    def __init__(
            self, loc: Loc, expected: Iterable[str] = (),
            consumed: bool = False):
        self.loc = loc
        self.expected = expected
        self.consumed = consumed

    def __repr__(self) -> str:
        return (
            "Error(loc={!r}, expected={!r}, consumed={!r})"
        ).format(self.loc, self.expected, self.consumed)

    def fmap(self, fn: object) -> "Error":
        return self

    def set_ctx(self, ctx: object) -> "Error":
        return self

    def set_expected(self, expected: Iterable[str]) -> "Error":
        if not self.consumed:
            self.expected = expected
        return self

    def prepend_expected(
            self, expected: Iterable[str], consumed: bool) -> "Error":
        if not self.consumed:
            self.expected = Append(expected, self.expected)
            self.consumed |= consumed
        return self


@final
class Recovered(Generic[V_co, S]):
    __slots__ = "selected", "pending", "loc", "expected", "consumed"

    def __init__(
            self, selected: Optional[Selected[V_co, S]],
            pending: Optional[Pending[V_co, S]], loc: Loc,
            expected: Iterable[str] = (), consumed: bool = False):
        self.selected = selected
        self.pending = pending
        self.loc = loc
        self.expected = expected
        self.consumed = consumed

    def __repr__(self) -> str:
        return (
            "Recovered(selected={!r}, pending={!r}, loc={!r}, " +
            "expected={!r}, consumed={!r})"
        ).format(
            self.selected, self.pending, self.loc, self.expected, self.consumed
        )

    def fmap(self, fn: Callable[[V_co], U]) -> "Recovered[U, S]":
        selected = self.selected
        pending = self.pending
        return Recovered(
            None if selected is None else Selected(
                selected.selected, selected.prefix, selected.count,
                selected.ops, fn(selected.value), selected.pos, selected.ctx,
                selected.expected, selected.consumed
            ),
            None if pending is None else Pending(
                pending.count, pending.ops, fn(pending.value), pending.pos,
                pending.ctx, pending.expected, pending.consumed
            ),
            self.loc, self.expected, self.consumed
        )

    def set_ctx(self, ctx: Ctx[S]) -> "Recovered[V_co, S]":
        selected = self.selected
        if selected is not None:
            selected.ctx = ctx
        pending = self.pending
        if pending is not None:
            pending.ctx = ctx
        return self

    def set_expected(self, expected: Iterable[str]) -> "Recovered[V_co, S]":
        if not self.consumed:
            self.expected = expected
        selected = self.selected
        if selected is not None:
            if not selected.consumed:
                selected.expected = expected
            ops_set_expected(selected.ops, expected)
        pending = self.pending
        if pending is not None:
            if not pending.consumed:
                pending.expected = expected
            ops_set_expected(pending.ops, expected)
        return self

    def prepend_expected(
            self, expected: Iterable[str],
            consumed: bool) -> "Recovered[V_co, S]":
        if not self.consumed:
            self.expected = Append(expected, self.expected)
            self.consumed |= consumed
        selected = self.selected
        if selected is not None:
            if not selected.consumed:
                selected.expected = Append(expected, selected.expected)
                selected.consumed |= consumed
            ops_prepend_expected(selected.ops, expected, consumed)
        pending = self.pending
        if pending is not None:
            if not pending.consumed:
                pending.expected = Append(expected, pending.expected)
                pending.consumed |= consumed
            ops_prepend_expected(pending.ops, expected, consumed)
        return self


Result = Union[Recovered[V, S], Ok[V, S], Error]
