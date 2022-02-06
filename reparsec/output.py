from dataclasses import dataclass
from typing import Callable, Generic, List, TypeVar

from .result import Error, Ok, Result

P = TypeVar("P")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")


@dataclass
class ErrorItem:
    pos: object
    expected: List[str]

    def msg(self) -> str:
        if not self.expected:
            return "at {!r}: unexpected input".format(self.pos)
        if len(self.expected) == 1:
            return "at {!r}: expected {}".format(self.pos, self.expected[0])
        return "at {!r}: expected {} or {}".format(
            self.pos, ', '.join(self.expected[:-1]), self.expected[-1]
        )


class ParseError(Exception):
    def __init__(self, errors: List[ErrorItem]):
        super().__init__(errors)
        self.errors = errors

    def __str__(self) -> str:
        return ", ".join(error.msg() for error in self.errors)


class ParseResult(Generic[P, V_co]):
    def __init__(self, result: Result[P, V_co]):
        self._result = result

    def fmap(self, fn: Callable[[V_co], U]) -> "ParseResult[P, U]":
        return ParseResult(self._result.fmap(fn))

    def unwrap(self, recover: bool = False) -> V_co:
        if type(self._result) is Ok:
            return self._result.value

        if type(self._result) is Error:
            raise ParseError(
                [ErrorItem(self._result.pos, list(self._result.expected))]
            )

        repair = min(self._result.repairs.values(), key=lambda r: r.cost)
        if recover:
            return repair.value
        errors: List[ErrorItem] = []
        for item in repair.prefix:
            errors.append(ErrorItem(item.op.pos, list(item.expected)))
        errors.append(ErrorItem(repair.op.pos, list(repair.expected)))
        raise ParseError(errors)
