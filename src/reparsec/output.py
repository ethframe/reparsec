from abc import abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, List, Optional, TypeVar

from .core.result import RepairOp, Skip
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

    @property
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
        return ", ".join(error.msg for error in self.errors)


class ParseResult(Generic[V_co, S]):
    @abstractmethod
    def fmap(self, fn: Callable[[V_co], U]) -> "ParseResult[U, S]":
        ...

    @abstractmethod
    def unwrap(self, recover: bool = False) -> V_co:
        ...
