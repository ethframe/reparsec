from abc import abstractmethod
from typing import (
    Callable, Dict, Generic, List, Optional, Sequence, Tuple, TypeVar
)

from .chain import Chain, ChainR
from .result import (
    Error, Insert, Ok, PrefixItem, Recovered, Repair, Result, Skip
)

T = TypeVar("T")
V = TypeVar("V", bound=object)
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U", bound=object)
X = TypeVar("X", bound=object)


ParseFn = Callable[[Sequence[T], int, int], Result[V]]


class Parser(Generic[T, V_co]):
    def parse(
            self, stream: Sequence[T], recover: bool = False) -> Result[V_co]:
        return self(stream, 0, -1 if recover else len(stream))

    @abstractmethod
    def __call__(self, stream: Sequence[T], pos: int, bt: int) -> Result[V_co]:
        ...

    def to_fn(self) -> ParseFn[T, V_co]:
        return self

    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[T, U]":
        self_fn = self.to_fn()

        def fmap(stream: Sequence[T], pos: int, bt: int) -> Result[U]:
            return self_fn(stream, pos, bt).fmap(fn)

        return FnParser(fmap)

    def bind(self, fn: Callable[[V_co], "Parser[T, U]"]) -> "Parser[T, U]":
        self_fn = self.to_fn()

        def bind(stream: Sequence[T], pos: int, bt: int) -> Result[U]:
            ra = self_fn(stream, pos, bt)
            if type(ra) is Error:
                return ra
            if type(ra) is Recovered:
                return bind_recover(ra, stream)
            return fn(ra.value)(stream, ra.pos, bt).merge_expected(ra)

        def bind_recover(
                ra: Recovered[V_co], stream: Sequence[T]) -> Result[U]:
            reps: Dict[int, Repair[U]] = {}
            for pa in ra.repairs:
                rb = fn(pa.value)(stream, pa.pos, -1)
                if type(rb) is Ok:
                    if rb.pos not in reps or pa.cost < reps[rb.pos].cost:
                        reps[rb.pos] = Repair(
                            pa.cost, rb.value, rb.pos, pa.op, pa.consumed,
                            pa.expected, pa.prefix
                        )
                elif type(rb) is Recovered:
                    for pb in rb.repairs:
                        cost = pa.cost + pb.cost
                        if pb.pos not in reps or cost < reps[pb.pos].cost:
                            reps[pb.pos] = Repair(
                                cost, pb.value, pb.pos, pb.op, pb.consumed,
                                pb.expected,
                                Chain(
                                    ChainR(
                                        pa.prefix,
                                        PrefixItem(pa.op, pa.expected)
                                    ),
                                    pb.prefix
                                )
                            )
            if reps:
                return Recovered(list(reps.values()))
            pa = next(iter(ra.repairs))
            return Error(pa.op.pos, pa.consumed, pa.expected)

        return FnParser(bind)

    def lseq(self, other: "Parser[T, U]") -> "Parser[T, V_co]":
        return lseq(self, other)

    def rseq(self, other: "Parser[T, U]") -> "Parser[T, U]":
        return rseq(self, other)

    def __add__(self, other: "Parser[T, U]") -> "Parser[T, Tuple[V_co, U]]":
        return seq(self, other)

    def __or__(self, other: "Parser[T, V_co]") -> "Parser[T, V_co]":
        self_fn = self.to_fn()
        other_fn = other.to_fn()

        def or_(stream: Sequence[T], pos: int, bt: int) -> Result[V_co]:
            ra = self_fn(stream, pos, max(pos, bt))
            if ra.consumed is True:
                return ra
            rb = other_fn(stream, pos, max(pos, bt))
            if rb.consumed is True:
                return rb
            expected = Chain(ra.expected, rb.expected)
            if type(ra) is Ok:
                return ra.expect(expected)
            if type(rb) is Ok:
                return rb.expect(expected)
            if pos > bt:
                ra = self_fn(stream, pos, -1)
                rb = other_fn(stream, pos, -1)
                if type(ra) is Recovered:
                    if type(rb) is Recovered:
                        reps = {pb.pos: pb for pb in rb.repairs}
                        reps.update((pa.pos, pa) for pa in ra.repairs)
                        # TODO: Merge expected of pa and pb with .pos == pos
                        return Recovered(list(reps.values()))
                    return ra.expect(expected)
                if type(rb) is Recovered:
                    return rb.expect(expected)
            return Error(pos, False, expected)

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

    def __call__(self, stream: Sequence[T], pos: int, bt: int) -> Result[V_co]:
        return self._fn(stream, pos, bt)


