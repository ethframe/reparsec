# Tutorial

Suppose we need to parse a list of numbers separated by commas without an
external lexer. This means that we should build our parser from the simplest
ones.

## Parsing numbers

First, we need to recognize digits. For this we will use the `satisfy` parser.
It is parameterized with a predicate to test the input token.

```python
>>> from reparsec.sequence import satisfy

>>> digit = satisfy(str.isdigit)

```

Let's try it in action. We can use the `parse` method of our freshly created
parser to parse a string. It returns either a result of successful parse or an
error. You can get the actual value or exception with an `unwrap` method:

```python
>>> digit.parse("123").unwrap()
'1'

>>> digit.parse("a").unwrap()
Traceback (most recent call last):
  ...
reparsec.output.ParseError: at 0: unexpected input

```

So far, so good. Next, we want to parse numbers. For simplicity let's assume
that a number is a sequence of one or more digits:

```python
>>> digits = digit + digit.many()

```

We use method `many` to construct parser that tries to apply original parser
zero or more times, and operator `+` to sequentially apply two parsers.

```python
>>> digits.parse("123").unwrap()
('1', ['2', '3'])

```

The output doesn't looks like a number yet. We need `fmap` to convert it to a
number:

```python
>>> number = digits.fmap(lambda v: int(v[0] + "".join(v[1])))

>>> number.parse("123").unwrap()
123

```

## Parsing lists

Now we are ready to parse the list. The list is just a sequence of numbers
separated by commas. To parse a single comma we will use the `sym` parser,
which is parameterized with expected character. Parsers for sequences with
separators are usually constructed using the `sep_by` combinator:

```python
>>> from reparsec.sequence import sym

>>> list_parser = number.sep_by(sym(","))

>>> list_parser.parse("12,34,56").unwrap()
[12, 34, 56]

```

Success!

## Allowing whitespace

What if we want to allow whitespace around numbers? Let's extend the parser to
accept such inputs:

```python
>>> space = satisfy(str.isspace)
>>> spaces = space.many()

>>> number = digits.fmap(lambda v: int(v[0] + "".join(v[1]))) << spaces
>>> comma = sym(",") << spaces

>>> list_parser = spaces >> number.sep_by(comma)

>>> list_parser.parse(" 1 , 2 ").unwrap()
[1, 2]

```

## Testing incorrect inputs

Until before we focused on parsing valid inputs. But what if we have a string
with unexpected characters in it?

```python
>>> list_parser.parse("1,a").unwrap()
Traceback (most recent call last):
  ...
reparsec.output.ParseError: at 2: unexpected input

```

The parser reported an error and provided a brief description of what was wrong
with the input.

```python
>>> list_parser.parse("1a").unwrap()
[1]

```

Ouch! While reporting errors in general, in some cases our parser silently
ignores the rest of the input. Let's fix this by requiring input to end right
after the list using the `eof` parser:

```python
>>> from reparsec.sequence import eof

>>> list_parser = spaces >> number.sep_by(comma) << eof()

>>> list_parser.parse("1a").unwrap()
Traceback (most recent call last):
  ...
reparsec.output.ParseError: at 1: expected ',' or end of file

```

Much better.

## Improving error reporting

Let's take a closer look at the errors messages:

```python
>>> list_parser.parse("1 2").unwrap()
Traceback (most recent call last):
  ...
reparsec.output.ParseError: at 2: expected ',' or end of file

```

Seems informative.

```python
>>> list_parser.parse("1,").unwrap()
Traceback (most recent call last):
  ...
reparsec.output.ParseError: at 2: unexpected input

```

This message is not very helpful. This is because the `satisfy` parser has no
idea about the expected token. Let's add some labels to help it:

```python
>>> digit = satisfy(str.isdigit).label("digit")
>>> digits = digit + digit.many()

>>> number = digits.fmap(
...     lambda v: int(v[0] + "".join(v[1]))
... ).label("number") << spaces

>>> list_parser = spaces >> number.sep_by(comma) << eof()

>>> list_parser.parse("1,").unwrap()
Traceback (most recent call last):
  ...
reparsec.output.ParseError: at 2: expected number

```

## Recovering from errors

And now for something completely different:

```python
>>> list_parser.parse("1 2", recover=True).unwrap(recover=True)
[1]

```

The parser recovered from the error and produced a partial result. Pretty
useful. However, `satisfy` again doesn't know how to fix input besides ignoring
some parts of the input:

```python
>>> list_parser.parse("1,", recover=True).unwrap(recover=True)
Traceback (most recent call last):
  ...
reparsec.output.ParseError: at 2: expected number

```

We can use `InsertValue` to return some value during error recovery:

``` python
>>> from reparsec.primitive import InsertValue

>>> list_parser = spaces >> (number | InsertValue(0)).sep_by(comma) << eof()

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
reparsec.output.ParseError: at 2: expected number (inserted 0), at 3: expected
number (inserted 0), at 6: expected ',' or end of file (skipped 1 token)

```

## Conclusion

The final parser definition should look like this:

```python
from reparsec.primitive import InsertValue
from reparsec.sequence import eof, satisfy, sym

spaces = satisfy(str.isspace).many()

digit = satisfy(str.isdigit).label("digit")
digits = digit + digit.many()

number = digits.fmap(
    lambda v: int(v[0] + "".join(v[1]))
).label("number") << spaces

comma = sym(",") << spaces

list_parser = spaces >> (number | InsertValue(0)).sep_by(comma) << eof()
```
