from typing import Callable, List, Optional, Tuple, TypeVar, Union

from .chain import Append
from .parser import ParseFn, ParseObj
from .recovery import MergeFn, continue_parse, join_repairs
from .repair import make_insert
from .result import Error, Ok, Recovered, Result
from .types import Ctx, RecoveryMode, disallow_recovery, maybe_allow_recovery

S = TypeVar("S")
V = TypeVar("V")
U = TypeVar("U")
X = TypeVar("X")


def fmap(parse_fn: ParseFn[S, V], fn: Callable[[V], U]) -> ParseFn[S, U]:
    def fmap(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[U, S]:
        return parse_fn(stream, pos, ctx, rm).fmap(fn)
    return fmap


def alt(
        parse_fn: ParseFn[S, V],
        second_fn: ParseFn[S, U]) -> ParseFn[S, Union[V, U]]:
    def alt(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[Union[V, U], S]:
        ra = parse_fn(stream, pos, ctx, disallow_recovery(rm))
        if type(ra) is Ok or ra.consumed:
            return ra
        rb = second_fn(stream, pos, ctx, disallow_recovery(rm))
        if rb.consumed:
            return rb
        expected = Append(ra.expected, rb.expected)
        if type(rb) is Ok:
            return rb.set_expected(expected)
        if rm:
            rra = parse_fn(stream, pos, ctx, rm)
            rrb = second_fn(stream, pos, ctx, rm)
            if type(rra) is Recovered:
                if type(rrb) is Recovered:
                    return join_repairs(rra, rrb).set_expected(expected)
                return rra.set_expected(expected)
            if type(rrb) is Recovered:
                return rrb.set_expected(expected)
        return Error(ra.loc, expected)

    return alt


def bind(
        parse_fn: ParseFn[S, V],
        fn: Callable[[V], ParseObj[S, U]]) -> ParseFn[S, U]:
    def bind(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[U, S]:
        ra = parse_fn(stream, pos, ctx, rm)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return continue_parse(
                stream, ra, rm,
                lambda v, s, p, c, r: fn(v).parse_fn(s, p, c, r),
                lambda _, v: v
            )
        return fn(ra.value).parse_fn(
            stream, ra.pos, ra.ctx, maybe_allow_recovery(ctx, rm, ra.consumed)
        ).prepend_expected(ra.expected, ra.consumed)

    return bind


def _seq(
        parse_fn: ParseFn[S, V], second_fn: ParseFn[S, U],
        merge: MergeFn[V, U, X]) -> ParseFn[S, X]:
    def seq(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[X, S]:
        ra = parse_fn(stream, pos, ctx, rm)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return continue_parse(
                stream, ra, rm, lambda _, s, p, c, r: second_fn(s, p, c, r),
                merge
            )
        va = ra.value
        return second_fn(
            stream, ra.pos, ra.ctx, maybe_allow_recovery(ctx, rm, ra.consumed)
        ).fmap(
            lambda vb: merge(va, vb)
        ).prepend_expected(ra.expected, ra.consumed)

    return seq


def seql(
        parse_fn: ParseFn[S, V],
        second_fn: ParseFn[S, U]) -> ParseFn[S, V]:
    return _seq(parse_fn, second_fn, lambda l, _: l)


def seqr(
        parse_fn: ParseFn[S, V],
        second_fn: ParseFn[S, U]) -> ParseFn[S, U]:
    return _seq(parse_fn, second_fn, lambda _, r: r)


def seq(
        parse_fn: ParseFn[S, V],
        second_fn: ParseFn[S, U]) -> ParseFn[S, Tuple[V, U]]:
    return _seq(parse_fn, second_fn, lambda l, r: (l, r))


V0 = TypeVar("V0")
V1 = TypeVar("V1")
V2 = TypeVar("V2")
V3 = TypeVar("V3")
V4 = TypeVar("V4")
V5 = TypeVar("V5")
V6 = TypeVar("V6")
V7 = TypeVar("V7")


def tuple3(
        parse_fn: ParseFn[S, Tuple[V0, V1]],
        second_fn: ParseFn[S, V2]) -> ParseFn[S, Tuple[V0, V1, V2]]:
    def merge(a: Tuple[V0, V1], b: V2) -> Tuple[V0, V1, V2]:
        return (*a, b)
    return _seq(parse_fn, second_fn, merge)


def tuple4(
        parse_fn: ParseFn[S, Tuple[V0, V1, V2]],
        second_fn: ParseFn[S, V3]) -> ParseFn[S, Tuple[V0, V1, V2, V3]]:
    def merge(a: Tuple[V0, V1, V2], b: V3) -> Tuple[V0, V1, V2, V3]:
        return (*a, b)
    return _seq(parse_fn, second_fn, merge)


def tuple5(
        parse_fn: ParseFn[S, Tuple[V0, V1, V2, V3]],
        second_fn: ParseFn[S, V4]) -> ParseFn[S, Tuple[V0, V1, V2, V3, V4]]:
    def merge(a: Tuple[V0, V1, V2, V3], b: V4) -> Tuple[V0, V1, V2, V3, V4]:
        return (*a, b)
    return _seq(parse_fn, second_fn, merge)


def tuple6(
        parse_fn: ParseFn[S, Tuple[V0, V1, V2, V3, V4]],
        second_fn: ParseFn[S, V5]) -> ParseFn[
            S, Tuple[V0, V1, V2, V3, V4, V5]]:
    def merge(
            a: Tuple[V0, V1, V2, V3, V4],
            b: V5) -> Tuple[V0, V1, V2, V3, V4, V5]:
        return (*a, b)
    return _seq(parse_fn, second_fn, merge)


def tuple7(
        parse_fn: ParseFn[S, Tuple[V0, V1, V2, V3, V4, V5]],
        second_fn: ParseFn[S, V6]) -> ParseFn[
            S, Tuple[V0, V1, V2, V3, V4, V5, V6]]:
    def merge(
            a: Tuple[V0, V1, V2, V3, V4, V5],
            b: V6) -> Tuple[V0, V1, V2, V3, V4, V5, V6]:
        return (*a, b)
    return _seq(parse_fn, second_fn, merge)


def tuple8(
        parse_fn: ParseFn[S, Tuple[V0, V1, V2, V3, V4, V5, V6]],
        second_fn: ParseFn[S, V7]) -> ParseFn[
            S, Tuple[V0, V1, V2, V3, V4, V5, V6, V7]]:
    def merge(
            a: Tuple[V0, V1, V2, V3, V4, V5, V6],
            b: V7) -> Tuple[V0, V1, V2, V3, V4, V5, V6, V7]:
        return (*a, b)
    return _seq(parse_fn, second_fn, merge)


def maybe(parse_fn: ParseFn[S, V]) -> ParseFn[S, Optional[V]]:
    def maybe(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[Optional[V], S]:
        r = parse_fn(stream, pos, ctx, disallow_recovery(rm))
        if r.consumed or type(r) is Ok:
            return r
        return Ok(None, pos, ctx, r.expected)

    return maybe


def many(parse_fn: ParseFn[S, V]) -> ParseFn[S, List[V]]:
    def many(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[List[V], S]:
        rm = disallow_recovery(rm)
        consumed = False
        value: List[V] = []
        r = parse_fn(stream, pos, ctx, rm)
        while type(r) is Ok:
            if not r.consumed:
                raise RuntimeError("parser shouldn't accept empty string")
            consumed = True
            value.append(r.value)
            pos = r.pos
            ctx = r.ctx
            r = parse_fn(stream, pos, ctx, rm)
        if type(r) is Recovered:
            return continue_parse(
                stream, r, rm, parse, lambda a, b: [*value, a, *b]
            )
        if r.consumed:
            return r
        return Ok(value, pos, ctx, r.expected, consumed)

    def parse(
            _: V, stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[List[V], S]:
        r = many(stream, pos, ctx, rm)
        if type(r) is Error and not r.consumed:
            return Ok[List[V], S]([], pos, ctx, r.expected)
        return r

    return many


def attempt(
        parse_fn: ParseFn[S, V]) -> ParseFn[S, V]:
    def attempt(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[V, S]:
        if rm:
            return parse_fn(stream, pos, ctx, rm)
        r = parse_fn(stream, pos, ctx, None)
        if type(r) is Error:
            return Error(r.loc, r.expected)
        return r

    return attempt


def label(parse_fn: ParseFn[S, V], x: str) -> ParseFn[S, V]:
    expected = [x]

    def label(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[V, S]:
        return parse_fn(stream, pos, ctx, rm).set_expected(expected)

    return label


def insert_on_error(
        parse_fn: ParseFn[S, V], insert_fn: Callable[[S, int], V],
        label: Optional[str] = None) -> ParseFn[S, V]:
    def insert_on_error(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[V, S]:
        r = parse_fn(stream, pos, ctx, rm)
        if rm and rm[0] and type(r) is Error and not r.consumed:
            value = insert_fn(stream, pos)
            loc = ctx.get_loc(stream, pos)
            return Recovered(
                None,
                make_insert(
                    value, pos, ctx, loc,
                    repr(value) if label is None else label
                ),
                loc
            )
        return r

    return insert_on_error
