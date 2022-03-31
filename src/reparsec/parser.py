"""
Core parser API and parser combinators.
"""

from typing import Callable, List, Optional, Tuple, TypeVar, Union

from .core import combinators
from .core.result import BaseRepair, Error, Ok, Result
from .core.state import Ctx, Loc
from .core.types import ParseFn, ParseObj, RecoveryMode
from .output import ErrorItem, ParseError, ParseResult

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")
X = TypeVar("X")


def _get_loc(loc: Loc, stream: S, pos: int) -> Loc:
    return Loc(pos, 0, 0)


def _fmt_loc(loc: Loc) -> str:
    return repr(loc.pos)


class Parser(ParseObj[S_contra, V_co]):
    def parse(
            self, stream: S_contra, recover: bool = False, *,
            max_insertions: int = 5,
            get_loc: Callable[[Loc, S_contra, int], Loc] = _get_loc,
            fmt_loc: Callable[[Loc], str] = _fmt_loc
    ) -> ParseResult[V_co, S_contra]:
        """
        Parses input.

        :param stream: Input to parse
        :param recover: Flag to enable error recovery
        :param max_insertions: Maximal number of token insertions in a row
            during error recovery
        :param get_loc: Function that constructs new ``Loc`` from a previous
            ``Loc``, a stream, and position in the stream
        :param fmt_loc: Function that converts ``Loc`` to string
        """

        ctx = Ctx(0, Loc(0, 0, 0), max_insertions, get_loc)
        result = self.parse_fn(
            stream, 0, ctx, ctx.max_insertions if recover else None
        )
        return _ParseResult(result, fmt_loc)

    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[S_contra, U]":
        """
        Transforms the result of the parser by applying ``fn`` to it.

        >>> from reparsec.sequence import satisfy

        >>> satisfy(str.isdigit).fmap(lambda x: int(x) + 1).parse("0").unwrap()
        1

        :param fn: Function to produce new value from the result of the parser
        """

        return fmap(self, fn)

    def bind(
            self, fn: Callable[[V_co], ParseObj[S_contra, U]]
    ) -> "Parser[S_contra, U]":
        """
        Calls ``fn`` with the result of the parser and then applies the
        returned parser.

        >>> from reparsec.sequence import satisfy, sym

        >>> parser = satisfy(lambda _: True).bind(lambda x: sym(x))

        >>> parser.parse("aa").unwrap()
        'a'
        >>> parser.parse("bb").unwrap()
        'b'
        >>> parser.parse("ab").unwrap()
        Traceback (most recent call last):
        ...
        reparsec.output.ParseError: at 1: expected 'a'

        :param fn: Function that returns a new parser using the result of this
            parser
        """

        return bind(self, fn)

    def seql(self, other: ParseObj[S_contra, U]) -> "Parser[S_contra, V_co]":
        """
        Alias for :meth:`Parser.__lshift__`

        :param other: Second parser
        """

        return seql(self, other)

    def seqr(self, other: ParseObj[S_contra, U]) -> "Parser[S_contra, U]":
        """
        Alias for :meth:`Parser.__rshift__`

        :param other: Second parser
        """

        return seqr(self, other)

    def __lshift__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, V_co]":
        """
        Applies two parsers sequentially and returns the result of the first
        parser.

        >>> from reparsec.sequence import sym

        >>> (sym("a") << sym("b")).parse("ab").unwrap()
        'a'

        :param other: Second parser
        """

        return seql(self, other)

    def __rshift__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, U]":
        """
        Applies two parsers sequentially and returns the result of the second
        parser.

        >>> from reparsec.sequence import sym

        >>> (sym("a") >> sym("b")).parse("ab").unwrap()
        'b'

        :param second: Second parser
        """

        return seqr(self, other)

    def __add__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, Tuple[V_co, U]]":
        """
        Applies two parsers sequentially and returns a tuple of their results.

        >>> from reparsec.sequence import sym

        >>> parser = sym("a") + sym("b")

        >>> parser.parse("ab").unwrap()
        ('a', 'b')
        >>> parser.parse("ac").unwrap()
        Traceback (most recent call last):
          ...
        reparsec.output.ParseError: at 1: expected 'b'

        :param other: Second parser
        """

        return seq(self, other)

    def __or__(
            self, other: ParseObj[S_contra, U]
    ) -> "Parser[S_contra, Union[V_co, U]]":
        """
        Applies the first parser and returns its' result unless it fails
        without consuming any input. In this case the second parser is applied
        and its' result is returned.

        >>> from reparsec.sequence import sym

        >>> parser = sym("a") | sym("b")

        >>> parser.parse("a").unwrap()
        'a'
        >>> parser.parse("b").unwrap()
        'b'
        >>> parser.parse("c").unwrap()
        Traceback (most recent call last):
        ...
        reparsec.output.ParseError: at 0: expected 'a' or 'b'

        :param other: Second parser
        """

        return alt(self, other)

    def maybe(self) -> "Parser[S_contra, Optional[V_co]]":
        """
        Applies the parser and returns ``None`` if it failed withoud consuming
        input. Otherwise returns the result of the parser.

        Identical to ``parser | Pure(None)``.

        >>> from reparsec.sequence import sym

        >>> parser = (sym("a") << sym("b")).maybe()

        >>> parser.parse("ab").unwrap()
        'a'
        >>> parser.parse("bb").unwrap()
        >>> parser.parse("aa").unwrap()
        Traceback (most recent call last):
          ...
        reparsec.output.ParseError: at 1: expected 'b'
        """

        return maybe(self)

    def many(self) -> "Parser[S_contra, List[V_co]]":
        """
        Applies the parser multiple times, until it fails. Returns a list of
        the parsed values if the parser failed withoud consuming input.

        >>> from reparsec.sequence import sym

        >>> parser = (sym("a") << sym("b")).many()

        >>> parser.parse("abab").unwrap()
        ['a', 'a']
        >>> parser.parse("abbb").unwrap()
        ['a']
        >>> parser.parse("abaa").unwrap()
        Traceback (most recent call last):
          ...
        reparsec.output.ParseError: at 3: expected 'b'
        """

        return many(self)

    def attempt(self) -> "Parser[S_contra, V_co]":
        """
        Applies the parser, and pretends that no input was consumed if it
        fails.

        This can be seen as switching the parser behaviour from LL(1)-like to
        PEG-like.

        >>> from reparsec.sequence import sym

        >>> parser = (sym("a") << sym("b"))

        >>> parser.maybe().parse("aa").unwrap()
        Traceback (most recent call last):
          ...
        reparsec.output.ParseError: at 1: expected 'b'
        >>> parser.attempt().maybe().parse("aa").unwrap()
        """

        return attempt(self)

    def label(self, expected: str) -> "Parser[S_contra, V_co]":
        """
        Applies the parser, and replaces list of expected values with
        ``[expected]`` if no input was consumed.

        >>> from reparsec.sequence import sym

        >>> parser = (sym("a") + sym("b")).label("x")

        >>> parser.parse("bb").unwrap()
        Traceback (most recent call last):
          ...
        reparsec.output.ParseError: at 0: expected x
        >>> parser.parse("aa").unwrap()
        Traceback (most recent call last):
          ...
        reparsec.output.ParseError: at 1: expected 'b'

        :param expected: Description of the expected input
        """

        return label(self, expected)

    def insert_on_error(
            self, insert_fn: Callable[[S_contra, int], V_co],
            label: Optional[str] = None) -> "Parser[S_contra, V_co]":
        """
        Applies the parser and returns its' result unless it failed without
        consuming input while error recovery is enabled. In this case, the
        ``insert_fn`` is called to produce a value that will be returned as a
        result of recovering from the error.

        >>> from reparsec.sequence import satisfy

        >>> parser = satisfy(str.isalpha).insert_on_error(lambda s, p: "b")

        >>> parser.parse("a").unwrap()
        'a'
        >>> parser.parse("0").unwrap()
        Traceback (most recent call last):
          ...
        reparsec.output.ParseError: at 0: unexpected input
        >>> parser.parse("0", recover=True).unwrap()
        Traceback (most recent call last):
          ...
        reparsec.output.ParseError: at 0: unexpected input (inserted 'b')
        >>> parser.parse("0", recover=True).unwrap(recover=True)
        'b'

        :param insert_fn: Function that produces a parsed value
        :param label: Description of the expected input
        """

        return insert_on_error(self, insert_fn, label)

    def sep_by(
            self,
            sep: ParseObj[S_contra, U]) -> "Parser[S_contra, List[V_co]]":
        """
        Applies the parser multiple times, with ``sep`` in between. Returns a
        list of the values parsed by the parser.

        >>> from reparsec.sequence import sym

        >>> parser = sym("a").sep_by(sym(","))

        >>> parser.parse("a,a,a").unwrap()
        ['a', 'a', 'a']

        :param sep: Separators parser
        """

        return sep_by(self, sep)

    def between(
            self, open: ParseObj[S_contra, U],
            close: ParseObj[S_contra, X]) -> "Parser[S_contra, V_co]":
        """
        Applies ``open``, then the parser, then ``close``, and returns the
        value parsed by the parser.

        >>> from reparsec.sequence import sym

        >>> parser = sym("a").between(sym("("), sym(")"))

        >>> parser.parse("(a)").unwrap()
        'a'

        :param open: 'Opening bracket' parser
        :param close: 'Closing bracket' parser
        """

        return between(open, close, self)

    def chainl1(
            self, op: ParseObj[S_contra, Callable[[V_co, V_co], V_co]]
    ) -> "Parser[S_contra, V_co]":
        """
        Applies the parser one or more times, with ``op`` in between. Returns a
        value of left-associative application of functions returned by ``op``
        to the values parsed by the parser.

        >>> from reparsec.sequence import sym

        >>> parser = sym("a").chainl1(
        ...     sym("+").fmap(lambda _: "({}+{})".format)
        ... )

        >>> parser.parse("a+a+a").unwrap()
        '((a+a)+a)'

        :param op: Operator parser
        """

        return chainl1(self, op)

    def chainr1(
            self, op: ParseObj[S_contra, Callable[[V_co, V_co], V_co]]
    ) -> "Parser[S_contra, V_co]":
        """
        Applies the parser one or more times, with ``op`` in between. Returns a
        value of right-associative application of functions returned by ``op``
        to the values parsed by the parser.

        >>> from reparsec.sequence import sym

        >>> parser = sym("a").chainr1(
        ...     sym("^").fmap(lambda _: "({}^{})".format)
        ... )

        >>> parser.parse("a^a^a").unwrap()
        '(a^(a^a))'

        :param op: Operator parser
        """

        return chainr1(self, op)


