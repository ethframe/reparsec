from dataclasses import dataclass
from typing import Callable, Generic, Iterable, List, NoReturn, TypeVar, Union

from typing_extensions import final

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
    __slots__ = "value", "pos", "expected"

    def __init__(self, value: V_co, pos: int, expected: Iterable[str] = ()):
        self.value = value
        self.pos = pos
        self.expected = expected

    def unwrap(self, recover: bool = False) -> V_co:
        return self.value

    def fmap(self, fn: Callable[[V_co], U]) -> "Ok[U]":
        return Ok(fn(self.value), self.pos, self.expected)

    def expect(self, pos: int, expected: Iterable[str]) -> "Ok[V_co]":
        if self.pos == pos:
            return Ok(self.value, self.pos, expected)
        return self

    def merge_expected(self, pos: int, ra: "LLResult[U]") -> "Ok[V_co]":
        if ra.pos != pos and ra.pos != self.pos:
            return self
        return Ok(self.value, self.pos, Chain(ra.expected, self.expected))


@final
class Error:
    __slots__ = "pos", "expected"

    def __init__(self, pos: int, expected: Iterable[str] = ()):
        self.pos = pos
        self.expected = expected

    def unwrap(self, recover: bool = False) -> NoReturn:
        raise ParseError([ErrorItem(self.pos, list(self.expected))])

    def fmap(self, fn: object) -> "Error":
        return self

    def expect(self, pos: int, expected: Iterable[str]) -> "Error":
        if self.pos == pos:
            return Error(self.pos, expected)
        return self

    def merge_expected(self, pos: int, ra: "LLResult[U]") -> "Error":
        if ra.pos != pos and ra.pos != self.pos:
            return self
        return Error(self.pos, Chain(ra.expected, self.expected))


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
class RepairError:
    op: RepairOp
    expected: Iterable[str]


@dataclass
class PrefixItem:
    error: RepairError
    expected: Iterable[str]


@dataclass
class Repair(Generic[V_co]):
    cost: int
    value: V_co
    pos: int
    error: RepairError
    expected: Iterable[str]
    prefix: Iterable[PrefixItem]


@final
class Recovered(Generic[V_co]):
    __slots__ = ("repairs", "pos")

    def __init__(self, repairs: Iterable[Repair[V_co]]):
        self.repairs = repairs
        self.pos = -1

    def unwrap(self, recover: bool = False) -> V_co:
        repair = next(iter(self.repairs))
        if recover:
            return repair.value
        errors: List[ErrorItem] = []
        for item in repair.prefix:
            errors.append(
                ErrorItem(item.error.op.pos, list(item.error.expected))
            )
        errors.append(
            ErrorItem(repair.error.op.pos, list(repair.error.expected))
        )
        raise ParseError(errors)

    def fmap(self, fn: Callable[[V_co], U]) -> "Recovered[U]":
        return Recovered([
            Repair(p.cost, fn(p.value), p.pos, p.error, p.expected, p.prefix)
            for p in self.repairs
        ])

    def expect(self, pos: int, expected: Iterable[str]) -> "Recovered[V_co]":
        return Recovered([
            Repair(
                p.cost, p.value, p.pos,
                RepairError(p.error.op, expected)
                if p.error.op.pos == pos else p.error,
                expected if p.pos == pos else p.expected,
                p.prefix
            )
            for p in self.repairs
        ])

    def merge_expected(self, pos: int, ra: "LLResult[U]") -> "Recovered[V_co]":
        ra_empty = ra.pos == pos
        return Recovered([
            Repair(
                p.cost, p.value, p.pos,
                RepairError(p.error.op, Chain(ra.expected, p.error.expected))
                if ra_empty or p.error.op.pos == ra.pos else p.error,
                Chain(ra.expected, p.expected) if ra_empty else p.expected,
                p.prefix
            )
            for p in self.repairs
        ])


Result = Union[Recovered[V], Ok[V], Error]
LLResult = Union[Ok[V], Error]
