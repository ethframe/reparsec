"""
Simple lexer based on regular expressions.
"""

from dataclasses import dataclass, field
from typing import Iterator, List, Pattern, Sequence, TypeVar

from .core.types import Loc
from .parser import Parser, TupleParser, label
from .sequence import satisfy
from .types import ParseResult

__all__ = ("Token", "LexError", "split_tokens", "token", "token_ins", "parse")

V = TypeVar("V")


@dataclass(frozen=True)
class Token:
    """
    Token

    :param kind: Name of capture group from lexer spec
    :param value: Value of token
    :param start: Start location
    :param end: End location
    """

    kind: str
    value: str
    start: Loc = field(default=Loc(0, 0, 0), repr=False, compare=False)
    end: Loc = field(default=Loc(0, 0, 0), repr=False, compare=False)


class LexError(Exception):
    """
    Exception that is raised if a lexer was unable to process the input.

    :param loc: Location of error
    """

    def __init__(self, loc: Loc):
        super().__init__(loc)
        self.loc = loc

    def __str__(self) -> str:
        return "Lexing error at {}:{}".format(
            self.loc.line + 1, self.loc.col + 1
        )


def iter_tokens(src: str, spec: Pattern[str]) -> Iterator[Token]:
    pos = 0
    line = 0
    col = 0
    loc = Loc(0, 0, 0)
    src_len = len(src)
    while pos < src_len:
        match = spec.match(src, pos=pos)
        if match is None:
            raise LexError(loc)

        end = match.end()
        nl = src.count("\n", pos, end)
        if nl:
            line += nl
            col = end - src.rfind("\n", pos, end) - 1
        else:
            col += end - pos
        end_loc = Loc(end, line, col)

        kind = match.lastgroup
        if kind is not None:
            yield Token(kind, match.group(kind), loc, end_loc)

        pos = end
        loc = end_loc


def split_tokens(src: str, spec: Pattern[str]) -> List[Token]:
    """
    Splits input string into list of tokens.

    The lexer specification is a compiled regular expressions with named
    capture groups for individual tokens. Only the last capture group is taken
    into account. If no capture group matches, the token is skipped.

    >>> from reparsec.lexer import split_tokens
    >>> import re

    >>> spec = re.compile(r"(?P<num>[0-9]+)|(?P<op>[+])|\\s+")

    >>> split_tokens("1 + 2 + 3", spec)  # doctest: +NORMALIZE_WHITESPACE
    [Token(kind='num', value='1'), Token(kind='op', value='+'),
     Token(kind='num', value='2'), Token(kind='op', value='+'),
     Token(kind='num', value='3')]

    :param src: Input
    :param spec: Compiled regular expression
    """
    return list(iter_tokens(src, spec))


def token(kind: str) -> TupleParser[Sequence[Token], Token]:
    """
    Parses token of the specified kind and returns the token.

    >>> from reparsec.lexer import parse, split_tokens, token
    >>> import re

    >>> spec = re.compile(r"(?P<num>[0-9]+)|(?P<op>[+])")
    >>> parser = token("num")

    >>> parse(parser, split_tokens("1", spec)).unwrap()
    Token(kind='num', value='1')

    >>> parse(parser, split_tokens("+", spec)).unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 1:1: expected num

    :param kind: Kind of expected token
    """

    return label(satisfy(lambda t: t.kind == kind), kind)


def token_ins(
        kind: str, ins_value: str) -> TupleParser[Sequence[Token], Token]:
    """
    Parses token of the specified kind and returns the token. When error
    recovery is enabled, inserts ``Token(kind=kind, value=ins_value)`` on
    error.

    >>> from reparsec.lexer import parse, split_tokens, token_ins
    >>> import re

    >>> spec = re.compile(r"(?P<num>[0-9]+)|(?P<op>[+])")
    >>> parser = token_ins("num", "0")

    >>> parse(
    ...     parser, split_tokens("+", spec), recover=True
    ... ).unwrap(recover=True)
    Token(kind='num', value='0')

    :param kind: Kind of expected token
    :param ins_value: Value for inserted token
    """

    def value_fn(stream: Sequence[Token], pos: int) -> Token:
        loc = _loc_from_stream(stream, pos)
        return Token(kind, ins_value, loc, loc)

    return token(kind).recover_with_fn(value_fn, kind)


def parse(
        parser: Parser[Sequence[Token], V], stream: Sequence[Token],
        recover: bool = False) -> ParseResult[V, Sequence[Token]]:
    """
    Wrapper around :meth:`reparsec.Parser.parse` that enables line and column
    tracking.

    :param parser: Parser to run
    :param stream: Stream of tokens to parse
    :param recover: Flag to enable error recovery
    """

    return parser.parse(
        stream, recover,
        get_loc=lambda _, s, p: _loc_from_stream(s, p),
        fmt_loc=lambda l: "{}:{}".format(l.line + 1, l.col + 1)
    )


def _loc_from_stream(stream: Sequence[Token], pos: int) -> Loc:
    if pos < len(stream):
        return stream[pos].start
    elif stream:
        return stream[-1].end
    return Loc(pos, 0, 0)