class FnParser(Parser[S_contra, V_co]):
    def __init__(self, fn: ParseFn[S_contra, V_co]):
        self._fn = fn

    def to_fn(self) -> ParseFn[S_contra, V_co]:
        return self._fn

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        return self._fn(stream, pos, ctx, rm)


def fmap(parser: ParseObj[S, V], fn: Callable[[V], U]) -> Parser[S, U]:
    """
    :meth:`Parser.fmap` as a function.

    :param parser: Parser
    :param fn: Function to produce value from the result of ``parser``
    """

    return FnParser(combinators.fmap(parser.to_fn(), fn))


def bind(
        parser: ParseObj[S, V],
        fn: Callable[[V], ParseObj[S, U]]) -> Parser[S, U]:
    """
    :meth:`Parser.bind` as a function.

    :param parser: Parser
    :param fn: Function that returns a new parser using the result of the
        parser
    """

    return FnParser(combinators.bind(parser.to_fn(), fn))


def seq(
        parser: ParseObj[S, V],
        second: ParseObj[S, U]) -> Parser[S, Tuple[V, U]]:
    """
    :meth:`Parser.__add__` as a function.

    :param parser: First parser
    :param second: Second parser
    """

    return FnParser(combinators.seq(parser.to_fn(), second.to_fn()))


