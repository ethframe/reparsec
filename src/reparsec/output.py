from abc import abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, List, Optional, TypeVar

from .core.result import RepairOp, Skip
from .core.types import Loc

S = TypeVar("S")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")


@dataclass
class ErrorItem:
    """
    Description of a single parse error.

    :param loc: Location of the error
    :param loc_str: String representation of the location
    :param expected: List of expected tokens descriptions
    :param op: Input modification that was applied to recover from the error
    """

    loc: Loc
    loc_str: str
    expected: List[str]
    op: Optional[RepairOp] = None

    @property
    def msg(self) -> str:
        """
        Human-readable description of the error.
        """

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
    """
    Exception that is raised if a parser was unable to parse the input.

    :param errors: List of errors
    """

    def __init__(self, errors: List[ErrorItem]):
        super().__init__(errors)
        self.errors = errors

    def __str__(self) -> str:
        return ", ".join(error.msg for error in self.errors)


class ParseResult(Generic[V_co, S]):
    """
    Result of the parsing.
    """

    @abstractmethod
    def fmap(self, fn: Callable[[V_co], U]) -> "ParseResult[U, S]":
        """
        Transforms :class:`ParseResult`\\[``V_co``, ``S``] into
        :class:`ParseResult`\\[``U``, ``S``] by applying `fn` to value.

        :param fn: Function to apply to value
        """

    @abstractmethod
    def unwrap(self, recover: bool = False) -> V_co:
        """
        Returns parsed value if there is one. Otherwise throws
        :exc:`ParseError`.

        :param recover: Flag to enable error recovery
        :raise: :exc:`ParseError`
        """