def _make_seq(
        parser: Parser[T, V], second: Parser[T, U],
        fn: Callable[[V, U], X]) -> Parser[T, X]:
    parser_fn = parser.to_fn()
    second_fn = second.to_fn()

    def seq(stream: Sequence[T], pos: int, bt: int) -> Result[X]:
        ra = parser_fn(stream, pos, bt)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return seq_recover(ra, stream)
        va = ra.value
        return second_fn(stream, ra.pos, bt).fmap(
            lambda vb: fn(va, vb)
        ).merge_expected(ra)

    def seq_recover(ra: Recovered[V], stream: Sequence[T]) -> Result[X]:
        reps: Dict[int, Repair[X]] = {}
        for pa in ra.repairs:
            rb = second_fn(stream, pa.pos, -1)
            if type(rb) is Ok:
                if rb.pos not in reps or pa.cost < reps[rb.pos].cost:
                    reps[rb.pos] = Repair(
                        pa.cost, fn(pa.value, rb.value), rb.pos, pa.op,
                        pa.consumed, pa.expected, pa.prefix
                    )
            elif type(rb) is Recovered:
                for pb in rb.repairs:
                    cost = pa.cost + pb.cost
                    if pb.pos not in reps or cost < reps[pb.pos].cost:
                        reps[pb.pos] = Repair(
                            cost, fn(pa.value, pb.value), pb.pos, pb.op, True,
                            pb.expected,
                            Chain(
                                ChainR(
                                    pa.prefix, PrefixItem(pa.op, pa.expected)
                                ),
                                pb.prefix
                            )
                        )
        if reps:
            return Recovered(list(reps.values()))
        pa = next(iter(ra.repairs))
        return Error(pa.op.pos, pa.consumed, pa.expected)

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

    def __call__(self, stream: Sequence[T], pos: int, bt: int) -> Result[V_co]:
        return Ok(self._x, pos, False)


pure = Pure


class PureFn(Parser[T, V_co]):
    def __init__(self, fn: Callable[[], V_co]):
        self._fn = fn

    def __call__(self, stream: Sequence[T], pos: int, bt: int) -> Result[V_co]:
        return Ok(self._fn(), pos, False)


pure_fn = PureFn


class Eof(Parser[T, None]):
    def __call__(self, stream: Sequence[T], pos: int, bt: int) -> Result[None]:
        if pos == len(stream):
            return Ok(None, pos, False)
        if pos > bt:
            skip = len(stream) - pos
            return Recovered([Repair(
                skip, None, len(stream), Skip(skip, pos), False,
                ["end of file"], ()
            )])
        return Error(pos, False, ["end of file"])


eof = Eof


def satisfy(test: Callable[[T], bool]) -> Parser[T, T]:
    def satisfy(stream: Sequence[T], pos: int, bt: int) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if test(t):
                return Ok(t, pos + 1, True)
        if pos > bt:
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if test(t):
                    skip = cur - pos
                    Recovered([Repair(
                        skip, t, cur + 1, Skip(skip, pos), False, (), ()
                    )])
                cur += 1
        return Error(pos, False)

    return FnParser(satisfy)


