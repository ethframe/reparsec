from dataclasses import dataclass
from typing import Callable, Generic, List, Optional, TypeVar

from .core.result import BaseRepair, Error, Ok, RepairOp, Result, Skip
from .core.state import Loc

S = TypeVar("S")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")


@dataclass
class ErrorItem:
    loc: Loc
    loc_str: str
    expected: List[str]
    op: Optional[RepairOp] = None

    def msg(self) -> str:
        res = "at {}: ".format(self.loc_str)
        if not self.expected:
            res += "unexpected input"
        elif len(self.expected) == 1:
            res += "expected {}".format(self.expected[0])
        else:
            res += "expected {} or {}".format(
                ', '.join(self.expected[:-1]), self.expected[-1]
            )
        if self.op is not None:
            if type(self.op) is Skip:
                repair = "skipped {} {}".format(
                    self.op.count, "token" if self.op.count == 1 else "tokens"
                )
            else:
                repair = "inserted {}".format(self.op.label)
            res += " (" + repair + ")"
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
                    self._result.loc,
                    self._fmt_loc(self._result.loc),
                    list(self._result.expected),
                )
            ])

        repair: Optional[BaseRepair[V_co, S]] = self._result.selected
        if repair is None:
            repair = self._result.pending
            if repair is None:
                raise RuntimeError("Invalid recovered result")
        if recover:
            return repair.value
        errors: List[ErrorItem] = []
        for item in repair.prefix:
            errors.append(
                ErrorItem(
                    item.op.loc, self._fmt_loc(item.op.loc),
                    list(item.expected), item.op
                )
            )
        errors.append(
            ErrorItem(
                repair.op.loc, self._fmt_loc(repair.op.loc),
                list(repair.expected), repair.op
            )
        )
        raise ParseError(errors)
