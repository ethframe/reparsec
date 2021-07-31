from abc import abstractmethod
from dataclasses import dataclass
from itertools import chain
from typing import (
    Callable, Dict, Generic, Iterable, List, NoReturn, Optional, Sequence,
    Tuple, TypeVar, Union
)

T = TypeVar("T")
V = TypeVar("V", bound=object)
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U", bound=object)
X = TypeVar("X", bound=object)


class ParseError(Exception):
    def __init__(self, pos: int, expected: List[str]):
        super().__init__(pos, expected)
        self.pos = pos
        self.expected = expected

    def __str__(self) -> str:
        if not self.expected:
            return "at {}: unexpected input".format(self.pos)
        if len(self.expected) == 1:
            return "at {}: expected {}".format(self.pos, self.expected[0])
        return "at {}: expected {} or {}".format(
            self.pos, ', '.join(self.expected[:-1]), self.expected[-1]
        )


class RepairOp(Generic[T]):
    pass


@dataclass
class Skip(RepairOp[T]):
    count: int
    pos: int
    expected: Iterable[str] = ()


@dataclass
class Insert(RepairOp[T]):
    value: T
    pos: int
    expected: Iterable[str] = ()


@dataclass
class Repair(Generic[T, V_co]):
    cost: int
    value: V_co
    pos: int
    ops: Iterable[RepairOp[T]]


@dataclass
class Ok(Generic[V_co]):
    value: V_co
    pos: int
    expected: Iterable[str] = ()

    def unwrap(self) -> V_co:
        return self.value

    def fmap(self, fn: Callable[[V_co], U]) -> "Ok[U]":
        return Ok(fn(self.value), self.pos, self.expected)

    def expect(self, expected: Iterable[str]) -> "Ok[V_co]":
        return Ok(self.value, self.pos, expected)


@dataclass
class Error:
    pos: int
    expected: Iterable[str] = ()

    def unwrap(self) -> NoReturn:
        self.expected = list(self.expected)
        raise ParseError(self.pos, self.expected)

    def fmap(self, fn: Callable[[V], U]) -> "Error":
        return self

    def expect(self, expected: Iterable[str]) -> "Error":
        return Error(self.pos, expected)


@dataclass
class Recovered(Generic[T, V_co]):
    repairs: Iterable[Repair[T, V_co]]
    pos: int
    expected: Iterable[str] = ()

    def unwrap(self) -> NoReturn:
        self.expected = list(self.expected)
        raise ParseError(self.pos, self.expected)

    def fmap(self, fn: Callable[[V_co], U]) -> "Recovered[T, U]":
        return Recovered(
            [Repair(p.cost, fn(p.value), p.pos, p.ops) for p in self.repairs],
            self.pos, self.expected
        )

    def expect(self, expected: Iterable[str]) -> "Recovered[T, V_co]":
        return Recovered(self.repairs, self.pos, expected)


Result = Union[Recovered[T, V], Ok[V], Error]

ParseFn = Callable[[Sequence[T], int, int], Result[T, V]]


def merge_expected(
        pos: int, ra: Result[T, V], rb: Result[T, U]) -> Iterable[str]:
    if ra.pos != pos and ra.pos != rb.pos:
        return rb.expected
    return chain(ra.expected, rb.expected)


