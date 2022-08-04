from typing import Callable, Generic, Iterable, List, Optional, TypeVar, Union

from typing_extensions import final

from .chain import Append
from .repair import Repair, ops_prepend_expected, ops_set_expected
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
    __slots__ = "repairs", "min_skip", "loc", "expected", "consumed"

    def __init__(
            self, repairs: List[Repair[V_co, S]], min_skip: Optional[int],
            loc: Loc, expected: Iterable[str] = (), consumed: bool = False):
        self.repairs = repairs
        self.min_skip = min_skip
        self.loc = loc
        self.expected = expected
        self.consumed = consumed

    def __repr__(self) -> str:
        return (
            "Recovered(repairs={!r}, min_skip={!r}, loc={!r}, expected={!r},"
            " consumed={!r})"
        ).format(
            self.repairs, self.min_skip, self.loc, self.expected, self.consumed
        )

    def fmap(self, fn: Callable[[V_co], U]) -> "Recovered[U, S]":
        return Recovered(
            [
                Repair(
                    r.skip, r.auto, r.ins, r.ops, fn(r.value), r.pos, r.ctx,
                    r.expected, r.consumed
                )
                for r in self.repairs
            ],
            self.min_skip, self.loc, self.expected, self.consumed
        )

    def set_ctx(self, ctx: Ctx[S]) -> "Recovered[V_co, S]":
        for r in self.repairs:
            r.ctx = ctx
        return self

    def set_expected(self, expected: Iterable[str]) -> "Recovered[V_co, S]":
        if not self.consumed:
            self.expected = expected
        for r in self.repairs:
            if not r.consumed:
                r.expected = expected
            ops_set_expected(r.ops, expected)
        return self

    def prepend_expected(
            self, expected: Iterable[str],
            consumed: bool) -> "Recovered[V_co, S]":
        if not self.consumed:
            self.expected = Append(expected, self.expected)
            self.consumed |= consumed
        for r in self.repairs:
            if not r.consumed:
                r.expected = Append(expected, r.expected)
                r.consumed |= consumed
            ops_prepend_expected(r.ops, expected, consumed)
        return self


Result = Union[Recovered[V, S], Ok[V, S], Error]
