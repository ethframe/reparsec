from abc import abstractmethod
from typing import (
    Callable, Dict, Generic, List, Literal, Optional, Sequence, Tuple, TypeVar
)

from .chain import Chain, ChainL
from .result import (
    Error, Insert, Ok, PrefixItem, Recovered, Repair, Result, Skip
)

T = TypeVar("T", bound=object)
V = TypeVar("V", bound=object)
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U", bound=object)
X = TypeVar("X", bound=object)


RecoveryMode = Literal[None, False, True]


def disallow_recovery(rm: RecoveryMode) -> RecoveryMode:
    if rm is None:
        return None
    return False


def maybe_allow_recovery(rm: RecoveryMode, r: Result[V]) -> RecoveryMode:
    if rm is not None and r.consumed:
        return True
    return rm


ParseFn = Callable[[Sequence[T], int, RecoveryMode], Result[V]]


class Parser(Generic[T, V_co]):
    def parse(
            self, stream: Sequence[T], recover: bool = False) -> Result[V_co]:
        return self.parse_fn(stream, 0, True if recover else None)

    @abstractmethod
    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        ...

    def to_fn(self) -> ParseFn[T, V_co]:
        return self.parse_fn

    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[T, U]":
        self_fn = self.to_fn()

        def fmap(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[U]:
            return self_fn(stream, pos, rm).fmap(fn)

        return FnParser(fmap)

    def bind(self, fn: Callable[[V_co], "Parser[T, U]"]) -> "Parser[T, U]":
        return bind(self, fn)

    def lseq(self, other: "Parser[T, U]") -> "Parser[T, V_co]":
        return lseq(self, other)

    def rseq(self, other: "Parser[T, U]") -> "Parser[T, U]":
        return rseq(self, other)

    def __add__(self, other: "Parser[T, U]") -> "Parser[T, Tuple[V_co, U]]":
        return seq(self, other)

    def __or__(self, other: "Parser[T, V_co]") -> "Parser[T, V_co]":
        self_fn = self.to_fn()
        other_fn = other.to_fn()

        def or_(
                stream: Sequence[T], pos: int,
                rm: RecoveryMode) -> Result[V_co]:
            ra = self_fn(stream, pos, disallow_recovery(rm))
            if ra.consumed is True:
                return ra
            rb = other_fn(stream, pos, disallow_recovery(rm))
            if rb.consumed is True:
                return rb
            expected = Chain(ra.expected, rb.expected)
            if type(ra) is Ok:
                return ra.expect(expected)
            if type(rb) is Ok:
                return rb.expect(expected)
            if rm:
                ra = self_fn(stream, pos, True)
                rb = other_fn(stream, pos, True)
                if type(ra) is Recovered:
                    if type(rb) is Recovered:
                        reps = {pb.pos: pb for pb in rb.repairs}
                        reps.update((pa.pos, pa) for pa in ra.repairs)
                        return Recovered(list(reps.values()))
                    return ra.expect(expected)
                if type(rb) is Recovered:
                    return rb.expect(expected)
            return Error(pos, expected)

        return FnParser(or_)

    def maybe(self) -> "Parser[T, Optional[V_co]]":
        return maybe(self)

    def many(self) -> "Parser[T, List[V_co]]":
        return many(self)

    def label(self, expected: str) -> "Parser[T, V_co]":
        return label(self, expected)

    def sep_by(self, sep: "Parser[T, U]") -> "Parser[T, List[V_co]]":
        return sep_by(self, sep)

    def between(
            self, open: "Parser[T, U]",
            close: "Parser[T, X]") -> "Parser[T, V_co]":
        return between(open, close, self)


class FnParser(Parser[T, V_co]):
    def __init__(self, fn: ParseFn[T, V_co]):
        self._fn = fn

    def to_fn(self) -> ParseFn[T, V_co]:
        return self._fn

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        return self._fn(stream, pos, rm)


def _continue_parse(
        stream: Sequence[T], ra: Recovered[V],
        parse: Callable[[Sequence[T], Repair[V]], Result[U]],
        merge: Callable[[V, U], X]) -> Result[X]:
    reps: Dict[int, Repair[X]] = {}
    for pa in ra.repairs:
        rb = parse(stream, pa)
        if type(rb) is Ok:
            if rb.pos not in reps or pa.cost < reps[rb.pos].cost:
                reps[rb.pos] = Repair(
                    pa.cost, merge(pa.value, rb.value), rb.pos, pa.op,
                    pa.expected, pa.consumed, pa.prefix
                )
        elif type(rb) is Recovered:
            for pb in rb.repairs:
                cost = pa.cost + pb.cost
                if pb.pos not in reps or cost < reps[pb.pos].cost:
                    reps[pb.pos] = Repair(
                        cost, merge(pa.value, pb.value), pb.pos, pb.op,
                        pb.expected, True,
                        Chain(
                            pa.prefix,
                            ChainL(PrefixItem(pa.op, pa.expected), pb.prefix)
                        )
                    )
    if reps:
        return Recovered(list(reps.values()))
    return ra.to_error()


def bind(
        parser: Parser[T, V], fn: Callable[[V], Parser[T, U]]) -> Parser[T, U]:
    parser_fn = parser.to_fn()

    def bind(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[U]:
        ra = parser_fn(stream, pos, rm)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return _continue_parse(
                stream, ra, lambda s, p: fn(p.value).parse_fn(s, p.pos, True),
                lambda _, v: v
            )
        return fn(ra.value).parse_fn(
            stream, ra.pos, maybe_allow_recovery(rm, ra)
        ).merge_expected(ra.expected, ra.consumed)

    return FnParser(bind)


def _make_seq(
        parser: Parser[T, V], second: Parser[T, U],
        fn: Callable[[V, U], X]) -> Parser[T, X]:
    parser_fn = parser.to_fn()
    second_fn = second.to_fn()

    def seq(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[X]:
        ra = parser_fn(stream, pos, rm)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return _continue_parse(
                stream, ra, lambda s, p: second_fn(s, p.pos, True), fn
            )
        va = ra.value
        return second_fn(stream, ra.pos, maybe_allow_recovery(rm, ra)).fmap(
            lambda vb: fn(va, vb)
        ).merge_expected(ra.expected, ra.consumed)

    return FnParser(seq)


def lseq(parser: Parser[T, V], second: Parser[T, U]) -> Parser[T, V]:
    return _make_seq(parser, second, lambda l, _: l)


def rseq(parser: Parser[T, V], second: Parser[T, U]) -> Parser[T, U]:
    return _make_seq(parser, second, lambda _, r: r)


def seq(parser: Parser[T, V], second: Parser[T, U]) -> Parser[T, Tuple[V, U]]:
    return _make_seq(parser, second, lambda l, r: (l, r))


class Pure(Parser[T, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        return Ok(self._x, pos)


pure = Pure


class PureFn(Parser[T, V_co]):
    def __init__(self, fn: Callable[[], V_co]):
        self._fn = fn

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        return Ok(self._fn(), pos)


pure_fn = PureFn


class Eof(Parser[T, None]):
    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[None]:
        if pos == len(stream):
            return Ok(None, pos)
        if rm:
            skip = len(stream) - pos
            return Recovered([Repair(
                skip, None, len(stream), Skip(skip, pos), ["end of file"]
            )])
        return Error(pos, ["end of file"])


eof = Eof


def satisfy(test: Callable[[T], bool]) -> Parser[T, T]:
    def satisfy(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if test(t):
                return Ok(t, pos + 1, consumed=True)
        if rm:
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if test(t):
                    skip = cur - pos
                    Recovered([Repair(skip, t, cur + 1, Skip(skip, pos))])
                cur += 1
        return Error(pos)

    return FnParser(satisfy)


def sym(s: T) -> Parser[T, T]:
    rs = repr(s)
    expected = [rs]

    def sym(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Ok(t, pos + 1, consumed=True)
        if rm:
            ins = Repair(1, s, pos, Insert(rs, pos), expected)
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if t == s:
                    skip = cur - pos
                    return Recovered([
                        ins,
                        Repair(skip, t, cur + 1, Skip(skip, pos), expected)
                    ])
                cur += 1
            return Recovered([ins])
        return Error(pos, expected)

    return FnParser(sym)


def maybe(parser: Parser[T, V]) -> Parser[T, Optional[V]]:
    fn = parser.to_fn()

    def maybe(
            stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[Optional[V]]:
        r = fn(stream, pos, disallow_recovery(rm))
        if r.consumed is True or type(r) is Ok:
            return r
        return Ok(None, pos, r.expected)

    return FnParser(maybe)


def many(parser: Parser[T, V]) -> Parser[T, List[V]]:
    fn = parser.to_fn()

    def many(
            stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[List[V]]:
        rm = disallow_recovery(rm)
        consumed = False
        value: List[V] = []
        r = fn(stream, pos, rm)
        while type(r) is Ok:
            consumed |= r.consumed
            value.append(r.value)
            r = fn(stream, r.pos, rm)
        if type(r) is Recovered:
            return _continue_parse(
                stream, r, parse, lambda a, b: [*value, a, *b]
            )
        if r.consumed:
            return r
        return Ok(value, r.pos, r.expected, consumed)

    def parse(stream: Sequence[T], p: Repair[V]) -> Result[List[V]]:
        r = many(stream, p.pos, True)
        if type(r) is Error and r.consumed is False:
            return Ok[List[V]]([], r.pos, r.expected)
        return r

    return FnParser(many)


def label(parser: Parser[T, V], x: str) -> Parser[T, V]:
    fn = parser.to_fn()
    expected = [x]

    def label(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[V]:
        return fn(stream, pos, rm).expect(expected)

    return FnParser(label)


class InsertValue(Parser[T, V_co]):
    def __init__(self, value: V_co, expected: Optional[str] = None):
        self._value = value
        self._label = repr(value)
        self._expected = [] if expected is None else [expected]

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        if rm:
            return Recovered([Repair(
                1, self._value, pos, Insert(self._label, pos), self._expected
            )])
        return Error(pos)


insert = InsertValue


class Delay(Parser[T, V_co]):
    def __init__(self) -> None:
        def _fn(
                stream: Sequence[T], pos: int,
                rm: RecoveryMode) -> Result[V_co]:
            raise RuntimeError("Delayed parser was not defined")

        self._defined = False
        self._fn: ParseFn[T, V_co] = _fn

    def define(self, parser: Parser[T, V_co]) -> None:
        if self._defined:
            raise RuntimeError("Delayed parser was already defined")
        self._defined = True
        self._fn = parser.to_fn()

    def to_fn(self) -> ParseFn[T, V_co]:
        if self._defined:
            return self._fn
        return super().to_fn()

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        return self._fn(stream, pos, rm)


def sep_by(parser: Parser[T, V], sep: Parser[T, U]) -> Parser[T, List[V]]:
    return maybe(parser + many(sep.rseq(parser))).fmap(
        lambda v: [] if v is None else [v[0]] + v[1]
    )


def between(
        open: Parser[T, U], close: Parser[T, X],
        parser: Parser[T, V]) -> Parser[T, V]:
    return open.rseq(parser).lseq(close)


letter: Parser[str, str] = satisfy(str.isalpha).label("letter")
digit: Parser[str, str] = satisfy(str.isdigit).label("digit")