def sym(s: T) -> Parser[T, T]:
    rs = repr(s)
    expected = [rs]

    def sym(stream: Sequence[T], pos: int, bt: int) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Ok(t, pos + 1, True)
        if pos > bt:
            ins = Repair(1, s, pos, Insert(rs, pos), False, expected, ())
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if t == s:
                    skip = cur - pos
                    return Recovered([
                        ins,
                        Repair(
                            skip, t, cur + 1, Skip(skip, pos), False, expected,
                            ()
                        )
                    ])
                cur += 1
            return Recovered([ins])
        return Error(pos, False, expected)

    return FnParser(sym)


def maybe(parser: Parser[T, V]) -> Parser[T, Optional[V]]:
    fn = parser.to_fn()

    def maybe(stream: Sequence[T], pos: int, bt: int) -> Result[Optional[V]]:
        r = fn(stream, pos, max(pos, bt))
        if r.consumed or type(r) is Ok:
            return r
        return Ok(None, pos, False, r.expected)

    return FnParser(maybe)


def many(parser: Parser[T, V]) -> Parser[T, List[V]]:
    fn = parser.to_fn()

    def many(stream: Sequence[T], pos: int, bt: int) -> Result[List[V]]:
        value: List[V] = []
        tpos = pos
        r = fn(stream, tpos, max(tpos, bt))
        while not type(r) is Error:
            if type(r) is Recovered:
                return many_recover(r, value, stream)
            value.append(r.value)
            tpos = r.pos
            r = fn(stream, tpos, max(tpos, bt))
        if r.consumed:
            return r
        return Ok(value, tpos, pos != tpos, r.expected)

    def many_recover(
            r: Recovered[V], value: List[V],
            stream: Sequence[T]) -> Result[List[V]]:
        reps: Dict[int, Repair[List[V]]] = {}
        for p in r.repairs:
            rb = many(stream, p.pos, -1)
            if type(rb) is Ok:
                if rb.pos not in reps or p.cost < reps[rb.pos].cost:
                    reps[rb.pos] = Repair(
                        p.cost, [*value, p.value, *rb.value], rb.pos, p.op,
                        p.consumed, p.expected, p.prefix
                    )
            elif type(rb) is Recovered:
                for pb in rb.repairs:
                    cost = p.cost + pb.cost
                    if pb.pos not in reps or cost < reps[pb.pos].cost:
                        reps[pb.pos] = Repair(
                            cost, [*value, p.value, *pb.value], pb.pos, pb.op,
                            True, pb.expected,
                            Chain(
                                ChainR(p.prefix, PrefixItem(p.op, p.expected)),
                                pb.prefix
                            )
                        )
            elif not rb.consumed:
                if p.pos not in reps or p.cost < reps[p.pos].cost:
                    reps[rb.pos] = Repair(
                        p.cost, [*value, p.value], rb.pos, p.op, p.consumed,
                        p.expected, p.prefix
                    )
        if reps:
            return Recovered(list(reps.values()))
        p = next(iter(r.repairs))
        return Error(p.op.pos, p.consumed, p.expected)

    return FnParser(many)


def label(parser: Parser[T, V], x: str) -> Parser[T, V]:
    fn = parser.to_fn()
    expected = [x]

    def label(stream: Sequence[T], pos: int, bt: int) -> Result[V]:
        return fn(stream, pos, bt).expect(expected)

    return FnParser(label)


class InsertValue(Parser[T, V_co]):
    def __init__(self, value: V_co, label: str):
        self._value = value
        self._label = label

    def __call__(self, stream: Sequence[T], pos: int, bt: int) -> Result[V_co]:
        if pos > bt:
            return Recovered([Repair(
                1, self._value, pos, Insert(self._label, pos), False,
                [self._label], ()
            )])
        return Error(pos, False)


insert = InsertValue


class Delay(Parser[T, V_co]):
    def __init__(self) -> None:
        def _fn(stream: Sequence[T], pos: int, bt: int) -> Result[V_co]:
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
        return self

    def __call__(self, stream: Sequence[T], pos: int, bt: int) -> Result[V_co]:
        return self._fn(stream, pos, bt)


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
