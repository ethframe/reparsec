# Intro

Suppose we need to parse a list of numbers separated by commas without an external lexer. This means that we should build our parser from the simplest ones.

First, we need to recognize digits. For this we will use the `satisfy` parser. It is parameterized with a predicate to test the input token.

```python
from reparsec.core import satisfy

digit = satisfy(str.isdigit)
```

Let's try it in action. Our freshly created parser have a `parse` method to parse a sequence of tokens. It returns either a result of successful parse or an error. You can get the actual value or exception with an `unwrap` method.

```python
>>> digit.parse("123").unwrap()
'1'

>>> digit.parse("a").unwrap()
Traceback (most recent call last):
  ...
reparsec.result.ParseError: at 0: unexpected input
```

So far, so good. Next, we want to parse numbers. For simplicity let's assume that a number is a sequence of one or more digits:

```python
number = digit + digit.many()
```

We use method `many` to construct parser that tries to apply original parser zero or more times, and operator `+` to sequentially apply two parsers.

```python
>>> number.parse("123").unwrap()
('1', ['2', '3'])
```

The output doesn't looks like a number yet. We need `fmap` to convert it to a number:

```python
number = (digit + digit.many()).fmap(lambda v: int(v[0] + "".join(v[1])))
```

```python
>>> number.parse("123").unwrap()
123
```

Done. Now we are ready to parse the list. The list is just a sequence of numbers separated by commas:

```python
from reparsec.core import sym

list_parser = number.sep_by(sym(","))
```

```python
>>> list_parser.parse("12,34,56").unwrap()
[12, 34, 56]
```

Success!

What if we want to allow whitespace around numbers? Let's extend the parser to accept such inputs:

```python
space = satisfy(str.isspace)
spaces = space.many()

list_parser = spaces.rseq(
    number.lseq(spaces).sep_by(sym(",") + spaces)
)
```

```python
>>> list_parser.parse(" 1 , 2 ").unwrap()
[1, 2]
```

Until before we focused on parsing valid inputs. But what if we have a string with unexpected characters in it?

```python
>>> list_parser.parse("1,a").unwrap()
Traceback (most recent call last):
  ...
reparsec.result.ParseError: at 2: unexpected input
```

The parser reported an error and provided a brief description of what was wrong with the input.

```python
>>> list_parser.parse("1a").unwrap()
[1]
```

Ouch! While reporting errors in general, in some cases our parser silently ignores the rest of the input. Let's fix this by requiring input to end right after the list using the `eof` parser:

```python
from reparsec.core import eof

list_parser = number.lseq(spaces).sep_by(
    sym(",") + spaces
).between(spaces, eof())
```

```python
>>> list_parser.parse("1a").unwrap()
Traceback (most recent call last):
  ...
reparsec.result.ParseError: at 1: expected ',' or end of file
```

Much better. Next, let's take a closer look at the errors messages:

```python
>>> list_parser.parse("1 2").unwrap()
Traceback (most recent call last):
  ...
reparsec.result.ParseError: at 2: expected ',' or end of file
```

Seems informative.

```python
>>> list_parser.parse("1,").unwrap()
Traceback (most recent call last):
  ...
reparsec.result.ParseError: at 2: unexpected input
```

This message is not very helpful. This is because the `satisfy` parser has no idea about the expected token. Let's add some labels to help it:

```python
digit = satisfy(str.isdigit).label("digit")

number = (digit + digit.many()).fmap(
    lambda v: int(v[0] + "".join(v[1]))
).label("number")

list_parser = number.lseq(spaces).sep_by(
    sym(",") + spaces
).between(spaces, eof())
```

```python
>>> list_parser.parse("1,").unwrap()
Traceback (most recent call last):
  ...
reparsec.result.ParseError: at 2: expected number
```

And now for something completely different:

```python
>>> list_parser.parse("1 2", recover=True).unwrap(recover=True)
[1]
```

The parser recovered from the error and produced a partial result. Pretty useful. However, `satisfy` again doesn't know how to fix input besides ignoring some parts of the input:

```python
>>> list_parser.parse("1,", recover=True).unwrap(recover=True)
Traceback (most recent call last):
  ...
reparsec.result.ParseError: at 2: expected number
```

We can use `recover_value` to return some value during error recovery:

``` python
from reparsec.core import recover_value

number = (digit + digit.many()).fmap(
    lambda v: int(v[0] + "".join(v[1]))
).label("number") | recover_value(0)

list_parser = number.lseq(spaces).sep_by(
    sym(",") + spaces
).between(spaces, eof())
```

```python
>>> list_parser.parse("1,", recover=True).unwrap(recover=True)
[1, 0]
```

The parser is even capable of fixing multiple errors in the input:

```python
>>> list_parser.parse("1,,,2 3", recover=True).unwrap(recover=True)
[1, 0, 0, 2]
```

And what if we want to show them to user?

```python
>>> list_parser.parse("1,,,2 3", recover=True).unwrap()
Traceback (most recent call last):
  ...
reparsec.result.ParseError: at 2: expected number, at 3: expected number, at 6: expected end of file
```

The final parser definition should look like this:

```python
from reparsec.core import recover_value, satisfy, sym, eof

digit = satisfy(str.isdigit).label("digit")

number = (digit + digit.many()).fmap(
    lambda v: int(v[0] + "".join(v[1]))
).label("number") | recover_value(0)

space = satisfy(str.isspace).many()

list_parser = space.rseq(
    number.sep_by(space.rseq(sym(",")))
).lseq(space).lseq(eof())
```
