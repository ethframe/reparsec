from typing import Callable, Iterable, List, Optional, Tuple, TypeVar, Union

from .chain import Append
from .parser import ParseFastFn, ParseFn, ParseFns, ParseObj
from .recovery import MergeFn, continue_parse, join_repairs
from .repair import Insert, OpItem, Repair
from .result import Error, Ok, Recovered, Result, SimpleResult
from .types import Ctx

S = TypeVar("S")
V = TypeVar("V")
U = TypeVar("U")
X = TypeVar("X")


def _fmap_fast(
        parse_fns: ParseFns[S, V], fn: Callable[[V], U]) -> ParseFastFn[S, U]:
    parse_fn = parse_fns.fast_fn

    def fmap(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[U, S]:
        return parse_fn(stream, pos, ctx).fmap(fn)

    return fmap


def _fmap(parse_fns: ParseFns[S, V], fn: Callable[[V], U]) -> ParseFn[S, U]:
    parse_fn = parse_fns.fn

    def fmap(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[U, S]:
        return parse_fn(stream, pos, ctx, ins, rem).fmap(fn)
    return fmap


def fmap(parse_fns: ParseFns[S, V], fn: Callable[[V], U]) -> ParseFns[S, U]:
    return ParseFns(_fmap_fast(parse_fns, fn), _fmap(parse_fns, fn))


def _alt_fast(
        parse_fns: ParseFns[S, V],
        second_fns: ParseFns[S, U]) -> ParseFastFn[S, Union[V, U]]:
    parse_fn = parse_fns.fast_fn
    second_fn = second_fns.fast_fn

    def alt(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[Union[V, U], S]:
        ra = parse_fn(stream, pos, ctx)
        if type(ra) is Ok or ra.consumed:
            return ra
        rb = second_fn(stream, pos, ctx)
        if rb.consumed:
            return rb
        expected = Append(ra.expected, rb.expected)
        if type(rb) is Ok:
            return rb.set_expected(expected)
        return Error(ra.loc, expected)

    return alt


def _alt(
        parse_fns: ParseFns[S, V],
        second_fns: ParseFns[S, U]) -> ParseFn[S, Union[V, U]]:
    parse_fn = parse_fns.fn
    second_fn = second_fns.fn

    def alt(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[Union[V, U], S]:
        ra = parse_fn(stream, pos, ctx, ins, None)
        if type(ra) is Ok or ra.consumed:
            return ra
        rb = second_fn(stream, pos, ctx, ins, None)
        if rb.consumed:
            return rb
        expected = Append(ra.expected, rb.expected)
        if type(rb) is Ok:
            return rb.set_expected(expected)
        if rem is not None:
            rra = parse_fn(stream, pos, ctx, ins, rem)
            rrb = second_fn(stream, pos, ctx, ins, rem)
            if type(rra) is Recovered:
                if type(rrb) is Recovered:
                    return join_repairs(rra, rrb).set_expected(expected)
                return rra.set_expected(expected)
            if type(rrb) is Recovered:
                return rrb.set_expected(expected)
        return Error(ra.loc, expected)

    return alt


def alt(
        parse_fns: ParseFns[S, V],
        second_fns: ParseFns[S, U]) -> ParseFns[S, Union[V, U]]:
    return ParseFns(
        _alt_fast(parse_fns, second_fns),
        _alt(parse_fns, second_fns)
    )


def _bind_fast(
        parse_fns: ParseFns[S, V],
        fn: Callable[[V], ParseObj[S, U]]) -> ParseFastFn[S, U]:
    parse_fn = parse_fns.fast_fn

    def bind(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[U, S]:
        ra = parse_fn(stream, pos, ctx)
        if type(ra) is Error:
            return ra
        return fn(ra.value).parse_fast_fn(
            stream, ra.pos, ra.ctx
        ).prepend_expected(ra.expected, ra.consumed)

    return bind


def _bind(
        parse_fns: ParseFns[S, V],
        fn: Callable[[V], ParseObj[S, U]]) -> ParseFn[S, U]:
    parse_fn = parse_fns.fn

    def bind(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[U, S]:
        ra = parse_fn(stream, pos, ctx, ins, rem)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return continue_parse(
                ra, ins,
                lambda v, p, c, r: fn(v).parse_fn(stream, p, c, ins, r),
                lambda _, v: v
            )
        if ra.consumed:
            return fn(ra.value).parse_fn(
                stream, ra.pos, ra.ctx, ins, ins
            ).prepend_expected(ra.expected, ra.consumed)
        return fn(ra.value).parse_fn(
            stream, ra.pos, ra.ctx, ins, rem
        ).prepend_expected(ra.expected, ra.consumed)

    return bind


def bind(
        parse_fns: ParseFns[S, V],
        fn: Callable[[V], ParseObj[S, U]]) -> ParseFns[S, U]:
    return ParseFns(_bind_fast(parse_fns, fn), _bind(parse_fns, fn))


def _seq_h_fast(
        parse_fns: ParseFns[S, V], second_fns: ParseFns[S, U],
        merge: MergeFn[V, U, X]) -> ParseFastFn[S, X]:
    parse_fn = parse_fns.fast_fn
    second_fn = second_fns.fast_fn

    def seq(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[X, S]:
        ra = parse_fn(stream, pos, ctx)
        if type(ra) is Error:
            return ra
        va = ra.value
        return second_fn(
            stream, ra.pos, ra.ctx
        ).fmap(
            lambda vb: merge(va, vb)
        ).prepend_expected(ra.expected, ra.consumed)

    return seq


def _seq_h(
        parse_fns: ParseFns[S, V], second_fns: ParseFns[S, U],
        merge: MergeFn[V, U, X]) -> ParseFn[S, X]:
    parse_fn = parse_fns.fn
    second_fn = second_fns.fn

    def seq(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[X, S]:
        ra = parse_fn(stream, pos, ctx, ins, rem)
        if type(ra) is Error:
            return ra
        if type(ra) is Recovered:
            return continue_parse(
                ra, ins, lambda _, p, c, r: second_fn(stream, p, c, ins, r),
                merge
            )
        va = ra.value
        return second_fn(
            stream, ra.pos, ra.ctx, ins, ins if ra.consumed else rem
        ).fmap(
            lambda vb: merge(va, vb)
        ).prepend_expected(ra.expected, ra.consumed)

    return seq


def _seq(
        parse_fns: ParseFns[S, V], second_fns: ParseFns[S, U],
        merge: MergeFn[V, U, X]) -> ParseFns[S, X]:
    return ParseFns(
        _seq_h_fast(parse_fns, second_fns, merge),
        _seq_h(parse_fns, second_fns, merge),
    )


def seql(
        parse_fns: ParseFns[S, V],
        second_fns: ParseFns[S, U]) -> ParseFns[S, V]:
    return _seq(parse_fns, second_fns, lambda l, _: l)


def seqr(
        parse_fns: ParseFns[S, V],
        second_fns: ParseFns[S, U]) -> ParseFns[S, U]:
    return _seq(parse_fns, second_fns, lambda _, r: r)


def seq(
        parse_fns: ParseFns[S, V],
        second_fns: ParseFns[S, U]) -> ParseFns[S, Tuple[V, U]]:
    return _seq(parse_fns, second_fns, lambda l, r: (l, r))


V0 = TypeVar("V0")
V1 = TypeVar("V1")
V2 = TypeVar("V2")
V3 = TypeVar("V3")
V4 = TypeVar("V4")
V5 = TypeVar("V5")
V6 = TypeVar("V6")
V7 = TypeVar("V7")


def tuple3(
        parse_fns: ParseFns[S, Tuple[V0, V1]],
        second_fns: ParseFns[S, V2]) -> ParseFns[S, Tuple[V0, V1, V2]]:
    def merge(a: Tuple[V0, V1], b: V2) -> Tuple[V0, V1, V2]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def tuple4(
        parse_fns: ParseFns[S, Tuple[V0, V1, V2]],
        second_fns: ParseFns[S, V3]) -> ParseFns[S, Tuple[V0, V1, V2, V3]]:
    def merge(a: Tuple[V0, V1, V2], b: V3) -> Tuple[V0, V1, V2, V3]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def tuple5(
        parse_fns: ParseFns[S, Tuple[V0, V1, V2, V3]],
        second_fns: ParseFns[S, V4]) -> ParseFns[S, Tuple[V0, V1, V2, V3, V4]]:
    def merge(a: Tuple[V0, V1, V2, V3], b: V4) -> Tuple[V0, V1, V2, V3, V4]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def tuple6(
        parse_fns: ParseFns[S, Tuple[V0, V1, V2, V3, V4]],
        second_fns: ParseFns[S, V5]) -> ParseFns[
            S, Tuple[V0, V1, V2, V3, V4, V5]]:
    def merge(
            a: Tuple[V0, V1, V2, V3, V4],
            b: V5) -> Tuple[V0, V1, V2, V3, V4, V5]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def tuple7(
        parse_fns: ParseFns[S, Tuple[V0, V1, V2, V3, V4, V5]],
        second_fns: ParseFns[S, V6]) -> ParseFns[
            S, Tuple[V0, V1, V2, V3, V4, V5, V6]]:
    def merge(
            a: Tuple[V0, V1, V2, V3, V4, V5],
            b: V6) -> Tuple[V0, V1, V2, V3, V4, V5, V6]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def tuple8(
        parse_fns: ParseFns[S, Tuple[V0, V1, V2, V3, V4, V5, V6]],
        second_fns: ParseFns[S, V7]) -> ParseFns[
            S, Tuple[V0, V1, V2, V3, V4, V5, V6, V7]]:
    def merge(
            a: Tuple[V0, V1, V2, V3, V4, V5, V6],
            b: V7) -> Tuple[V0, V1, V2, V3, V4, V5, V6, V7]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def _maybe_fast(parse_fns: ParseFns[S, V]) -> ParseFastFn[S, Optional[V]]:
    parse_fn = parse_fns.fast_fn

    def maybe(
            stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[Optional[V], S]:
        r = parse_fn(stream, pos, ctx)
        if r.consumed or type(r) is Ok:
            return r
        return Ok(None, pos, ctx, r.expected)

    return maybe


def _maybe(parse_fns: ParseFns[S, V]) -> ParseFn[S, Optional[V]]:
    parse_fn = parse_fns.fn

    def maybe(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[Optional[V], S]:
        r = parse_fn(stream, pos, ctx, ins, None)
        if r.consumed or type(r) is Ok:
            return r
        return Ok(None, pos, ctx, r.expected)

    return maybe


def maybe(parse_fns: ParseFns[S, V]) -> ParseFns[S, Optional[V]]:
    return ParseFns(_maybe_fast(parse_fns), _maybe(parse_fns))


def _many_fast(parse_fns: ParseFns[S, V]) -> ParseFastFn[S, List[V]]:
    parse_fn = parse_fns.fast_fn

    def many(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[List[V], S]:
        consumed = False
        value: List[V] = []
        r = parse_fn(stream, pos, ctx)
        while type(r) is Ok:
            if not r.consumed:
                raise RuntimeError("parser shouldn't accept empty string")
            consumed = True
            value.append(r.value)
            pos = r.pos
            ctx = r.ctx
            r = parse_fn(stream, pos, ctx)
        if r.consumed:
            return r
        return Ok(value, pos, ctx, r.expected, consumed)

    return many


def _many(parse_fns: ParseFns[S, V]) -> ParseFn[S, List[V]]:
    parse_fn = parse_fns.fn

    def many(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[List[V], S]:
        consumed = False
        value: List[V] = []
        r = parse_fn(stream, pos, ctx, ins, None)
        while type(r) is Ok:
            if not r.consumed:
                raise RuntimeError("parser shouldn't accept empty string")
            consumed = True
            value.append(r.value)
            pos = r.pos
            ctx = r.ctx
            r = parse_fn(stream, pos, ctx, ins, None)
        if type(r) is Recovered:
            def parse(
                    _: V, pos: int, ctx: Ctx[S],
                    __: int) -> Result[List[V], S]:
                r = many(stream, pos, ctx, ins, None)
                if type(r) is Error and not r.consumed:
                    return Ok[List[V], S]([], pos, ctx, r.expected)
                return r

            return continue_parse(
                r, ins, parse, lambda a, b: [*value, a, *b]
            )
        if r.consumed:
            return r
        return Ok(value, pos, ctx, r.expected, consumed)

    return many


def many(parse_fns: ParseFns[S, V]) -> ParseFns[S, List[V]]:
    return ParseFns(_many_fast(parse_fns), _many(parse_fns))


def _attempt_fast(parse_fns: ParseFns[S, V]) -> ParseFastFn[S, V]:
    parse_fn = parse_fns.fast_fn

    def attempt(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[V, S]:
        r = parse_fn(stream, pos, ctx)
        if type(r) is Error:
            return Error(r.loc, r.expected)
        return r

    return attempt


def _attempt(parse_fns: ParseFns[S, V]) -> ParseFn[S, V]:
    parse_fast_fn = parse_fns.fast_fn
    parse_fn = parse_fns.fn

    def attempt(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[V, S]:
        if rem is not None:
            return parse_fn(stream, pos, ctx, ins, rem)
        r = parse_fast_fn(stream, pos, ctx)
        if type(r) is Error:
            return Error(r.loc, r.expected)
        return r

    return attempt


def attempt(parse_fns: ParseFns[S, V]) -> ParseFns[S, V]:
    return ParseFns(_attempt_fast(parse_fns), _attempt(parse_fns))


def _label_fast(
        parse_fns: ParseFns[S, V],
        expected: Iterable[str]) -> ParseFastFn[S, V]:
    parse_fn = parse_fns.fast_fn

    def label(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[V, S]:
        return parse_fn(stream, pos, ctx).set_expected(expected)

    return label


def _label(
        parse_fns: ParseFns[S, V], expected: Iterable[str]) -> ParseFn[S, V]:
    parse_fn = parse_fns.fn

    def label(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[V, S]:
        return parse_fn(stream, pos, ctx, ins, rem).set_expected(expected)

    return label


def label(parse_fns: ParseFns[S, V], x: str) -> ParseFns[S, V]:
    expected = [x]
    return ParseFns(
        _label_fast(parse_fns, expected),
        _label(parse_fns, expected)
    )


def _recover_fast(parse_fns: ParseFns[S, V]) -> ParseFastFn[S, V]:
    return parse_fns.fast_fn


def _recover(parse_fns: ParseFns[S, V]) -> ParseFn[S, V]:
    parse_fn = parse_fns.fn

    def recover(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[V, S]:
        r = parse_fn(stream, pos, ctx, ins, rem)
        if type(r) is Recovered:
            for p in r.repairs:
                if p.skip is None:
                    p.auto = False
        return r

    return recover


def recover(parse_fns: ParseFns[S, V]) -> ParseFns[S, V]:
    return ParseFns(_recover_fast(parse_fns), _recover(parse_fns))


def _recover_with_fast(
        parse_fns: ParseFns[S, V], x: V, vs: str) -> ParseFastFn[S, V]:
    return parse_fns.fast_fn


def _recover_with(
        parse_fns: ParseFns[S, V], x: V, vs: str) -> ParseFn[S, V]:
    parse_fn = parse_fns.fn

    def recover_with(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[V, S]:
        if rem is None:
            return parse_fn(stream, pos, ctx, ins, None)
        r = parse_fn(stream, pos, ctx, ins, rem)
        if type(r) is Ok or r.consumed:
            return r
        if rem:
            loc = ctx.get_loc(stream, pos)
            rep = Repair(
                None, False, rem - 1, [OpItem(Insert(vs), loc, r.expected)],
                x, pos, ctx, (), True
            )
            if type(r) is Error:
                return Recovered([rep], None, loc)
            return Recovered([rep, *r.repairs], r.min_skip, loc, r.expected)
        return r

    return recover_with


def recover_with(
        parse_fns: ParseFns[S, V], x: V,
        label: Optional[str] = None) -> ParseFns[S, V]:
    vs = repr(x) if label is None else label

    return ParseFns(
        _recover_with_fast(parse_fns, x, vs),
        _recover_with(parse_fns, x, vs)
    )


def _recover_with_fn_fast(parse_fns: ParseFns[S, V]) -> ParseFastFn[S, V]:
    return parse_fns.fast_fn


def _recover_with_fn(
        parse_fns: ParseFns[S, V], fn: Callable[[S, int], V],
        label: Optional[str]) -> ParseFn[S, V]:
    parse_fn = parse_fns.fn

    def recover_with_fn(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[V, S]:
        if rem is None:
            return parse_fn(stream, pos, ctx, ins, None)
        r = parse_fn(stream, pos, ctx, ins, rem)
        if type(r) is Ok or r.consumed:
            return r
        if rem:
            x = fn(stream, pos)
            loc = ctx.get_loc(stream, pos)
            rep = Repair(
                None, False, rem - 1, [
                    OpItem(
                        Insert(repr(x) if label is None else label),
                        loc, r.expected
                    )
                ],
                x, pos, ctx, (), True
            )
            if type(r) is Error:
                return Recovered([rep], None, loc)
            return Recovered([rep, *r.repairs], r.min_skip, loc, r.expected)
        return r

    return recover_with_fn


def recover_with_fn(
        parse_fns: ParseFns[S, V], fn: Callable[[S, int], V],
        label: Optional[str]) -> ParseFns[S, V]:
    return ParseFns(
        _recover_with_fn_fast(parse_fns),
        _recover_with_fn(parse_fns, fn, label),
    )
