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

## Example

With `reparsec`, simple arithmetic expression parser and evaluator could be written like this:

```python
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
```

This parser can:

* evaluate an expression:
  ```python
  >>> parser.parse("1 + 2 * (3 + 4)").unwrap()
  15
  ```
* report first syntax error:
  ```python
  >>> parser.parse("1 + 2 * * (3 + 4 5)").unwrap()
  Traceback (most recent call last):
    ...
  reparsec.types.ParseError: at 8: expected '('
  ```
* attempt to recover and report multiple syntax errors:
  ```python
  >>> parser.parse("1 + 2 * * (3 + 4 5)", recover=True).unwrap()
  Traceback (most recent call last):
    ...
  reparsec.types.ParseError: at 8: expected '(' (skipped 2 tokens), at 17: expected ')' (skipped 1 token)
  ```
* automatically repair input and return some result:
  ```python
  >>> parser.parse("1 + 2 * * (3 + 4 5)", recover=True).unwrap(recover=True)
  15
  ```
* track line and column numbers:
  ```python
  >>> parse(parser, """1 +
  ... 2 * * (
  ... 3 + 4 5)""", recover=True).unwrap()
  Traceback (most recent call last):
    ...
  reparsec.types.ParseError: at 2:5: expected '(' (skipped 2 tokens), at 3:7: expected ')' (skipped 1 token)
  ```

More examples:
  * [JSON parser](https://github.com/ethframe/reparsec/blob/master/tests/parsers/json.py)
  * [Scannerless JSON parser](https://github.com/ethframe/reparsec/blob/master/tests/parsers/json_scannerless.py)