def seql(parser: ParseObj[S, V], second: ParseObj[S, U]) -> Parser[S, V]:
    """
    :meth:`Parser.seql` as a function.

    :param parser: First parser
    :param second: Second parser
    """

    return FnParser(combinators.seql(parser.to_fn(), second.to_fn()))


def seqr(parser: ParseObj[S, V], second: ParseObj[S, U]) -> Parser[S, U]:
    """
    :meth:`Parser.seqr` as a function.

    :param parser: First parser
    :param second: Second parser
    """

    return FnParser(combinators.seqr(parser.to_fn(), second.to_fn()))


def alt(
        parser: ParseObj[S, V],
        second: ParseObj[S, U]) -> Parser[S, Union[V, U]]:
    """
    :meth:`Parser.__or__` as a function.

    :param parser: First parser
    :param second: Second parser
    """

    return FnParser(combinators.alt(parser.to_fn(), second.to_fn()))


def maybe(parser: ParseObj[S, V]) -> Parser[S, Optional[V]]:
    """
    :meth:`Parser.maybe` as a function.

    :param parser: Parser
    """

    return FnParser(combinators.maybe(parser.to_fn()))


def many(parser: ParseObj[S, V]) -> Parser[S, List[V]]:
    """
    :meth:`Parser.many` as a function.

    :param parser: Parser
    """

    return FnParser(combinators.many(parser.to_fn()))


def attempt(parser: ParseObj[S, V]) -> Parser[S, V]:
    """
    :meth:`Parser.attempt` as a function.

    :param parser: Parser
    """

    return FnParser(combinators.attempt(parser.to_fn()))


def label(parser: ParseObj[S, V], expected: str) -> Parser[S, V]:
    """
    :meth:`Parser.label` as a function.

    :param parser: Parser
    :param expected: Description of the expected input
    """

    return FnParser(combinators.label(parser.to_fn(), expected))


def insert_on_error(
        parser: ParseObj[S, V], insert_fn: Callable[[S, int], V],
        label: Optional[str] = None) -> Parser[S, V]:
    """
    :meth:`Parser.insert_on_error` as a function.

    :param parser: Parser
    :param insert_fn: Function that produces a parsed value
    :param label: Description of the expected input
    """

    return FnParser(
        combinators.insert_on_error(parser.to_fn(), insert_fn, label)
    )


