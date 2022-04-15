from typing import List, Tuple

import pytest

from reparsec import Parser
from reparsec.sequence import sym

a = sym("a")
b = sym("b")
c = sym("c")
d = sym("d")
e = sym("e")
f = sym("f")
g = sym("g")
h = sym("h")
comma = sym(",")

DATA_POSITIVE: List[
    Tuple[Parser[str, Tuple[str, ...]], str, Tuple[str, ...]]
] = [
    (a.skip(comma).then(b), "a,b", ("a", "b")),
    (a.skip(comma).then(b).skip(comma), "a,b,", ("a", "b")),
    (a.skip(comma).then(b).skip(comma).then(c), "a,b,c", ("a", "b", "c")),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma),
        "a,b,c,",
        ("a", "b", "c")
    ),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma).then(d),
        "a,b,c,d",
        ("a", "b", "c", "d")
    ),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma).then(d)
        .skip(comma),
        "a,b,c,d,",
        ("a", "b", "c", "d")
    ),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma).then(d)
        .skip(comma).then(e),
        "a,b,c,d,e",
        ("a", "b", "c", "d", "e")
    ),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma).then(d)
        .skip(comma).then(e).skip(comma),
        "a,b,c,d,e,",
        ("a", "b", "c", "d", "e")
    ),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma).then(d)
        .skip(comma).then(e).skip(comma).then(f),
        "a,b,c,d,e,f",
        ("a", "b", "c", "d", "e", "f")
    ),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma).then(d)
        .skip(comma).then(e).skip(comma).then(f).skip(comma),
        "a,b,c,d,e,f,",
        ("a", "b", "c", "d", "e", "f")
    ),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma).then(d)
        .skip(comma).then(e).skip(comma).then(f).skip(comma).then(g),
        "a,b,c,d,e,f,g",
        ("a", "b", "c", "d", "e", "f", "g")
    ),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma).then(d)
        .skip(comma).then(e).skip(comma).then(f).skip(comma).then(g)
        .skip(comma),
        "a,b,c,d,e,f,g,",
        ("a", "b", "c", "d", "e", "f", "g")
    ),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma).then(d)
        .skip(comma).then(e).skip(comma).then(f).skip(comma).then(g)
        .skip(comma).then(h),
        "a,b,c,d,e,f,g,h",
        ("a", "b", "c", "d", "e", "f", "g", "h")
    ),
    (
        a.skip(comma).then(b).skip(comma).then(c).skip(comma).then(d)
        .skip(comma).then(e).skip(comma).then(f).skip(comma).then(g)
        .skip(comma).then(h).skip(comma),
        "a,b,c,d,e,f,g,h,",
        ("a", "b", "c", "d", "e", "f", "g", "h")
    ),
    (a.then(b).apply(lambda a, b: (b, a)), "ab", ("b", "a")),
    (
        a.then(b).then(c).apply(lambda a, b, c: (c, b, a)),
        "abc",
        ("c", "b", "a")
    ),
    (
        a.then(b).then(c).then(d).apply(lambda a, b, c, d: (d, c, b, a)),
        "abcd",
        ("d", "c", "b", "a")
    ),
    (
        a.then(b).then(c).then(d).then(e)
        .apply(lambda a, b, c, d, e: (e, d, c, b, a)),
        "abcde",
        ("e", "d", "c", "b", "a")
    ),
    (
        a.then(b).then(c).then(d).then(e).then(f)
        .apply(lambda a, b, c, d, e, f: (f, e, d, c, b, a)),
        "abcdef",
        ("f", "e", "d", "c", "b", "a")
    ),
    (
        a.then(b).then(c).then(d).then(e).then(f).then(g)
        .apply(lambda a, b, c, d, e, f, g: (g, f, e, d, c, b, a)),
        "abcdefg",
        ("g", "f", "e", "d", "c", "b", "a")
    ),
    (
        a.then(b).then(c).then(d).then(e).then(f).then(g).then(h)
        .apply(lambda a, b, c, d, e, f, g, h: (h, g, f, e, d, c, b, a)),
        "abcdefgh",
        ("h", "g", "f", "e", "d", "c", "b", "a")
    ),
]


@pytest.mark.parametrize("parser, data, value", DATA_POSITIVE)
def test_positive(parser: Parser[str, str], data: str, value: str) -> None:
    assert parser.parse(data).unwrap() == value
