from typing import Tuple

from reparsec import Delay
from reparsec.layout import aligned, indented
from reparsec.scannerless import parse, regexp
from reparsec.sequence import eof

eol = regexp(r"\n\s*")
ows = regexp(r"\s*")
ident = regexp(r"[a-zA-Z_][a-zA-Z_0-9]*")
colon = regexp("[ \t]*:[ \t]*")

pair = Delay[str, Tuple[str, object]]()
pairs = aligned(pair).many()
value = (
    ident << (eol | eof()) |
    eol >> indented(4, (pair + pairs).fmap(lambda vs: dict([vs[0], *vs[1]])))
)
pair.define((ident << colon) + value)

parser = ows >> pairs.fmap(lambda kvs: dict(kvs)) << eof()


def loads(source: str) -> object:
    return parse(parser, source).unwrap()
