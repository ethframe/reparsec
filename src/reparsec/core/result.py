from typing import Callable, Generic, Iterable, List, Optional, TypeVar, Union

from typing_extensions import final

from .chain import Append
from .repair import Repair, ops_prepend_expected, ops_set_expected
from .types import Ctx, Loc

A = TypeVar("A")
A_co = TypeVar("A_co", covariant=True)
B = TypeVar("B")
S = TypeVar("S")


@final
class Ok(Generic[A_co, S]):
    __slots__ = "value", "pos", "ctx", "expected", "consumed"

    def __init__(
            self, value: A_co, pos: int, ctx: Ctx[S],
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

    def fmap(self, fn: Callable[[A_co], B]) -> "Ok[B, S]":
        return Ok(
            fn(self.value), self.pos, self.ctx, self.expected, self.consumed
        )

    def set_ctx(self, ctx: Ctx[S]) -> "Ok[A_co, S]":
        self.ctx = ctx
        return self

    def set_expected(self, expected: Iterable[str]) -> "Ok[A_co, S]":
        if not self.consumed:
            self.expected = expected
        return self

    def prepend_expected(
            self, expected: Iterable[str], consumed: bool) -> "Ok[A_co, S]":
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
class Recovered(Generic[A_co, S]):
    __slots__ = "repairs", "min_prio", "loc", "expected", "consumed"

    def __init__(
            self, repairs: List[Repair[A_co, S]], min_prio: Optional[int],
            loc: Loc, expected: Iterable[str] = (), consumed: bool = False):
        self.repairs = repairs
        self.min_prio = min_prio
        self.loc = loc
        self.expected = expected
        self.consumed = consumed

    def __repr__(self) -> str:
        return (
            "Recovered(repairs={!r}, min_prio={!r}, loc={!r}, expected={!r},"
            " consumed={!r})"
        ).format(
            self.repairs, self.min_prio, self.loc, self.expected, self.consumed
        )

    def fmap(self, fn: Callable[[A_co], B]) -> "Recovered[B, S]":
        return Recovered(
            [
                Repair(
                    r.cost, r.prio, r.ins, r.ops, fn(r.value), r.pos, r.ctx,
                    r.expected, r.consumed
                )
                for r in self.repairs
            ],
            self.min_prio, self.loc, self.expected, self.consumed
        )

    def set_ctx(self, ctx: Ctx[S]) -> "Recovered[A_co, S]":
        for r in self.repairs:
            r.ctx = ctx
        return self

    def set_expected(self, expected: Iterable[str]) -> "Recovered[A_co, S]":
        if not self.consumed:
            self.expected = expected
        for r in self.repairs:
            if not r.consumed:
                r.expected = expected
            ops_set_expected(r.ops, expected)
        return self

    def prepend_expected(
            self, expected: Iterable[str],
            consumed: bool) -> "Recovered[A_co, S]":
        if not self.consumed:
            self.expected = Append(expected, self.expected)
            self.consumed |= consumed
        for r in self.repairs:
            if not r.consumed:
                r.expected = Append(expected, r.expected)
                r.consumed |= consumed
            ops_prepend_expected(r.ops, expected, consumed)
        return self


SimpleResult = Union[Ok[A, S], Error]
Result = Union[SimpleResult[A, S], Recovered[A, S]]
