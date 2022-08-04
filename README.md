[![Build status](https://github.com/ethframe/reparsec/workflows/Tests/badge.svg?branch=master)](https://github.com/ethframe/reparsec/actions?query=workflow%3ATests+branch%3Amaster+event%3Apush)
[![codecov.io](https://codecov.io/gh/ethframe/reparsec/branch/master/graph/badge.svg)](https://codecov.io/gh/ethframe/reparsec)
[![Documentation status](https://readthedocs.org/projects/reparsec/badge/?version=latest)](https://reparsec.readthedocs.io/en/latest/?badge=latest)
[![PyPI version](https://img.shields.io/pypi/v/reparsec)](https://pypi.org/project/reparsec)

# reparsec

Small parsec-like parser combinators library with semi-automatic error recovery.

## Installation

```
pip install reparsec
```

## Usage

* [Tutorial](https://reparsec.readthedocs.io/en/latest/pages/tutorial.html)
* [Documentation](https://reparsec.readthedocs.io/en/latest/index.html)

Simple arithmetic expression parser and calculator:

```python
from typing import Callable

from reparsec import Delay
from reparsec.scannerless import literal, regexp
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
value = number | expr.between(l_paren, r_paren)
expr.define(value.chainl1(mul_op).chainl1(add_op))

parser = expr << eof()

print(parser.parse("1 + 2 * (3 + 4)").unwrap())
```

Output:

```
15
```

Out-of-the-box error recovery:

```python
result = parser.parse("1 + 2 * * (3 + 4)", recover=True)

try:
    result.unwrap()
except ParseError as e:
    print(e)

print(result.unwrap(recover=True))
```

Output:

```
at 8: expected '(' (skipped 2 tokens)
15
```

More examples:
  * [JSON parser](https://github.com/ethframe/reparsec/blob/master/tests/parsers/json.py)
  * [Scannerless JSON parser](https://github.com/ethframe/reparsec/blob/master/tests/parsers/json_scannerless.py)
