from dataclasses import dataclass
from typing import Callable, Generic, Iterable, List, NoReturn, TypeVar, Union

from typing_extensions import final

from .chain import Chain, ChainL

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

    def expect(self, expected: Iterable[str]) -> "Ok[V_co]":
        return Ok(self.value, self.pos, expected)


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

    def expect(self, expected: Iterable[str]) -> "Error":
        return Error(self.pos, expected)


class RepairOp:
    pos: int


@dataclass
class Skip(RepairOp):
    count: int
    pos: int


@dataclass
class Insert(RepairOp):
    token: str
    pos: int


@dataclass
class Repair(Generic[V_co]):
    cost: int
    value: V_co
    pos: int
    ops: Iterable[RepairOp]
    errors: Iterable[Iterable[str]] = ()


@final
class Recovered(Generic[V_co]):
    __slots__ = "repairs", "pos", "expected"

    def __init__(
            self, repairs: Iterable[Repair[V_co]], pos: int,
            expected: Iterable[str] = ()):
        self.repairs = repairs
        self.pos = pos
        self.expected = expected

    def unwrap(self, recover: bool = False) -> V_co:
        repair = next(iter(self.repairs))
        if recover:
            return repair.value
        errors: List[ErrorItem] = []
        ops_expected = zip(repair.ops, ChainL(self.expected, repair.errors))
        for op, expected in ops_expected:
            errors.append(ErrorItem(op.pos, list(expected)))
        raise ParseError(errors)

    def fmap(self, fn: Callable[[V_co], U]) -> "Recovered[U]":
        return Recovered(
            [
                Repair(p.cost, fn(p.value), p.pos, p.ops, p.errors)
                for p in self.repairs
            ],
            self.pos, self.expected
        )

    def expect(self, expected: Iterable[str]) -> "Recovered[V_co]":
        return Recovered(self.repairs, self.pos, expected)


Result = Union[Recovered[V], Ok[V], Error]


def merge_expected(pos: int, ra: Result[V], rb: Result[U]) -> Iterable[str]:
    if ra.pos != pos and ra.pos != rb.pos:
        return rb.expected
    return Chain(ra.expected, rb.expected)
