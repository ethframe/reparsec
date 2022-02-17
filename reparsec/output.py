from dataclasses import dataclass
from typing import Callable, Generic, List, TypeVar

from .result import Error, Ok, Result
from .state import Loc

S = TypeVar("S")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")


@dataclass
class ErrorItem:
    pos: str
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


class ParseResult(Generic[V_co, S]):
    def __init__(self, result: Result[V_co, S], fmt_loc: Callable[[Loc], str]):
        self._result = result
        self._fmt_loc = fmt_loc

    def fmap(self, fn: Callable[[V_co], U]) -> "ParseResult[U, S]":
        return ParseResult(self._result.fmap(fn), self._fmt_loc)

    def unwrap(self, recover: bool = False) -> V_co:
        if type(self._result) is Ok:
            return self._result.value

        if type(self._result) is Error:
            raise ParseError([
                ErrorItem(
                    self._fmt_loc(self._result.loc),
                    list(self._result.expected)
                )
            ])

        repair = min(self._result.repairs.values(), key=lambda r: r.cost)
        if recover:
            return repair.value
        errors: List[ErrorItem] = []
        for item in repair.prefix:
            errors.append(
                ErrorItem(self._fmt_loc(item.op.loc), list(item.expected))
            )
        errors.append(
            ErrorItem(self._fmt_loc(repair.op.loc), list(repair.expected))
        )
        raise ParseError(errors)
