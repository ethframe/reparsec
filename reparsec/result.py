from dataclasses import dataclass
from typing import Callable, Generic, Iterable, Mapping, TypeVar, Union

from typing_extensions import Literal, final

from .chain import Chain

P = TypeVar("P", bound=object)
C = TypeVar("C")
CO = TypeVar("CO")
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")


@final
class Ok(Generic[P, C, V_co]):
    __slots__ = "value", "pos", "ctx", "expected", "consumed"

    def __init__(
            self, value: V_co, pos: P, ctx: C, expected: Iterable[str] = (),
            consumed: bool = False):
        self.value = value
        self.pos = pos
        self.ctx = ctx
        self.expected = expected
        self.consumed = consumed

    def fmap(self, fn: Callable[[V_co], U]) -> "Ok[P, C, U]":
        return Ok(
            fn(self.value), self.pos, self.ctx, self.expected, self.consumed
        )

    def fmap_ctx(self, fn: Callable[[C], CO]) -> "Ok[P, CO, V_co]":
        return Ok(
            self.value, self.pos, fn(self.ctx), self.expected, self.consumed
        )

    def expect(self, expected: Iterable[str]) -> "Ok[P, C, V_co]":
        if self.consumed:
            return self
        return Ok(self.value, self.pos, self.ctx, expected, self.consumed)

    def merge_expected(
            self, expected: Iterable[str], consumed: bool) -> "Ok[P, C, V_co]":
        if consumed and self.consumed:
            return self
        return Ok(
            self.value, self.pos, self.ctx, Chain(expected, self.expected),
            consumed or self.consumed
        )


@final
class Error(Generic[P]):
    __slots__ = "pos", "expected", "consumed"

    def __init__(
            self, pos: P, expected: Iterable[str] = (),
            consumed: bool = False):
        self.pos = pos
        self.expected = expected
        self.consumed = consumed

    def fmap(self, fn: object) -> "Error[P]":
        return self

    def fmap_ctx(self, fn: object) -> "Error[P]":
        return self

    def expect(self, expected: Iterable[str]) -> "Error[P]":
        if self.consumed:
            return self
        return Error(self.pos, expected, self.consumed)

    def merge_expected(
            self, expected: Iterable[str], consumed: bool) -> "Error[P]":
        if consumed and self.consumed:
            return self
        return Error(
            self.pos, Chain(expected, self.expected), consumed or self.consumed
        )


@dataclass
class Skip(Generic[P]):
    count: int
    pos: P


@dataclass
class Insert(Generic[P]):
    label: str
    pos: P


RepairOp = Union[Skip[P], Insert[P]]


@dataclass
class PrefixItem(Generic[P]):
    op: RepairOp[P]
    expected: Iterable[str]


@dataclass
class Repair(Generic[P, C, V_co]):
    cost: int
    value: V_co
    ctx: C
    op: RepairOp[P]
    expected: Iterable[str] = ()
    consumed: bool = False
    prefix: Iterable[PrefixItem[P]] = tuple()


@final
class Recovered(Generic[P, C, V_co]):
    __slots__ = "repairs", "pos", "expected", "consumed"

    consumed: Literal[True]

    def __init__(
            self, repairs: Mapping[P, Repair[P, C, V_co]], pos: P,
            expected: Iterable[str] = ()):
        self.repairs = repairs
        self.pos = pos
        self.expected = expected
        self.consumed = True

    def fmap(self, fn: Callable[[V_co], U]) -> "Recovered[P, C, U]":
        return Recovered(
            {
                p: Repair(
                    r.cost, fn(r.value), r.ctx, r.op, r.expected, r.consumed,
                    r.prefix
                )
                for p, r in self.repairs.items()
            },
            self.pos, self.expected
        )

    def fmap_ctx(self, fn: Callable[[C], CO]) -> "Recovered[P, CO, V_co]":
        return Recovered(
            {
                p: Repair(
                    r.cost, r.value, fn(r.ctx), r.op, r.expected, r.consumed,
                    r.prefix
                )
                for p, r in self.repairs.items()
            },
            self.pos, self.expected
        )

    def expect(self, expected: Iterable[str]) -> "Recovered[P, C, V_co]":
        return Recovered(
            {
                p: Repair(
                    r.cost, r.value, r.ctx, r.op,
                    r.expected if r.consumed else expected,
                    r.consumed, r.prefix
                )
                for p, r in self.repairs.items()
            },
            self.pos, self.expected
        )

    def merge_expected(
            self, expected: Iterable[str],
            consumed: bool) -> "Recovered[P, C, V_co]":
        return Recovered(
            {
                p: Repair(
                    r.cost, r.value, r.ctx, r.op,
                    r.expected if consumed and r.consumed
                    else Chain(expected, r.expected),
                    consumed or r.consumed, r.prefix
                )
                for p, r in self.repairs.items()
            },
            self.pos, self.expected
        )


Result = Union[Recovered[P, C, V], Ok[P, C, V], Error[P]]
