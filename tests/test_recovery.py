from typing import List, Tuple

import pytest

from reparsec import Parser
from reparsec.sequence import eof, sym

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
    (ab.bind(lambda s: a.fmap(lambda x: s + x)), "aba", "aba"),
    (ab.bind(lambda s: a.fmap(lambda x: s + x)), "aa", "aba"),
    (ab.bind(lambda s: a.fmap(lambda x: s + x)), "_a_a", "aba"),
    (ab | b, "ab", "ab"),
    (ab | b, "b", "b"),
    (ab | b, "", "ab"),
    (ab | b, "a", "ab"),
    (ab | b, "_ab", "ab"),
    (ab | b, "a_b", "ab"),
    (ab | b, "_a_b", "ab"),
    (ab.maybe(), "ab", "ab"),
    (ab.maybe(), "", None),
    (ab.maybe(), "b", None),
    (ab.maybe(), "_ab", None),
    (ab.maybe(), "a", "ab"),
    (ab.many(), "a", ["ab"]),
    (ab.many(), "aa", ["ab", "ab"]),
    (ab.many(), "ac", ["ab"]),
    (ab.sep_by(comma), "ab,ab,ab", ["ab", "ab", "ab"]),
    (ab.sep_by(comma), "ab,ab,ab,", ["ab", "ab", "ab", "ab"]),
    (ab.sep_by(comma), "ab,ab,,ab", ["ab", "ab", "ab"]),
    (ab.sep_by(comma), "ab,abab", ["ab", "ab"]),
    (ab.sep_by(comma), "ab,a,ab", ["ab", "ab", "ab"]),
    (ab.sep_by(comma), "ab,b,ab", ["ab", "ab", "ab"]),
    (ab | a, "ab", "ab"),
    (ab.attempt() | a, "ab", "ab"),
    (ab | a, "a", "ab"),
    (ab.attempt() | a, "a", "a"),
    ((a + b.attempt()).fmap("".join), "a", "ab"),
    ((a + b.attempt()).fmap("".join), "b", "ab"),
    (ab.recover_with("b"), "ab", "ab"),
    (ab.recover_with("b"), "_ab", "ab"),
    (ab.recover_with("b"), "a", "ab"),
    (ab.recover_with("b"), "b", "ab"),
    (ab.recover_with("b"), "", "b"),
    (ab.recover_with_fn(lambda _, __: "b"), "", "b"),
    (ab | cab, "ab", "ab"),
    (ab | cab, "cab", "cab"),
    (ab | cab, "b", "ab"),
    (cab | ab, "b", "cab"),
    ((ab | cab) << a, "", "ab"),
    ((cab | ab) << a, "", "cab"),
    (abaa | caba, "b", "abaa"),
    (caba | abaa, "b", "caba"),
    (aaba | caba, "b", "aaba"),
    (caba | aaba, "b", "caba"),
]


@pytest.mark.parametrize("parser, data, expected", DATA_RECOVERY)
def test_recovery(
        parser: Parser[str, object], data: str, expected: object) -> None:
    result = (parser << eof()).parse(data, recover=True)
    assert result.unwrap(recover=True) == expected
