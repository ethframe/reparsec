from typing import Callable

from reparsec import Delay
from reparsec.scannerless import literal, parse, regexp
from reparsec.sequence import eof


def op_action(op: str) -> Callable[[int, int], int]:
    return {
        "+": lambda a, b: a + b,
        "-": lambda a, b: a - b,
        "*": lambda a, b: a * b,
    }[op]


spaces = regexp(r"\s*")
number = regexp(r"\d+").fmap(int) << spaces
mul_op = regexp(r"[*]").fmap(op_action) << spaces
add_op = regexp(r"[-+]").fmap(op_action) << spaces
l_paren = literal("(") << spaces
r_paren = literal(")") << spaces

expr = Delay[str, int]()
expr.define(
    (
        number |
        expr.between(l_paren, r_paren)
    )
    .chainl1(mul_op)
    .chainl1(add_op)
)

parser = expr << eof()


def eval(src: str) -> int:
    return parse(parser, src).unwrap()
