from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Pattern, Sequence, Tuple, TypeVar

from .core import ParseFnC, RecoveryMode
from .parser import (
    InsertValue, InsertValueC, Parser, ParserC, SatisfyC, label, satisfy
)
from .result import Result

C = TypeVar("C")


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    loc: Optional[Tuple[int, int]] = field(
        default=None, repr=False, compare=False
    )


def iter_tokens(src: str, spec: Pattern[str]) -> Iterator[Token]:
    line = 0
    col = 0
    pos = 0
    src_len = len(src)
    while pos < src_len:
        match = spec.match(src, pos=pos)
        if match is None:
            raise ValueError()
        kind = match.lastgroup
        if kind is not None:
            yield Token(kind, match.group(kind), (line, col))
        pos = match.end()

        chunk = match.group()
        nl = chunk.count("\n")
        if nl:
            line += nl
            col = len(chunk) - chunk.rfind("\n") - 1
        else:
            col += len(chunk)


def split_tokens(src: str, spec: Pattern[str]) -> List[Token]:
    return list(iter_tokens(src, spec))


class TokenC(ParserC[Sequence[Token], int, C, Token]):
    def __init__(self, k: str):
        self._k = k

    def parse_fn(
            self, stream: Sequence[Token], pos: int, ctx: C,
            rm: RecoveryMode) -> Result[int, C, Token]:
        return self.to_fn()(stream, pos, ctx, rm)

    def to_fn(self) -> ParseFnC[Sequence[Token], int, C, Token]:
        k = self._k
        return SatisfyC[Token, C](lambda t: t.kind == k).label(k).to_fn()


def token(k: str) -> Parser[Sequence[Token], int, Token]:
    return label(satisfy(lambda t: t.kind == k), k)


class TokenInsC(ParserC[Sequence[Token], int, C, Token]):
    def __init__(self, kind: str, ins_value: str):
        self._kind = kind
        self._ins_value = ins_value

    def parse_fn(
            self, stream: Sequence[Token], pos: int, ctx: C,
            rm: RecoveryMode) -> Result[int, C, Token]:
        return self.to_fn()(stream, pos, ctx, rm)

    def to_fn(self) -> ParseFnC[Sequence[Token], int, C, Token]:
        return (
            TokenC[C](self._kind) |
            InsertValueC[Sequence[Token], int, C, Token](
                Token(self._kind, self._ins_value)
            )
        ).to_fn()


def token_ins(
        kind: str, ins_value: str) -> Parser[Sequence[Token], int, Token]:
    return (
        token(kind) |
        InsertValue[Sequence[Token], int, Token](Token(kind, ins_value))
    )
