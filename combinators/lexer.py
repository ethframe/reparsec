from typing import Iterator, List, NamedTuple, Pattern

from .core import Parser, insert, label, satisfy


class Token(NamedTuple):
    kind: str
    value: str


def iter_tokens(src: str, spec: Pattern[str]) -> Iterator[Token]:
    pos = 0
    src_len = len(src)
    while pos < src_len:
        match = spec.match(src, pos=pos)
        if match is None:
            raise ValueError()
        kind = match.lastgroup
        if kind is not None:
            yield Token(kind, match.group(kind))
        pos = match.end()


def split_tokens(src: str, spec: Pattern[str]) -> List[Token]:
    return list(iter_tokens(src, spec))


def token(k: str) -> Parser[Token, Token]:
    return label(satisfy(lambda t: t.kind == k), k)


def token_ins(kind: str, ins_value: str) -> Parser[Token, Token]:
    return token(kind) | insert(Token(kind, ins_value))
