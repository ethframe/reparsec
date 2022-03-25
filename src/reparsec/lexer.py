from dataclasses import dataclass, field
from typing import Iterator, List, Pattern, Sequence, TypeVar

from .core.state import Loc
from .output import ParseResult
from .parser import Parser, label
from .sequence import satisfy

__all__ = ("Token", "LexError", "split_tokens", "token", "token_ins", "parse")

V = TypeVar("V")


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    start: Loc = field(default=Loc(0, 0, 0), repr=False, compare=False)
    end: Loc = field(default=Loc(0, 0, 0), repr=False, compare=False)


class LexError(Exception):
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
    return list(iter_tokens(src, spec))


def token(kind: str) -> Parser[Sequence[Token], Token]:
    return label(satisfy(lambda t: t.kind == kind), kind)


def token_ins(kind: str, ins_value: str) -> Parser[Sequence[Token], Token]:
    def insert_fn(stream: Sequence[Token], pos: int) -> Token:
        loc = _loc_from_stream(stream, pos)
        return Token(kind, ins_value, loc, loc)

    return token(kind).insert_on_error(insert_fn, kind)


def parse(
        parser: Parser[Sequence[Token], V], stream: Sequence[Token],
        recover: bool = False) -> ParseResult[V, Sequence[Token]]:
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
