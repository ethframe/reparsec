from typing import Tuple

from reparsec.layout import indented, same
from reparsec.parser import Delay, Parser, alt
from reparsec.scannerless import regexp, run
from reparsec.sequence import eof

eol = regexp(r"\n\s*")
ows = regexp(r"\s*")
ident = regexp(r"[a-zA-Z_][a-zA-Z_0-9]*")
pair: Delay[str, Tuple[str, object]] = Delay()
value: Parser[str, object] = alt(
    ident << eol.maybe(),
    (eol >> indented(4, pair.many())).fmap(lambda kvs: dict(kvs))
)
pair.define((same(ident) << regexp("[ \t]*:[ \t]*")) + value)

parser = ows >> pair.many().fmap(lambda kvs: dict(kvs)) << eof()


def loads(source: str) -> object:
    return run(parser, source).unwrap()