class Parser(Generic[T, V_co]):
    def parse(
            self, stream: Sequence[T],
            recover: bool = False) -> Result[T, V_co]:
        return self(stream, 0, -1 if recover else len(stream))

    @abstractmethod
    def __call__(
            self, stream: Sequence[T], pos: int, bt: int) -> Result[T, V_co]:
        ...

    def to_fn(self) -> ParseFn[T, V_co]:
        return self

    def fmap(self, fn: Callable[[V_co], U]) -> "Parser[T, U]":
        self_fn = self.to_fn()

        def fmap(stream: Sequence[T], pos: int, bt: int) -> Result[T, U]:
            return self_fn(stream, pos, bt).fmap(fn)

        return FnParser(fmap)

    def bind(self, fn: Callable[[V_co], "Parser[T, U]"]) -> "Parser[T, U]":
        self_fn = self.to_fn()

        def bind(stream: Sequence[T], pos: int, bt: int) -> Result[T, U]:
            ra = self_fn(stream, pos, bt)
            if isinstance(ra, Error):
                return ra
            if isinstance(ra, Recovered):
                return bind_recover(ra, stream)
            rb = fn(ra.value)(stream, ra.pos, bt)
            return rb.expect(merge_expected(pos, ra, rb))

        def bind_recover(
                ra: Recovered[T, V_co], stream: Sequence[T]) -> Result[T, U]:
            reps: Dict[int, Repair[T, U]] = {}
            for pa in ra.repairs:
                rb = fn(pa.value)(stream, pa.pos, -1)
                if isinstance(rb, Ok):
                    if rb.pos not in reps or pa.cost < reps[rb.pos].cost:
                        reps[rb.pos] = Repair(
                            pa.cost, rb.value, rb.pos, pa.ops)
                elif isinstance(rb, Recovered):
                    pa_ops = list(pa.ops)
                    for pb in rb.repairs:
                        cost = pa.cost + pb.cost
                        if pb.pos not in reps or cost < reps[pb.pos].cost:
                            reps[pb.pos] = Repair(
                                cost, pb.value, pb.pos, chain(pa_ops, pb.ops)
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

        def or_(stream: Sequence[T], pos: int, bt: int) -> Result[T, V_co]:
            ra = self_fn(stream, pos, max(pos, bt))
            if ra.pos != pos:
                return ra
            rb = other_fn(stream, pos, max(pos, bt))
            if rb.pos != pos:
                return rb
            expected = chain(ra.expected, rb.expected)
            if isinstance(ra, Ok):
                return Ok(ra.value, pos, expected)
            if isinstance(rb, Ok):
                return Ok(rb.value, pos, expected)
            if pos > bt:
                ra = self_fn(stream, pos, -1)
                rb = other_fn(stream, pos, -1)
                if isinstance(ra, Recovered):
                    if isinstance(rb, Recovered):
                        reps = {pa.pos: pa for pa in ra.repairs}
                        for pb in rb.repairs:
                            reps.setdefault(pb.pos, pb)
                        return Recovered(list(reps.values()), ra.pos, expected)
                    return Recovered(ra.repairs, ra.pos, expected)
                if isinstance(rb, Recovered):
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

    def __call__(
            self, stream: Sequence[T], pos: int, bt: int) -> Result[T, V_co]:
        return self._fn(stream, pos, bt)


class Pure(Parser[T, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def __call__(
            self, stream: Sequence[T], pos: int, bt: int) -> Result[T, V_co]:
        return Ok(self._x, pos)


pure = Pure


class PureFn(Parser[T, V_co]):
    def __init__(self, fn: Callable[[], V_co]):
        self._fn = fn

    def __call__(
            self, stream: Sequence[T], pos: int, bt: int) -> Result[T, V_co]:
        return Ok(self._fn(), pos)


pure_fn = PureFn


class Eof(Parser[T, None]):
    def __call__(
            self, stream: Sequence[T], pos: int, bt: int) -> Result[T, None]:
        if pos == len(stream):
            return Ok(None, pos)
        if pos > bt:
            skip = len(stream) - pos
            return Recovered([Repair(
                skip, None, len(stream), [Skip(skip, pos, ["end of file"])]
            )], pos, ["end of file"])
        return Error(pos, ["end of file"])


eof = Eof


def satisfy(test: Callable[[T], bool]) -> Parser[T, T]:
    def satisfy(stream: Sequence[T], pos: int, bt: int) -> Result[T, T]:
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
    expected = [repr(s)]

    def sym(stream: Sequence[T], pos: int, bt: int) -> Result[T, T]:
        if pos < len(stream):
            t = stream[pos]
            if t == s:
                return Ok(t, pos + 1)
        if pos > bt:
            ins = Repair(1, s, pos, [Insert(s, pos, expected)])
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


def lseq(parser: Parser[T, V], second: Parser[T, U]) -> Parser[T, V]:
    return parser.bind(lambda l: second.fmap(lambda _: l))


def rseq(parser: Parser[T, V], second: Parser[T, U]) -> Parser[T, U]:
    return parser.bind(lambda _: second.fmap(lambda r: r))


def seq(parser: Parser[T, V], second: Parser[T, U]) -> Parser[T, Tuple[V, U]]:
    return parser.bind(lambda l: second.fmap(lambda r: (l, r)))


def maybe(parser: Parser[T, V]) -> Parser[T, Optional[V]]:
    fn = parser.to_fn()

    def maybe(
            stream: Sequence[T], pos: int, bt: int) -> Result[T, Optional[V]]:
        r = fn(stream, pos, max(pos, bt))
        if r.pos != pos or isinstance(r, Ok):
            return r
        return Ok(None, pos, r.expected)

    return FnParser(maybe)


def many(parser: Parser[T, V]) -> Parser[T, List[V]]:
    fn = parser.to_fn()

    recovery_parser: Delay[T, List[V]] = Delay()
    recovery_parser.define(
        (parser + recovery_parser).fmap(lambda v: [v[0]] + v[1]) |
        pure_fn(lambda: [])
    )

    def many(stream: Sequence[T], pos: int, bt: int) -> Result[T, List[V]]:
        value: List[V] = []
        r = fn(stream, pos, max(pos, bt))
        while not isinstance(r, Error):
            if isinstance(r, Recovered):
                return many_recover(r, value, stream)
            value.append(r.value)
            pos = r.pos
            r = parser(stream, pos, max(pos, bt))
        if r.pos != pos:
            return r
        return Ok(value, pos, r.expected)

    def many_recover(
            r: Recovered[T, V], value: List[V],
            stream: Sequence[T]) -> Result[T, List[V]]:
        reps: Dict[int, Repair[T, List[V]]] = {}
        for p in r.repairs:
            rb = recovery_parser(stream, p.pos, -1)
            if isinstance(rb, Ok):
                if rb.pos not in reps or p.cost < reps[rb.pos].cost:
                    pv = [*value, p.value, *rb.value]
                    reps[rb.pos] = Repair(p.cost, pv, rb.pos, p.ops)
            elif isinstance(rb, Recovered):
                p_ops = list(p.ops)
                for pb in rb.repairs:
                    cost = p.cost + pb.cost
                    if pb.pos not in reps or cost < reps[pb.pos].cost:
                        pv = [*value, p.value, *pb.value]
                        reps[pb.pos] = Repair(
                            cost, pv, pb.pos, chain(p_ops, pb.ops)
                        )
            elif rb.pos == p.pos:
                if p.pos not in reps or p.cost < reps[p.pos].cost:
                    pv = [*value, p.value]
                    reps[rb.pos] = Repair(p.cost, pv, p.pos, p.ops)
        if reps:
            return Recovered(list(reps.values()), r.pos, r.expected)
        return Error(r.pos, r.expected)

    return FnParser(many)


def label(parser: Parser[T, V], x: str) -> Parser[T, V]:
    fn = parser.to_fn()
    expected = [x]

    def label(stream: Sequence[T], pos: int, bt: int) -> Result[T, V]:
        r = fn(stream, pos, bt)
        if r.pos != pos:
            return r
        return r.expect(expected)

    return FnParser(label)


def insert(s: T) -> Parser[T, T]:
    expected = [repr(s)]

    def insert(sequence: Sequence[T], pos: int, bt: int) -> Result[T, T]:
        if pos > bt:
            return Recovered(
                [Repair(1, s, pos, [Insert(s, pos, expected)])], pos
            )
        return Error(pos)

    return FnParser(insert)


class Delay(Parser[T, V_co]):
    def __init__(self) -> None:
        def _fn(stream: Sequence[T], pos: int, bt: int) -> Result[T, V_co]:
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

    def __call__(
            self, stream: Sequence[T], pos: int, bt: int) -> Result[T, V_co]:
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
