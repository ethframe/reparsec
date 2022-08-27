"""
Core parser API.
"""

from abc import abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, List, Optional, TypeVar

from .core.parser import ParseObj
from .core.repair import RepairOp, Skip
from .core.result import Error, Ok, Result
from .core.types import Ctx, Loc

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
A_co = TypeVar("A_co", covariant=True)
B = TypeVar("B")


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


class ParseResult(Generic[A_co, S]):
    """
    Result of the parsing.
    """

    @abstractmethod
    def fmap(self, fn: Callable[[A_co], B]) -> "ParseResult[B, S]":
        """
        Transforms :class:`ParseResult`\\[``A_co``, ``S``] into
        :class:`ParseResult`\\[``B``, ``S``] by applying `fn` to value.

        :param fn: Function to apply to value
        """

    @abstractmethod
    def unwrap(self, recover: bool = False) -> A_co:
        """
        Returns parsed value if there is one. Otherwise throws
        :exc:`ParseError`.

        :param recover: Flag to enable error recovery
        :raise: :exc:`ParseError`
        """


def _get_loc(loc: Loc, stream: S, pos: int) -> Loc:
    return Loc(pos, 0, 0)


def _fmt_loc(loc: Loc) -> str:
    return repr(loc.pos)


class ParserParseObj(ParseObj[S_contra, A_co]):
    def parse(
            self, stream: S_contra, recover: bool = False, *,
            max_insertions: int = 5,
            get_loc: Callable[[Loc, S_contra, int], Loc] = _get_loc,
            fmt_loc: Callable[[Loc], str] = _fmt_loc
    ) -> ParseResult[A_co, S_contra]:
        """
        Parses input.

        :param stream: Input to parse
        :param recover: Flag to enable error recovery
        :param max_insertions: Maximal number of token insertions in a row
            during error recovery
        :param get_loc: Function that constructs new ``Loc`` from a previous
            ``Loc``, a stream, and position in the stream
        :param fmt_loc: Function that converts ``Loc`` to string
        """

        ctx = Ctx(0, Loc(0, 0, 0), get_loc)
        if recover:
            result = self.parse_fn(
                stream, 0, ctx, max_insertions, max_insertions
            )
        else:
            result = self.parse_fast_fn(stream, 0, ctx)
        return _ParseResult(result, fmt_loc)


class _ParseResult(ParseResult[A_co, S]):
    def __init__(self, result: Result[A_co, S], fmt_loc: Callable[[Loc], str]):
        self._result = result
        self._fmt_loc = fmt_loc

    def fmap(self, fn: Callable[[A_co], B]) -> ParseResult[B, S]:
        return _ParseResult(self._result.fmap(fn), self._fmt_loc)

    def unwrap(self, recover: bool = False) -> A_co:
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

        if not self._result.repairs:
            raise ParseError([
                ErrorItem(
                    self._result.loc,
                    self._fmt_loc(self._result.loc),
                    list(self._result.expected)
                )
            ])
        repair = min(
            self._result.repairs, key=lambda r: (r.cost, -r.pos, r.auto)
        )
        if recover:
            return repair.value
        errors = [
            ErrorItem(
                item.loc, self._fmt_loc(item.loc), list(item.expected), item.op
            )
            for item in repair.ops
        ]
        raise ParseError(errors)
