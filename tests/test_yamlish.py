from typing import List, Tuple

import pytest

from reparsec import yamlish

DATA_POSITIVE: List[Tuple[str, object]] = [
    ("key: value", {"key": "value"}),
    (
        r"""
foo: bar
baz: qux
""",
        {"foo": "bar", "baz": "qux"}
    ),
    (
        r"""
foo:
    bar: baz
    qux: quux
  """,
        {"foo": {"bar": "baz", "qux": "quux"}}
    ),
    (
        r"""
foo:
    bar: baz
qux: quux
""",
        {"foo": {"bar": "baz"}, "qux": "quux"}
    ),
]


@pytest.mark.parametrize("data, expected", DATA_POSITIVE)
def test_positive(data: str, expected: object) -> None:
    assert yamlish.parse(data) == expected
