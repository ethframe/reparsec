"""
Parsers for scannerless parsing of strings.
"""

from typing import TypeVar, Union

from .core import scannerless
from .parser import FnParser, Parser, TupleParser
from .types import ParseResult

__all__ = ("literal", "regexp", "parse")

A = TypeVar("A")


def literal(s: str) -> TupleParser[str, str]:
    """
    Parses the string ``s`` and returns it.

    >>> from reparsec.scannerless import literal

    >>> parser = literal("ab")

    >>> parser.parse("ab").unwrap()
    'ab'
    >>> parser.parse("ac").unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 0: expected 'ab'

    :param s: String to parse
    """

    return FnParser(scannerless.literal(s))


def regexp(pat: str, group: Union[int, str] = 0) -> TupleParser[str, str]:
    """
    Parses the prefix of input that matches ``pat`` and returns the value of
    ``group``.

    >>> from reparsec.scannerless import regexp

    >>> parser = regexp("a(.)", 1)

    >>> parser.parse("ab").unwrap()
    'b'
    >>> parser.parse("bb").unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 0: unexpected input

    :param pat: Regular expression
    :param group: Group index or name
    """

    return FnParser(scannerless.regexp(pat, group))


def parse(
        parser: Parser[str, A], stream: str,
        recover: bool = False) -> ParseResult[A, str]:
    """
    Wrapper around :meth:`reparsec.Parser.parse` that enables line and column
    tracking for scannerless parsers.

    >>> from reparsec.scannerless import literal, parse

    >>> parser = literal("a\\n") + literal("b") + literal("c")

    >>> parser.parse("a\\nbb").unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 3: expected 'c'
    >>> parse(parser, "a\\nbb").unwrap()
    Traceback (most recent call last):
      ...
    reparsec.types.ParseError: at 2:2: expected 'c'

    :param parser: Parser to run
    :param stream: String to parse
    :param recover: Flag to enable error recovery
    """

    return parser.parse(
        stream, recover,
        get_loc=scannerless.get_loc,
        fmt_loc=lambda l: "{}:{}".format(l.line + 1, l.col + 1)
    )
