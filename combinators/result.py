from dataclasses import dataclass
from typing import Callable, Generic, Iterable, List, NoReturn, TypeVar, Union

from typing_extensions import Literal, final

from .chain import Chain

V = TypeVar("V", bound=object)
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U", bound=object)


@dataclass
class ErrorItem:
    pos: int
    expected: List[str]

    def msg(self) -> str:
        if not self.expected:
            return "at {}: unexpected input".format(self.pos)
        if len(self.expected) == 1:
            return "at {}: expected {}".format(self.pos, self.expected[0])
        return "at {}: expected {} or {}".format(
            self.pos, ', '.join(self.expected[:-1]), self.expected[-1]
        )


class ParseError(Exception):
    def __init__(self, errors: List[ErrorItem]):
        super().__init__(errors)
        self.errors = errors

    def __str__(self) -> str:
        return ", ".join(error.msg() for error in self.errors)


@final
class Ok(Generic[V_co]):
    __slots__ = "value", "pos", "consumed", "expected"

    def __init__(
            self, value: V_co, pos: int, consumed: bool,
            expected: Iterable[str] = ()):
        self.value = value
        self.pos = pos
        self.consumed = consumed
        self.expected = expected

    def unwrap(self, recover: bool = False) -> V_co:
        return self.value

    def fmap(self, fn: Callable[[V_co], U]) -> "Ok[U]":
        return Ok(fn(self.value), self.pos, self.consumed, self.expected)

    def expect(self, expected: Iterable[str]) -> "Ok[V_co]":
        if self.consumed:
            return self
        return Ok(self.value, self.pos, self.consumed, expected)

    def merge_expected(self, ra: "LLResult[U]") -> "Ok[V_co]":
        if ra.consumed and self.consumed:
            return self
        return Ok(
            self.value, self.pos, ra.consumed or self.consumed,
            Chain(ra.expected, self.expected)
        )


@final
class Error:
    __slots__ = "pos", "consumed", "expected"

    def __init__(self, pos: int, consumed: bool, expected: Iterable[str] = ()):
        self.pos = pos
        self.consumed = consumed
        self.expected = expected

    def unwrap(self, recover: bool = False) -> NoReturn:
        raise ParseError([ErrorItem(self.pos, list(self.expected))])

    def fmap(self, fn: object) -> "Error":
        return self

    def expect(self, expected: Iterable[str]) -> "Error":
        if self.consumed:
            return self
        return Error(self.pos, self.consumed, expected)

    def merge_expected(self, ra: "LLResult[U]") -> "Error":
        if ra.consumed and self.consumed:
            return self
        return Error(
            self.pos, ra.consumed or self.consumed,
            Chain(ra.expected, self.expected)
        )


@dataclass
class Skip:
    count: int
    pos: int


@dataclass
class Insert:
    token: str
    pos: int


RepairOp = Union[Skip, Insert]


@dataclass
class PrefixItem:
    op: RepairOp
    expected: Iterable[str]


@dataclass
class Repair(Generic[V_co]):
    cost: int
    value: V_co
    pos: int
    op: RepairOp
    consumed: bool
    expected: Iterable[str]
    prefix: Iterable[PrefixItem]


@final
class Recovered(Generic[V_co]):
    __slots__ = "repairs", "consumed"

    consumed: Literal[True]

    def __init__(self, repairs: Iterable[Repair[V_co]]):
        self.repairs = repairs
        self.consumed = True

    def to_error(self) -> Error:
        repair = min(self.repairs, key=lambda r: r.cost)
        return Error(repair.op.pos, repair.consumed, repair.expected)

    def unwrap(self, recover: bool = False) -> V_co:
        repair = next(iter(self.repairs))
        if recover:
            return repair.value
        errors: List[ErrorItem] = []
        for item in repair.prefix:
            errors.append(ErrorItem(item.op.pos, list(item.expected)))
        errors.append(ErrorItem(repair.op.pos, list(repair.expected)))
        raise ParseError(errors)

    def fmap(self, fn: Callable[[V_co], U]) -> "Recovered[U]":
        return Recovered([
            Repair(
                p.cost, fn(p.value), p.pos, p.op, p.consumed, p.expected,
                p.prefix
            )
            for p in self.repairs
        ])

    def expect(self, expected: Iterable[str]) -> "Recovered[V_co]":
        return Recovered([
            Repair(
                p.cost, p.value, p.pos, p.op, p.consumed,
                p.expected if p.consumed else expected,
                p.prefix
            )
            for p in self.repairs
        ])

    def merge_expected(self, ra: "LLResult[U]") -> "Recovered[V_co]":
        return Recovered([
            Repair(
                p.cost, p.value, p.pos, p.op,  ra.consumed or p.consumed,
                p.expected if ra.consumed and p.consumed
                else Chain(ra.expected, p.expected),
                p.prefix
            )
            for p in self.repairs
        ])


Result = Union[Recovered[V], Ok[V], Error]
LLResult = Union[Ok[V], Error]
