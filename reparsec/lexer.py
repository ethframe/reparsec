from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Pattern, Tuple

from .parser import Parser, label, satisfy, recover_value


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


def token(k: str) -> Parser[Token, Token]:
    return label(satisfy(lambda t: t.kind == k), k)


def token_ins(kind: str, ins_value: str) -> Parser[Token, Token]:
    return token(kind) | recover_value(Token(kind, ins_value))
