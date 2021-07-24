from .core import Parser, label, satisfy
from typing import Iterator, List, NamedTuple, Pattern


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
