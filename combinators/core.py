from abc import abstractmethod
from typing import (
    Callable, Dict, Generic, List, Optional, Sequence, Tuple, TypeVar
)

from .chain import Chain, ChainL, ChainR
from .result import (
    Error, Insert, Ok, Recovered, Repair, Result, Skip, merge_expected
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
            rb = fn(ra.value)(stream, ra.pos, bt)
            return rb.expect(merge_expected(pos, ra, rb))

        def bind_recover(
                ra: Recovered[V_co], stream: Sequence[T]) -> Result[U]:
            reps: Dict[int, Repair[U]] = {}
            for pa in ra.repairs:
                rb = fn(pa.value)(stream, pa.pos, -1)
                if type(rb) is Ok:
                    if rb.pos not in reps or pa.cost < reps[rb.pos].cost:
                        reps[rb.pos] = Repair(
                            pa.cost, rb.value, rb.pos, pa.ops, pa.errors
                        )
                elif type(rb) is Recovered:
                    for pb in rb.repairs:
                        cost = pa.cost + pb.cost
                        if pb.pos not in reps or cost < reps[pb.pos].cost:
                            reps[pb.pos] = Repair(
                                cost, pb.value, pb.pos, Chain(pa.ops, pb.ops),
                                Chain(pa.errors, ChainL(
                                    rb.expected, pb.errors))
                            )
            if reps:
                return Recovered(list(reps.values()), ra.pos, ra.expected)
            return Error(ra.pos, ra.expected)

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
            if ra.pos != pos:
                return ra
            rb = other_fn(stream, pos, max(pos, bt))
            if rb.pos != pos:
                return rb
            expected = Chain(ra.expected, rb.expected)
            if type(ra) is Ok:
                return Ok(ra.value, pos, expected)
            if type(rb) is Ok:
                return Ok(rb.value, pos, expected)
            if pos > bt:
                ra = self_fn(stream, pos, -1)
                rb = other_fn(stream, pos, -1)
                if type(ra) is Recovered:
                    if type(rb) is Recovered:
                        reps = {pb.pos: pb for pb in rb.repairs}
                        reps.update((pa.pos, pa) for pa in ra.repairs)
                        return Recovered(list(reps.values()), ra.pos, expected)
                    return Recovered(ra.repairs, ra.pos, expected)
                if type(rb) is Recovered:
                    return Recovered(rb.repairs, ra.pos, expected)
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
        rb = second_fn(stream, ra.pos, bt)
        return rb.fmap(lambda vb: fn(va, vb)).expect(
            merge_expected(pos, ra, rb)
        )

    def seq_recover(ra: Recovered[V], stream: Sequence[T]) -> Result[X]:
        reps: Dict[int, Repair[X]] = {}
        for pa in ra.repairs:
            rb = second_fn(stream, pa.pos, -1)
            if type(rb) is Ok:
                if rb.pos not in reps or pa.cost < reps[rb.pos].cost:
                    reps[rb.pos] = Repair(
                        pa.cost, fn(
                            pa.value, rb.value), rb.pos, pa.ops, pa.errors
                    )
            elif type(rb) is Recovered:
                for pb in rb.repairs:
                    cost = pa.cost + pb.cost
                    if pb.pos not in reps or cost < reps[pb.pos].cost:
                        reps[pb.pos] = Repair(
                            cost, fn(pa.value, pb.value), pb.pos,
                            Chain(pa.ops, pb.ops),
                            Chain(pa.errors, ChainL(rb.expected, pb.errors))
                        )
        if reps:
            return Recovered(list(reps.values()), ra.pos, ra.expected)
        return Error(ra.pos, ra.expected)

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
        return Ok(self._x, pos)


pure = Pure


class PureFn(Parser[T, V_co]):
    def __init__(self, fn: Callable[[], V_co]):
        self._fn = fn

    def __call__(self, stream: Sequence[T], pos: int, bt: int) -> Result[V_co]:
        return Ok(self._fn(), pos)


pure_fn = PureFn


class Eof(Parser[T, None]):
    def __call__(self, stream: Sequence[T], pos: int, bt: int) -> Result[None]:
        if pos == len(stream):
            return Ok(None, pos)
        if pos > bt:
            skip = len(stream) - pos
            return Recovered([Repair(
                skip, None, len(stream), [Skip(skip, pos)], ()
            )], pos, ["end of file"])
        return Error(pos, ["end of file"])


eof = Eof


def satisfy(test: Callable[[T], bool]) -> Parser[T, T]:
    def satisfy(stream: Sequence[T], pos: int, bt: int) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if test(t):
                return Ok(t, pos + 1)
        if pos > bt:
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if test(t):
                    skip = cur - pos
                    return Recovered(
                        [Repair(skip, t, cur + 1, [Skip(skip, pos)])], pos
                    )
                cur += 1
        return Error(pos)

    return FnParser(satisfy)


def sym(s: T) -> Parser[T, T]:
    rs = repr(s)
    expected = [rs]

    def sym(stream: Sequence[T], pos: int, bt: int) -> Result[T]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Ok(t, pos + 1)
        if pos > bt:
            ins = Repair(1, s, pos, [Insert(rs, pos)])
            cur = pos + 1
            while cur < len(stream):
                t = stream[cur]
                if t == s:
                    skip = cur - pos
                    return Recovered(
                        [ins, Repair(skip, t, cur + 1, [Skip(skip, pos)])],
                        pos, expected
                    )
                cur += 1
            return Recovered([ins], pos, expected)
        return Error(pos, expected)

    return FnParser(sym)


def maybe(parser: Parser[T, V]) -> Parser[T, Optional[V]]:
    fn = parser.to_fn()

    def maybe(stream: Sequence[T], pos: int, bt: int) -> Result[Optional[V]]:
        r = fn(stream, pos, max(pos, bt))
        if r.pos != pos or type(r) is Ok:
            return r
        return Ok(None, pos, r.expected)

    return FnParser(maybe)


def many(parser: Parser[T, V]) -> Parser[T, List[V]]:
    fn = parser.to_fn()

    def many(stream: Sequence[T], pos: int, bt: int) -> Result[List[V]]:
        value: List[V] = []
        r = fn(stream, pos, max(pos, bt))
        while not type(r) is Error:
            if type(r) is Recovered:
                return many_recover(r, value, stream)
            value.append(r.value)
            pos = r.pos
            r = fn(stream, pos, max(pos, bt))
        if r.pos != pos:
            return r
        return Ok(value, pos, r.expected)

    def many_recover(
            r: Recovered[V], value: List[V],
            stream: Sequence[T]) -> Result[List[V]]:
        reps: Dict[int, Repair[List[V]]] = {}
        for p in r.repairs:
            rb = many(stream, p.pos, -1)
            if type(rb) is Ok:
                if rb.pos not in reps or p.cost < reps[rb.pos].cost:
                    pv = [*value, p.value, *rb.value]
                    reps[rb.pos] = Repair(p.cost, pv, rb.pos, p.ops, p.errors)
            elif type(rb) is Recovered:
                for pb in rb.repairs:
                    cost = p.cost + pb.cost
                    if pb.pos not in reps or cost < reps[pb.pos].cost:
                        pv = [*value, p.value, *pb.value]
                        reps[pb.pos] = Repair(
                            cost, pv, pb.pos, Chain(p.ops, pb.ops),
                            Chain(p.errors, ChainL(rb.expected, pb.errors))
                        )
            elif rb.pos == p.pos:
                if p.pos not in reps or p.cost < reps[p.pos].cost:
                    pv = [*value, p.value]
                    reps[rb.pos] = Repair(
                        p.cost, pv, p.pos, p.ops, ChainR(p.errors, rb.expected)
                    )
        if reps:
            return Recovered(list(reps.values()), r.pos, r.expected)
        return Error(r.pos, r.expected)

    return FnParser(many)


def label(parser: Parser[T, V], x: str) -> Parser[T, V]:
    fn = parser.to_fn()
    expected = [x]

    def label(stream: Sequence[T], pos: int, bt: int) -> Result[V]:
        r = fn(stream, pos, bt)
        if r.pos != pos:
            return r
        return r.expect(expected)

    return FnParser(label)


class InsertValue(Parser[T, V_co]):
    def __init__(self, value: V_co, label: str):
        self._value = value
        self._label = label

    def __call__(self, stream: Sequence[T], pos: int, bt: int) -> Result[V_co]:
        if pos > bt:
            return Recovered([Repair(
                1, self._value, pos, [Insert(self._label, pos)]
            )], pos, [self._label])
        return Error(pos)


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
