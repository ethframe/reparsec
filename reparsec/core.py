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


ParseFn = Callable[[Sequence[T], int, RecoveryMode], Result[V_co]]


class ParseObj(Generic[T, V_co]):
    @abstractmethod
    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        ...

    def to_fn(self) -> ParseFn[T, V_co]:
        return self.parse_fn


def fmap(parse_fn: ParseFn[T, V], fn: Callable[[V], U]) -> ParseFn[T, U]:
    def fmap(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[U]:
        return parse_fn(stream, pos, rm).fmap(fn)
    return fmap


def or_(parse_fn: ParseFn[T, V], second_fn: ParseFn[T, V]) -> ParseFn[T, V]:
    def or_(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[V]:
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
                    reps = {pb.pos: pb for pb in rb.repairs}
                    reps.update((pa.pos, pa) for pa in ra.repairs)
                    return Recovered(list(reps.values()))
                return ra.expect(expected)
            if type(rb) is Recovered:
                return rb.expect(expected)
        return Error(pos, expected)

    return or_


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
        parse_fn: ParseFn[T, V],
        fn: Callable[[V], ParseObj[T, U]]) -> ParseFn[T, U]:
    def bind(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[U]:
        ra = parse_fn(stream, pos, rm)
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

    return bind


def _make_seq(
        parse_fn: ParseFn[T, V], second_fn: ParseFn[T, U],
        fn: Callable[[V, U], X]) -> ParseFn[T, X]:
    def seq(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[X]:
        ra = parse_fn(stream, pos, rm)
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

    return seq


def lseq(parse_fn: ParseFn[T, V], second_fn: ParseFn[T, U]) -> ParseFn[T, V]:
    return _make_seq(parse_fn, second_fn, lambda l, _: l)


def rseq(parse_fn: ParseFn[T, V], second_fn: ParseFn[T, U]) -> ParseFn[T, U]:
    return _make_seq(parse_fn, second_fn, lambda _, r: r)


def seq(
        parse_fn: ParseFn[T, V],
        second_fn: ParseFn[T, U]) -> ParseFn[T, Tuple[V, U]]:
    return _make_seq(parse_fn, second_fn, lambda l, r: (l, r))


class Pure(ParseObj[T, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        return Ok(self._x, pos)


pure = Pure


class PureFn(ParseObj[T, V_co]):
    def __init__(self, fn: Callable[[], V_co]):
        self._fn = fn

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        return Ok(self._fn(), pos)


pure_fn = PureFn


class Eof(ParseObj[T, None]):
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


def satisfy(test: Callable[[T], bool]) -> ParseFn[T, T]:
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
                    return Recovered(
                        [Repair(skip, t, cur + 1, Skip(skip, pos))]
                    )
                cur += 1
        return Error(pos)

    return satisfy


def sym(s: T) -> ParseFn[T, T]:
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

    return sym


def maybe(parse_fn: ParseFn[T, V]) -> ParseFn[T, Optional[V]]:
    def maybe(
            stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[Optional[V]]:
        r = parse_fn(stream, pos, disallow_recovery(rm))
        if r.consumed is True or type(r) is Ok:
            return r
        return Ok(None, pos, r.expected)

    return maybe


def many(parse_fn: ParseFn[T, V]) -> ParseFn[T, List[V]]:
    def many(
            stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[List[V]]:
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

    def parse(stream: Sequence[T], p: Repair[V]) -> Result[List[V]]:
        r = many(stream, p.pos, True)
        if type(r) is Error and r.consumed is False:
            return Ok[List[V]]([], r.pos, r.expected)
        return r

    return many


def label(parse_fn: ParseFn[T, V], x: str) -> ParseFn[T, V]:
    expected = [x]

    def label(stream: Sequence[T], pos: int, rm: RecoveryMode) -> Result[V]:
        return parse_fn(stream, pos, rm).expect(expected)

    return label


class RecoverValue(ParseObj[T, V_co]):
    def __init__(self, x: V_co, expected: Optional[str] = None):
        self._x = x
        self._label = repr(x)
        self._expected = [] if expected is None else [expected]

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        if rm:
            return Recovered([Repair(
                1, self._x, pos, Insert(self._label, pos), self._expected
            )])
        return Error(pos)


recover_value = RecoverValue


class RecoverFn(ParseObj[T, V_co]):
    def __init__(self, fn: Callable[[], V_co], expected: Optional[str] = None):
        self._fn = fn
        self._expected = [] if expected is None else [expected]

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        if rm:
            x = self._fn()
            return Recovered([
                Repair(1, x, pos, Insert(repr(x), pos), self._expected)
            ])
        return Error(pos)


recover_fn = RecoverFn


class Delay(ParseObj[T, V_co]):
    def __init__(self) -> None:
        def _fn(
                stream: Sequence[T], pos: int,
                rm: RecoveryMode) -> Result[V_co]:
            raise RuntimeError("Delayed parser was not defined")

        self._defined = False
        self._fn: ParseFn[T, V_co] = _fn

    def define_fn(self, parse_fn: ParseFn[T, V_co]) -> None:
        if self._defined:
            raise RuntimeError("Delayed parser was already defined")
        self._defined = True
        self._fn = parse_fn

    def to_fn(self) -> ParseFn[T, V_co]:
        if self._defined:
            return self._fn
        return super().to_fn()

    def parse_fn(
            self, stream: Sequence[T], pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        return self._fn(stream, pos, rm)
