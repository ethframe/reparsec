
from typing import Tuple

from .parser import (
    Ctx, DelayC, ParserC, Pos, RegexpC, SlEofC, alt, indented, same, sl_run_c
)


def get_level(_: str, pos: Pos) -> int:
    return pos[2]


eol = RegexpC[Ctx](r"\n\s*")
ows = RegexpC[Ctx](r"\s*")
ident = RegexpC[Ctx](r"[a-zA-Z_][a-zA-Z_0-9]*")
pair: DelayC[str, Pos, Ctx, Tuple[str, object]] = DelayC()
value: ParserC[str, Pos, Ctx, object] = alt(
    ident << eol.maybe(),
    (eol >> indented(4, pair.many(), get_level)).fmap(lambda kvs: dict(kvs))
)
pair.define((same(ident, get_level) << RegexpC[Ctx]("[ \t]*:[ \t]*")) + value)

parser = ows >> pair.many().fmap(lambda kvs: dict(kvs)) << SlEofC[Ctx]()


def parse(source: str) -> object:
    return sl_run_c(parser, source, 0).unwrap()
