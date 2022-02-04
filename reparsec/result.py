from dataclasses import dataclass
from typing import (
    Callable, Generic, Iterable, List, Mapping, NoReturn, TypeVar, Union
)

from typing_extensions import Literal, final

from .chain import Chain

V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")


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
    __slots__ = "value", "pos", "expected", "consumed"

    def __init__(
            self, value: V_co, pos: int, expected: Iterable[str] = (),
            consumed: bool = False):
        self.value = value
        self.pos = pos
        self.expected = expected
        self.consumed = consumed

    def unwrap(self, recover: bool = False) -> V_co:
        return self.value

    def fmap(self, fn: Callable[[V_co], U]) -> "Ok[U]":
        return Ok(fn(self.value), self.pos, self.expected, self.consumed)

    def expect(self, expected: Iterable[str]) -> "Ok[V_co]":
        if self.consumed:
            return self
        return Ok(self.value, self.pos, expected, self.consumed)

    def merge_expected(
            self, expected: Iterable[str], consumed: bool) -> "Ok[V_co]":
        if consumed and self.consumed:
            return self
        return Ok(
            self.value, self.pos, Chain(expected, self.expected),
            consumed or self.consumed
        )


@final
class Error:
    __slots__ = "pos", "expected", "consumed"

    def __init__(
            self, pos: int, expected: Iterable[str] = (),
            consumed: bool = False):
        self.pos = pos
        self.expected = expected
        self.consumed = consumed

    def unwrap(self, recover: bool = False) -> NoReturn:
        raise ParseError([ErrorItem(self.pos, list(self.expected))])

    def fmap(self, fn: object) -> "Error":
        return self

    def expect(self, expected: Iterable[str]) -> "Error":
        if self.consumed:
            return self
        return Error(self.pos, expected, self.consumed)

    def merge_expected(
            self, expected: Iterable[str], consumed: bool) -> "Error":
        if consumed and self.consumed:
            return self
        return Error(
            self.pos, Chain(expected, self.expected), consumed or self.consumed
        )


@dataclass
class Skip:
    count: int
    pos: int


@dataclass
class Insert:
    label: str
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
    op: RepairOp
    expected: Iterable[str] = ()
    consumed: bool = False
    prefix: Iterable[PrefixItem] = ()


@final
class Recovered(Generic[V_co]):
    __slots__ = "repairs", "pos", "expected", "consumed"

    consumed: Literal[True]

    def __init__(
            self, repairs: Mapping[int, Repair[V_co]], pos: int,
            expected: Iterable[str] = ()):
        self.repairs = repairs
        self.pos = pos
        self.expected = expected
        self.consumed = True

    def to_error(self) -> Error:
        return Error(self.pos, self.expected, True)

    def unwrap(self, recover: bool = False) -> V_co:
        repair = min(self.repairs.values(), key=lambda r: r.cost)
        if recover:
            return repair.value
        errors: List[ErrorItem] = []
        for item in repair.prefix:
            errors.append(ErrorItem(item.op.pos, list(item.expected)))
        errors.append(ErrorItem(repair.op.pos, list(repair.expected)))
        raise ParseError(errors)

    def fmap(self, fn: Callable[[V_co], U]) -> "Recovered[U]":
        return Recovered(
            {
                p: Repair(
                    r.cost, fn(r.value), r.op, r.expected, r.consumed,
                    r.prefix
                )
                for p, r in self.repairs.items()
            },
            self.pos, self.expected
        )

    def expect(self, expected: Iterable[str]) -> "Recovered[V_co]":
        return Recovered(
            {
                p: Repair(
                    r.cost, r.value, r.op,
                    r.expected if r.consumed else expected,
                    r.consumed, r.prefix
                )
                for p, r in self.repairs.items()
            },
            self.pos, self.expected
        )

    def merge_expected(
            self, expected: Iterable[str],
            consumed: bool) -> "Recovered[V_co]":
        return Recovered(
            {
                p: Repair(
                    r.cost, r.value, r.op,
                    r.expected if consumed and r.consumed
                    else Chain(expected, r.expected),
                    consumed or r.consumed, r.prefix
                )
                for p, r in self.repairs.items()
            },
            self.pos, self.expected
        )


Result = Union[Recovered[V_co], Ok[V_co], Error]
