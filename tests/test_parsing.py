from typing import List, Sequence

import pytest

from reparsec.output import ParseError
from reparsec.parser import Parser, run
from reparsec.primitive import Pure, PureFn
from reparsec.sequence import digit, letter, sym

a = sym("a")
b = sym("b")

maybe_a_b = (a.maybe().fmap(str) + b).fmap("".join)

ident = (
    (letter | sym("_")) + (letter | digit | sym("_")).many()
).fmap(lambda v: v[0] + "".join(v[1]))

empty_fst = (Pure[Sequence[str], str]("a") | b)
empty_snd = (a | Pure("b"))

bind_letter = letter.bind(lambda l: digit if l == "d" else letter) | Pure("!")

attempt_seq = (a + b).fmap(lambda v: v[0] + v[1]).attempt() | Pure("!")

chains = letter.chainl1(
    sym(">").rseq(Pure(lambda a, b: f"({a}>{b})"))
).chainr1(
    sym("<").rseq(Pure(lambda a, b: f"({a}<{b})"))
)

DATA_POSITIVE = [
    (Pure("a"), "", "a"),
    (PureFn(lambda: "a"), "", "a"),
    (a.lseq(b), "ab", "a"),
    (a.rseq(b), "ab", "b"),
    (maybe_a_b, "ab", "ab"),
    (maybe_a_b, "b", "Noneb"),
    (ident, "a", "a"),
    (ident, "ab", "ab"),
    (ident, "a_b", "a_b"),
    (ident, "a0_b", "a0_b"),
    (ident, "_a0_b", "_a0_b"),
    (ident, "_a0_b.", "_a0_b"),
    (empty_fst, "a", "a"),
    (empty_fst, "b", "b"),
    (empty_fst, "c", "a"),
    (empty_snd, "a", "a"),
    (empty_snd, "b", "b"),
    (empty_snd, "c", "b"),
    (bind_letter, "ab", "b"),
    (bind_letter, "d0", "0"),
    (bind_letter, "00", "!"),
    (attempt_seq, "ab", "ab"),
    (attempt_seq, "ac", "!"),
    (chains, "a", "a"),
    (chains, "a>b", "(a>b)"),
    (chains, "a<b", "(a<b)"),
    (chains, "a>b>c", "((a>b)>c)"),
    (chains, "a<b<c", "(a<(b<c))"),
    (chains, "a>b<c", "((a>b)<c)"),
    (chains, "a<b>c", "(a<(b>c))"),
    (chains, "a>b<c>d", "((a>b)<(c>d))"),
    (chains, "a<b>c<d", "(a<((b>c)<d))"),
]


@pytest.mark.parametrize("parser, data, value", DATA_POSITIVE)
def test_positive(parser: Parser[str, str], data: str, value: str) -> None:
    assert run(parser, data).unwrap() == value


DATA_NEGATIVE = [
    (ident, "0", ["letter", "'_'"]),
]


@pytest.mark.parametrize("parser, data, expected", DATA_NEGATIVE)
def test_negative(
        parser: Parser[str, str], data: str, expected: List[str]) -> None:
    with pytest.raises(ParseError) as err:
        run(parser, data).unwrap()
    assert err.value.errors[0].expected == expected
