Tutorial
========

Suppose we need to parse a list of numbers separated by commas without an
external lexer. This means that we should build our parser from the simplest
ones.

Parsing numbers
---------------

First, we need to recognize digits. For this we will use the
:func:`reparsec.sequence.satisfy` parser. It is parameterized with a predicate
to test the input token.

>>> from reparsec.sequence import satisfy
>>> digit = satisfy(str.isdigit)


Let's try it in action. We can use the :meth:`reparsec.Parser.parse` method of
our freshly created parser to parse a string. It returns either a result of
successful parse or an error. You can get the actual value or exception with an
:meth:`reparsec.ParseResult.unwrap` method:

>>> digit.parse("123").unwrap()
'1'
>>> digit.parse("a").unwrap()
Traceback (most recent call last):
  ...
reparsec.types.ParseError: at 0: unexpected input

So far, so good. Next, we want to parse numbers. For simplicity let's assume
that a number is a sequence of one or more digits:

>>> digits = digit + digit.many()

We use method :meth:`reparsec.Parser.many` to construct parser that tries to
apply original parser zero or more times, and operator `+` to sequentially
apply two parsers.

>>> digits.parse("123").unwrap()
('1', ['2', '3'])

The output doesn't looks like a number yet. We need
:meth:`reparsec.Parser.fmap` to convert it to a number:

>>> number = digits.fmap(lambda v: int(v[0] + "".join(v[1])))
>>> number.parse("123").unwrap()
123

Parsing lists
-------------

Now we are ready to parse the list. The list is just a sequence of numbers
separated by commas. To parse a single comma we will use the
:func:`reparsec.sequence.sym` parser, which is parameterized with expected
character. Parsers for sequences with separators are usually constructed using
the :meth:`reparsec.Parser.sep_by` combinator:

>>> from reparsec.sequence import sym
>>> list_parser = number.sep_by(sym(","))
>>> list_parser.parse("12,34,56").unwrap()
[12, 34, 56]

Success!

Allowing whitespace
-------------------

What if we want to allow whitespace around numbers? Let's extend the parser to
accept such inputs:

>>> space = satisfy(str.isspace)
>>> spaces = space.many()
>>> number = digits.fmap(lambda v: int(v[0] + "".join(v[1]))) << spaces
>>> comma = sym(",") << spaces
>>> list_parser = spaces >> number.sep_by(comma)
>>> list_parser.parse(" 1 , 2 ").unwrap()
[1, 2]

The `<<` and `>>` operators used here are similar to `+`, but return only the
value of left or right parser, respectively.

Parsing incorrect inputs
------------------------

Until before we focused on parsing valid inputs. But what if we have a string
with unexpected characters in it?

>>> list_parser.parse("1,a").unwrap()
Traceback (most recent call last):
  ...
reparsec.types.ParseError: at 2: unexpected input

The parser reported an error and provided a brief description of what was wrong
with the input.

>>> list_parser.parse("1a").unwrap()
[1]

Ouch! While reporting errors in general, in some cases our parser silently
ignores the rest of the input. Let's fix this by requiring input to end right
after the list using the :func:`reparsec.sequence.eof` parser:

>>> from reparsec.sequence import eof
>>> list_parser = spaces >> number.sep_by(comma) << eof()
>>> list_parser.parse("1a").unwrap()
Traceback (most recent call last):
  ...
reparsec.types.ParseError: at 1: expected ',' or end of file

Much better.

Improving error reporting
-------------------------

Let's take a closer look at the errors messages:

>>> list_parser.parse("1 2").unwrap()
Traceback (most recent call last):
  ...
reparsec.types.ParseError: at 2: expected ',' or end of file

Seems informative.

>>> list_parser.parse("1,").unwrap()
Traceback (most recent call last):
  ...
reparsec.types.ParseError: at 2: unexpected input

This message is not very helpful. This is because the
:func:`reparsec.sequence.satisfy` parser has no idea about the expected token.
Let's add some labels to help it with :meth:`reparsec.Parser.label` combinator:

>>> digit = satisfy(str.isdigit).label("digit")
>>> digits = digit + digit.many()
>>> number = digits.fmap(
...     lambda v: int(v[0] + "".join(v[1]))
... ).label("number") << spaces
>>> list_parser = spaces >> number.sep_by(comma) << eof()
>>> list_parser.parse("1,").unwrap()
Traceback (most recent call last):
  ...
reparsec.types.ParseError: at 2: expected number

Recovering from errors
----------------------

And now for something completely different:

>>> list_parser.parse("1 2", recover=True).unwrap(recover=True)
[1]

The parser recovered from the error and produced a partial result. Pretty
useful. However, :func:`reparsec.satisfy` again doesn't know how to fix input
besides ignoring some parts of the input:

>>> list_parser.parse("1,", recover=True).unwrap(recover=True)
Traceback (most recent call last):
  ...
reparsec.types.ParseError: at 2: expected number

We can use :meth:`reparsec.Parser.recover_with` to return some value during
error recovery:

>>> list_parser = spaces >> number.recover_with(0).sep_by(comma) << eof()
>>> list_parser.parse("1,", recover=True).unwrap(recover=True)
[1, 0]

The parser is even capable of fixing multiple errors in the input:

>>> list_parser.parse("1,,,2 3", recover=True).unwrap(recover=True)
[1, 0, 0, 2]

And what if we want to show them to user?

>>> list_parser.parse("1,,,2 3", recover=True).unwrap()
Traceback (most recent call last):
  ...
reparsec.types.ParseError: at 2: expected number (inserted 0),
at 3: expected number (inserted 0),
at 6: expected ',' or end of file (skipped 1 token)

Line and column tracking
------------------------

Error reporting still needs another improvement. All of the messages in the
previous examples contains indexes in the input string as error positions, but
it is more convenient to show line and column numbers instead. To achieve this,
we will use :func:`reparsec.scannerless.parse`. This is a wrapper around
:meth:`reparsec.Parser.parse` that enables position tracking for parsers with
string inputs:

>>> from reparsec.scannerless import parse
>>> src = """\
... 1,,
...  ,2
... 3
... """
>>> parse(list_parser, src, recover=True).unwrap()
Traceback (most recent call last):
  ...
reparsec.types.ParseError: at 1:3: expected number (inserted 0),
at 2:2: expected number (inserted 0),
at 3:1: expected ',' or end of file (skipped 2 tokens)

As a finishing touch, let's write a helper function so that users of our parser
don't have to think about how to properly invoke the parser:

>>> from typing import List
>>> def parse_list(src: str) -> List[int]:
...     return parse(list_parser, src, recover=True).unwrap()
>>> parse_list("1, 2, 3")
[1, 2, 3]
>>> parse_list("1, ,2 3")
Traceback (most recent call last):
  ...
reparsec.types.ParseError: at 1:4: expected number (inserted 0),
at 1:7: expected ',' or end of file (skipped 1 token)

Conclusion
----------

The final parser definition should look like this::

    from typing import List

    from reparsec.scannerless import parse
    from reparsec.sequence import eof, satisfy, sym

    spaces = satisfy(str.isspace).many()

    digit = satisfy(str.isdigit).label("digit")
    digits = digit + digit.many()

    number = digits.fmap(
        lambda v: int(v[0] + "".join(v[1]))
    ).label("number") << spaces

    comma = sym(",") << spaces

    list_parser = spaces >> number.recover_with(0).sep_by(comma) << eof()

    def parse_list(src: str) -> List[int]:
        return parse(list_parser, src, recover=True).unwrap()
