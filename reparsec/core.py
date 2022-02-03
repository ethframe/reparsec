from abc import abstractmethod
from typing import (
    Callable, Dict, Generic, List, Literal, Optional, Tuple, TypeVar
)

from .chain import Chain, ChainL
from .result import Error, Insert, Ok, PrefixItem, Recovered, Repair, Result

S = TypeVar("S", bound=object)
S_contra = TypeVar("S_contra", contravariant=True)
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


ParseFn = Callable[[S_contra, int, RecoveryMode], Result[V_co]]


class ParseObj(Generic[S_contra, V_co]):
    @abstractmethod
    def parse_fn(
            self, stream: S_contra, pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        ...

    def to_fn(self) -> ParseFn[S_contra, V_co]:
        return self.parse_fn


def fmap(parse_fn: ParseFn[S, V], fn: Callable[[V], U]) -> ParseFn[S, U]:
    def fmap(stream: S, pos: int, rm: RecoveryMode) -> Result[U]:
        return parse_fn(stream, pos, rm).fmap(fn)
    return fmap


def or_(parse_fn: ParseFn[S, V], second_fn: ParseFn[S, V]) -> ParseFn[S, V]:
    def or_(stream: S, pos: int, rm: RecoveryMode) -> Result[V]:
        ra = parse_fn(stream, pos, disallow_recovery(rm))
        if ra.consumed is True:
            return ra
        rb = second_fn(stream, pos, disallow_recovery(rm))
        if rb.consumed is True:
            return rb
        expected = Chain(ra.expected, rb.expected)
        if type(ra) is Ok:
            return ra.expect(expected)
        if type(rb) is Ok:
            return rb.expect(expected)
        if rm:
            ra = parse_fn(stream, pos, True)
            rb = second_fn(stream, pos, True)
            if type(ra) is Recovered:
                if type(rb) is Recovered:
                    return Recovered({**rb.repairs, **ra.repairs})
                return ra.expect(expected)
            if type(rb) is Recovered:
                return rb.expect(expected)
        return Error(pos, expected)

    return or_


def _continue_parse(
        stream: S, ra: Recovered[V],
        parse: Callable[[S, int, Repair[V]], Result[U]],
        merge: Callable[[V, U], X]) -> Result[X]:
    reps: Dict[int, Repair[X]] = {}
    for p, pa in ra.repairs.items():
        rb = parse(stream, p, pa)
        if type(rb) is Ok:
            if rb.pos not in reps or pa.cost < reps[rb.pos].cost:
                reps[rb.pos] = Repair(
                    pa.cost, merge(pa.value, rb.value), pa.op, pa.expected,
                    pa.consumed, pa.prefix
                )
        elif type(rb) is Recovered:
            for p, pb in rb.repairs.items():
                cost = pa.cost + pb.cost
                if p not in reps or cost < reps[p].cost:
                    reps[p] = Repair(
                        cost, merge(pa.value, pb.value), pb.op, pb.expected,
                        True,
                        Chain(
                            pa.prefix,
                            ChainL(PrefixItem(pa.op, pa.expected), pb.prefix)
                        )
                    )
    if reps:
        return Recovered(reps)
    return ra.to_error()


def bind(
        parse_fn: ParseFn[S, V],
        fn: Callable[[V], ParseObj[S, U]]) -> ParseFn[S, U]:
    def bind(stream: S, pos: int, rm: RecoveryMode) -> Result[U]:
        ra = parse_fn(stream, pos, rm)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return _continue_parse(
                stream, ra, lambda s, i, p: fn(p.value).parse_fn(s, i, True),
                lambda _, v: v
            )
        return fn(ra.value).parse_fn(
            stream, ra.pos, maybe_allow_recovery(rm, ra)
        ).merge_expected(ra.expected, ra.consumed)

    return bind


def _make_seq(
        parse_fn: ParseFn[S, V], second_fn: ParseFn[S, U],
        fn: Callable[[V, U], X]) -> ParseFn[S, X]:
    def seq(stream: S, pos: int, rm: RecoveryMode) -> Result[X]:
        ra = parse_fn(stream, pos, rm)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return _continue_parse(
                stream, ra, lambda s, i, p: second_fn(s, i, True), fn
            )
        va = ra.value
        return second_fn(stream, ra.pos, maybe_allow_recovery(rm, ra)).fmap(
            lambda vb: fn(va, vb)
        ).merge_expected(ra.expected, ra.consumed)

    return seq


def lseq(parse_fn: ParseFn[S, V], second_fn: ParseFn[S, U]) -> ParseFn[S, V]:
    return _make_seq(parse_fn, second_fn, lambda l, _: l)


def rseq(parse_fn: ParseFn[S, V], second_fn: ParseFn[S, U]) -> ParseFn[S, U]:
    return _make_seq(parse_fn, second_fn, lambda _, r: r)


def seq(
        parse_fn: ParseFn[S, V],
        second_fn: ParseFn[S, U]) -> ParseFn[S, Tuple[V, U]]:
    return _make_seq(parse_fn, second_fn, lambda l, r: (l, r))


class Pure(ParseObj[S, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def parse_fn(self, stream: S, pos: int, rm: RecoveryMode) -> Result[V_co]:
        return Ok(self._x, pos)


pure = Pure


class PureFn(ParseObj[S, V_co]):
    def __init__(self, fn: Callable[[], V_co]):
        self._fn = fn

    def parse_fn(self, stream: S, pos: int, rm: RecoveryMode) -> Result[V_co]:
        return Ok(self._fn(), pos)


pure_fn = PureFn


def maybe(parse_fn: ParseFn[S, V]) -> ParseFn[S, Optional[V]]:
    def maybe(stream: S, pos: int, rm: RecoveryMode) -> Result[Optional[V]]:
        r = parse_fn(stream, pos, disallow_recovery(rm))
        if r.consumed is True or type(r) is Ok:
            return r
        return Ok(None, pos, r.expected)

    return maybe


def many(parse_fn: ParseFn[S, V]) -> ParseFn[S, List[V]]:
    def many(stream: S, pos: int, rm: RecoveryMode) -> Result[List[V]]:
        rm = disallow_recovery(rm)
        consumed = False
        value: List[V] = []
        r = parse_fn(stream, pos, rm)
        while type(r) is Ok:
            consumed |= r.consumed
            value.append(r.value)
            r = parse_fn(stream, r.pos, rm)
        if type(r) is Recovered:
            return _continue_parse(
                stream, r, parse, lambda a, b: [*value, a, *b]
            )
        if r.consumed:
            return r
        return Ok(value, r.pos, r.expected, consumed)

    def parse(stream: S, pos: int, p: Repair[V]) -> Result[List[V]]:
        r = many(stream, pos, True)
        if type(r) is Error and r.consumed is False:
            return Ok[List[V]]([], r.pos, r.expected)
        return r

    return many


def label(parse_fn: ParseFn[S, V], x: str) -> ParseFn[S, V]:
    expected = [x]

    def label(stream: S, pos: int, rm: RecoveryMode) -> Result[V]:
        return parse_fn(stream, pos, rm).expect(expected)

    return label


class RecoverValue(ParseObj[S, V_co]):
    def __init__(self, x: V_co, expected: Optional[str] = None):
        self._x = x
        self._label = repr(x)
        self._expected = [] if expected is None else [expected]

    def parse_fn(self, stream: S, pos: int, rm: RecoveryMode) -> Result[V_co]:
        if rm:
            return Recovered({
                pos: Repair(
                    1, self._x, Insert(self._label, pos), self._expected
                )
            })
        return Error(pos)


recover_value = RecoverValue


class RecoverFn(ParseObj[S, V_co]):
    def __init__(self, fn: Callable[[], V_co], expected: Optional[str] = None):
        self._fn = fn
        self._expected = [] if expected is None else [expected]

    def parse_fn(self, stream: S, pos: int, rm: RecoveryMode) -> Result[V_co]:
        if rm:
            x = self._fn()
            return Recovered({
                pos: Repair(1, x, Insert(repr(x), pos), self._expected)
            })
        return Error(pos)


recover_fn = RecoverFn


class Delay(ParseObj[S, V_co]):
    def __init__(self) -> None:
        def _fn(stream: S, pos: int, rm: RecoveryMode) -> Result[V_co]:
            raise RuntimeError("Delayed parser was not defined")

        self._defined = False
        self._fn: ParseFn[S, V_co] = _fn

    def define_fn(self, parse_fn: ParseFn[S, V_co]) -> None:
        if self._defined:
            raise RuntimeError("Delayed parser was already defined")
        self._defined = True
        self._fn = parse_fn

    def to_fn(self) -> ParseFn[S, V_co]:
        if self._defined:
            return self._fn
        return super().to_fn()

    def parse_fn(self, stream: S, pos: int, rm: RecoveryMode) -> Result[V_co]:
        return self._fn(stream, pos, rm)
