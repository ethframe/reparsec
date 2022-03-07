from typing import List, Tuple

import pytest

from reparsec import Parser, run
from reparsec.primitive import InsertValue
from reparsec.sequence import sym, eof

a = sym("a")
b = sym("b")
c = sym("c")
comma = sym(",")

ab = (a + b).fmap("".join)
cab = (c + ab).fmap("".join)
aba = (ab + a).fmap("".join)
abaa = (aba + a).fmap("".join)
aaba = (a + aba).fmap("".join)
caba = (c + aba).fmap("".join)


DATA_RECOVERY: List[Tuple[Parser[str, object], str, object]] = [
    (ab, "ab", "ab"),
    (ab, "_ab", "ab"),
    (ab, "_a_b", "ab"),
    (ab, "b", "ab"),
    (ab, "a", "ab"),
    (ab, "_a", "ab"),
    (ab | b, "ab", "ab"),
    (ab | b, "b", "b"),
    (ab | b, "", "b"),
    (ab | b, "a", "ab"),
    (ab | b, "_ab", "ab"),
    (ab | b, "a_b", "ab"),
    (ab | b, "_a_b", "ab"),
    (ab.maybe(), "ab", "ab"),
    (ab.maybe(), "", None),
    (ab.maybe(), "b", None),
    (ab.maybe(), "_ab", None),
    (ab.maybe(), "a", "ab"),
    (ab.sep_by(comma), "ab,ab,ab", ["ab", "ab", "ab"]),
    (ab.sep_by(comma), "ab,ab,ab,", ["ab", "ab", "ab", "ab"]),
    (ab.sep_by(comma), "ab,ab,,ab", ["ab", "ab", "ab", "ab"]),
    (ab.sep_by(comma), "ab,abab", ["ab", "ab"]),
    (ab.sep_by(comma), "ab,a,ab", ["ab", "ab", "ab"]),
    (ab.sep_by(comma), "ab,b,ab", ["ab", "ab", "ab"]),
    (ab | a, "ab", "ab"),
    (ab.attempt() | a, "ab", "ab"),
    (ab | a, "a", "ab"),
    (ab.attempt() | a, "a", "a"),
    (ab | InsertValue("b"), "ab", "ab"),
    (ab | InsertValue("b"), "_ab", "ab"),
    (ab | InsertValue("b"), "a", "ab"),
    (ab | InsertValue("b"), "b", "ab"),
    (ab | InsertValue("b"), "", "b"),
    (ab | cab, "ab", "ab"),
    (ab | cab, "cab", "cab"),
    (ab | cab, "b", "ab"),
    (cab | ab, "b", "ab"),
    ((ab | cab) << a, "", "ab"),
    ((cab | ab) << a, "", "ab"),
    (abaa | caba, "b", "abaa"),
    (caba | abaa, "b", "abaa"),
    (aaba | caba, "b", "aaba"),
    (caba | aaba, "b", "caba"),
]


@pytest.mark.parametrize("parser, data, expected", DATA_RECOVERY)
def test_recovery(
        parser: Parser[str, object], data: str, expected: object) -> None:
    result = run(parser << eof(), data, recover=True)
    assert result.unwrap(recover=True) == expected
