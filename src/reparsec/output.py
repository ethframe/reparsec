from dataclasses import dataclass
from typing import Callable, Generic, List, Optional, TypeVar

from .core.result import BaseRepair, Error, Insert, Ok, RepairOp, Result, Skip
from .core.state import Loc

S = TypeVar("S")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")


@dataclass
class ErrorItem:
    loc: str
    expected: List[str]
    repair: Optional[str] = None

    def msg(self) -> str:
        res = "at {}: ".format(self.loc)
        if not self.expected:
            res += "unexpected input"
        elif len(self.expected) == 1:
            res += "expected {}".format(self.expected[0])
        else:
            res += "expected {} or {}".format(
                ', '.join(self.expected[:-1]), self.expected[-1]
            )
        if self.repair is not None:
            res += " (" + self.repair + ")"
        return res


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
                    list(self._result.expected),
                )
            ])

        def op_to_str(op: RepairOp) -> str:
            if type(op) is Skip:
                return "skipped {} {}".format(
                    op.count, "token" if op.count == 1 else "tokens"
                )
            elif type(op) is Insert:
                return "inserted {}".format(op.label)
            raise RuntimeError()

        repair: Optional[BaseRepair[V_co, S]] = self._result.selected
        if repair is None:
            repair = self._result.pending[0]
        if recover:
            return repair.value
        errors: List[ErrorItem] = []
        for item in repair.prefix:
            errors.append(
                ErrorItem(
                    self._fmt_loc(item.op.loc), list(item.expected),
                    op_to_str(item.op)
                )
            )
        errors.append(
            ErrorItem(
                self._fmt_loc(repair.op.loc), list(repair.expected),
                op_to_str(repair.op)
            )
        )
        raise ParseError(errors)