class Delay(Parser[S_contra, V_co]):
    """
    Special parser to use as a forward declaration.

    >>> from reparsec import Delay
    >>> from reparsec.sequence import sym

    >>> parser = Delay()
    >>> parser.define((sym("a") + parser).maybe())

    >>> parser.parse("aaa").unwrap()
    ('a', ('a', ('a', None)))
    """

    def __init__(self) -> None:
        def _fn(
                stream: S_contra, pos: int, ctx: Ctx[S_contra],
                rm: RecoveryMode) -> Result[V_co, S_contra]:
            raise RuntimeError("Delayed parser was not defined")

        self._defined = False
        self._fn: ParseFn[S_contra, V_co] = _fn

    def define(self, parser: ParseObj[S_contra, V_co]) -> None:
        """
        Define the parser.

        >>> from reparsec import Delay
        >>> from reparsec.sequence import sym

        >>> parser = Delay()
        >>> parser.parse("a")
        Traceback (most recent call last):
          ...
        RuntimeError: Delayed parser was not defined

        >>> parser.define(sym("a"))
        >>> parser.parse("a").unwrap()
        'a'

        :param parser: Parser definition
        """

        if self._defined:
            raise RuntimeError("Delayed parser was already defined")
        self._defined = True
        self._fn = parser.to_fn()

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        return self._fn(stream, pos, ctx, rm)

    def to_fn(self) -> ParseFn[S_contra, V_co]:
        if self._defined:
            return self._fn
        return super().to_fn()


def sep_by(parser: ParseObj[S, V], sep: ParseObj[S, U]) -> Parser[S, List[V]]:
    """
    :meth:`Parser.sep_by` as a function.

    :param parser: Items parser
    :param sep: Separators parser
    """

    return maybe(seq(parser, many(seqr(sep, parser)))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


def between(
        open: ParseObj[S, U], close: ParseObj[S, X],
        parser: ParseObj[S, V]) -> Parser[S, V]:
    """
    :meth:`Parser.between` as a function.

    :param open: 'Opening bracket' parser
    :param close: 'Closing bracket' parser
    :param parser: Value parser
    """

    return seqr(open, seql(parser, close))


def chainl1(
        arg: ParseObj[S, V],
        op: ParseObj[S, Callable[[V, V], V]]) -> Parser[S, V]:
    """
    :meth:`Parser.chainl1` as a function.

    :param arg: Argument parser
    :param op: Operator parser
    """

    def reducer(v: Tuple[V, List[Tuple[Callable[[V, V], V], V]]]) -> V:
        res, tail = v
        for op, arg in tail:
            res = op(res, arg)
        return res

    return fmap(seq(arg, many(seq(op, arg))), reducer)


def chainr1(
        arg: ParseObj[S, V],
        op: ParseObj[S, Callable[[V, V], V]]) -> Parser[S, V]:
    """
    :meth:`Parser.chainr1` as a function.

    :param arg: Argument parser
    :param op: Operator parser
    """

    def reducer(v: Tuple[V, List[Tuple[Callable[[V, V], V], V]]]) -> V:
        res, tail = v
        rassoc: List[Tuple[V, Callable[[V, V], V]]] = []
        for op, arg in tail:
            rassoc.append((res, op))
            res = arg
        for arg, op in reversed(rassoc):
            res = op(arg, res)
        return res

    return fmap(seq(arg, many(seq(op, arg))), reducer)


class _ParseResult(ParseResult[V_co, S]):
    def __init__(self, result: Result[V_co, S], fmt_loc: Callable[[Loc], str]):
        self._result = result
        self._fmt_loc = fmt_loc

    def fmap(self, fn: Callable[[V_co], U]) -> ParseResult[U, S]:
        return _ParseResult(self._result.fmap(fn), self._fmt_loc)

    def unwrap(self, recover: bool = False) -> V_co:
        if type(self._result) is Ok:
            return self._result.value

        if type(self._result) is Error:
            raise ParseError([
                ErrorItem(
                    self._result.loc,
                    self._fmt_loc(self._result.loc),
                    list(self._result.expected),
                )
            ])

        repair: Optional[BaseRepair[V_co, S]] = self._result.selected
        if repair is None:
            repair = self._result.pending
            if repair is None:
                raise ParseError([
                    ErrorItem(
                        self._result.loc,
                        self._fmt_loc(self._result.loc),
                        list(self._result.expected)
                    )
                ])
        if recover:
            return repair.value
        errors = [
            ErrorItem(
                item.loc, self._fmt_loc(item.loc), list(item.expected), item.op
            )
            for item in repair.ops
        ]
        raise ParseError(errors)
