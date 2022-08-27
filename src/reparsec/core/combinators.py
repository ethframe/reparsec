from typing import Callable, Iterable, List, Optional, Tuple, TypeVar, Union

from .chain import Append
from .parser import ParseFastFn, ParseFn, ParseFns, ParseObj
from .recovery import MergeFn, continue_parse, join_repairs
from .repair import make_user_insert
from .result import Error, Ok, Recovered, Result, SimpleResult
from .types import Ctx

S = TypeVar("S")
A = TypeVar("A")
B = TypeVar("B")
C = TypeVar("C")


def _fmap_fast(
        parse_fns: ParseFns[S, A], fn: Callable[[A], B]) -> ParseFastFn[S, B]:
    parse_fn = parse_fns.fast_fn

    def fmap(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[B, S]:
        return parse_fn(stream, pos, ctx).fmap(fn)

    return fmap


def _fmap(parse_fns: ParseFns[S, A], fn: Callable[[A], B]) -> ParseFn[S, B]:
    parse_fn = parse_fns.fn

    def fmap(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[B, S]:
        return parse_fn(stream, pos, ctx, ins, rem).fmap(fn)
    return fmap


def fmap(parse_fns: ParseFns[S, A], fn: Callable[[A], B]) -> ParseFns[S, B]:
    return ParseFns(_fmap_fast(parse_fns, fn), _fmap(parse_fns, fn))


def _alt_fast(
        parse_fns: ParseFns[S, A],
        second_fns: ParseFns[S, B]) -> ParseFastFn[S, Union[A, B]]:
    parse_fn = parse_fns.fast_fn
    second_fn = second_fns.fast_fn

    def alt(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[Union[A, B], S]:
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
        parse_fns: ParseFns[S, A],
        second_fns: ParseFns[S, B]) -> ParseFn[S, Union[A, B]]:
    parse_fn = parse_fns.fn
    second_fn = second_fns.fn

    def alt(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[Union[A, B], S]:
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
        parse_fns: ParseFns[S, A],
        second_fns: ParseFns[S, B]) -> ParseFns[S, Union[A, B]]:
    return ParseFns(
        _alt_fast(parse_fns, second_fns),
        _alt(parse_fns, second_fns)
    )


def _bind_fast(
        parse_fns: ParseFns[S, A],
        fn: Callable[[A], ParseObj[S, B]]) -> ParseFastFn[S, B]:
    parse_fn = parse_fns.fast_fn

    def bind(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[B, S]:
        ra = parse_fn(stream, pos, ctx)
        if type(ra) is Error:
            return ra
        return fn(ra.value).parse_fast_fn(
            stream, ra.pos, ra.ctx
        ).prepend_expected(ra.expected, ra.consumed)

    return bind


def _bind(
        parse_fns: ParseFns[S, A],
        fn: Callable[[A], ParseObj[S, B]]) -> ParseFn[S, B]:
    parse_fn = parse_fns.fn

    def bind(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[B, S]:
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
        parse_fns: ParseFns[S, A],
        fn: Callable[[A], ParseObj[S, B]]) -> ParseFns[S, B]:
    return ParseFns(_bind_fast(parse_fns, fn), _bind(parse_fns, fn))


def _seq_h_fast(
        parse_fns: ParseFns[S, A], second_fns: ParseFns[S, B],
        merge: MergeFn[A, B, C]) -> ParseFastFn[S, C]:
    parse_fn = parse_fns.fast_fn
    second_fn = second_fns.fast_fn

    def seq(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[C, S]:
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
        parse_fns: ParseFns[S, A], second_fns: ParseFns[S, B],
        merge: MergeFn[A, B, C]) -> ParseFn[S, C]:
    parse_fn = parse_fns.fn
    second_fn = second_fns.fn

    def seq(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[C, S]:
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
        parse_fns: ParseFns[S, A], second_fns: ParseFns[S, B],
        merge: MergeFn[A, B, C]) -> ParseFns[S, C]:
    return ParseFns(
        _seq_h_fast(parse_fns, second_fns, merge),
        _seq_h(parse_fns, second_fns, merge),
    )


def seql(
        parse_fns: ParseFns[S, A],
        second_fns: ParseFns[S, B]) -> ParseFns[S, A]:
    return _seq(parse_fns, second_fns, lambda l, _: l)


def seqr(
        parse_fns: ParseFns[S, A],
        second_fns: ParseFns[S, B]) -> ParseFns[S, B]:
    return _seq(parse_fns, second_fns, lambda _, r: r)


def seq(
        parse_fns: ParseFns[S, A],
        second_fns: ParseFns[S, B]) -> ParseFns[S, Tuple[A, B]]:
    return _seq(parse_fns, second_fns, lambda l, r: (l, r))


A0 = TypeVar("A0")
A1 = TypeVar("A1")
A2 = TypeVar("A2")
A3 = TypeVar("A3")
A4 = TypeVar("A4")
A5 = TypeVar("A5")
A6 = TypeVar("A6")
A7 = TypeVar("A7")


def tuple3(
        parse_fns: ParseFns[S, Tuple[A0, A1]],
        second_fns: ParseFns[S, A2]) -> ParseFns[S, Tuple[A0, A1, A2]]:
    def merge(a: Tuple[A0, A1], b: A2) -> Tuple[A0, A1, A2]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def tuple4(
        parse_fns: ParseFns[S, Tuple[A0, A1, A2]],
        second_fns: ParseFns[S, A3]) -> ParseFns[S, Tuple[A0, A1, A2, A3]]:
    def merge(a: Tuple[A0, A1, A2], b: A3) -> Tuple[A0, A1, A2, A3]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def tuple5(
        parse_fns: ParseFns[S, Tuple[A0, A1, A2, A3]],
        second_fns: ParseFns[S, A4]) -> ParseFns[S, Tuple[A0, A1, A2, A3, A4]]:
    def merge(a: Tuple[A0, A1, A2, A3], b: A4) -> Tuple[A0, A1, A2, A3, A4]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def tuple6(
        parse_fns: ParseFns[S, Tuple[A0, A1, A2, A3, A4]],
        second_fns: ParseFns[S, A5]) -> ParseFns[
            S, Tuple[A0, A1, A2, A3, A4, A5]]:
    def merge(
            a: Tuple[A0, A1, A2, A3, A4],
            b: A5) -> Tuple[A0, A1, A2, A3, A4, A5]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def tuple7(
        parse_fns: ParseFns[S, Tuple[A0, A1, A2, A3, A4, A5]],
        second_fns: ParseFns[S, A6]) -> ParseFns[
            S, Tuple[A0, A1, A2, A3, A4, A5, A6]]:
    def merge(
            a: Tuple[A0, A1, A2, A3, A4, A5],
            b: A6) -> Tuple[A0, A1, A2, A3, A4, A5, A6]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def tuple8(
        parse_fns: ParseFns[S, Tuple[A0, A1, A2, A3, A4, A5, A6]],
        second_fns: ParseFns[S, A7]) -> ParseFns[
            S, Tuple[A0, A1, A2, A3, A4, A5, A6, A7]]:
    def merge(
            a: Tuple[A0, A1, A2, A3, A4, A5, A6],
            b: A7) -> Tuple[A0, A1, A2, A3, A4, A5, A6, A7]:
        return (*a, b)
    return _seq(parse_fns, second_fns, merge)


def _maybe_fast(parse_fns: ParseFns[S, A]) -> ParseFastFn[S, Optional[A]]:
    parse_fn = parse_fns.fast_fn

    def maybe(
            stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[Optional[A], S]:
        r = parse_fn(stream, pos, ctx)
        if r.consumed or type(r) is Ok:
            return r
        return Ok(None, pos, ctx, r.expected)

    return maybe


def _maybe(parse_fns: ParseFns[S, A]) -> ParseFn[S, Optional[A]]:
    parse_fn = parse_fns.fn

    def maybe(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[Optional[A], S]:
        r = parse_fn(stream, pos, ctx, ins, None)
        if r.consumed or type(r) is Ok:
            return r
        return Ok(None, pos, ctx, r.expected)

    return maybe


def maybe(parse_fns: ParseFns[S, A]) -> ParseFns[S, Optional[A]]:
    return ParseFns(_maybe_fast(parse_fns), _maybe(parse_fns))


def _many_fast(parse_fns: ParseFns[S, A]) -> ParseFastFn[S, List[A]]:
    parse_fn = parse_fns.fast_fn

    def many(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[List[A], S]:
        consumed = False
        value: List[A] = []
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


def _many(parse_fns: ParseFns[S, A]) -> ParseFn[S, List[A]]:
    parse_fn = parse_fns.fn

    def many(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[List[A], S]:
        consumed = False
        value: List[A] = []
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
            return continue_parse(
                r, ins, lambda _, p, c, __: many(stream, p, c, ins, None),
                lambda a, b: [*value, a, *b]
            )
        if r.consumed:
            return r
        return Ok(value, pos, ctx, r.expected, consumed)

    return many


def many(parse_fns: ParseFns[S, A]) -> ParseFns[S, List[A]]:
    return ParseFns(_many_fast(parse_fns), _many(parse_fns))


def _attempt_fast(parse_fns: ParseFns[S, A]) -> ParseFastFn[S, A]:
    parse_fn = parse_fns.fast_fn

    def attempt(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[A, S]:
        r = parse_fn(stream, pos, ctx)
        if type(r) is Error:
            return Error(r.loc, r.expected)
        return r

    return attempt


def _attempt(parse_fns: ParseFns[S, A]) -> ParseFn[S, A]:
    parse_fast_fn = parse_fns.fast_fn
    parse_fn = parse_fns.fn

    def attempt(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[A, S]:
        if rem is not None:
            return parse_fn(stream, pos, ctx, ins, rem)
        r = parse_fast_fn(stream, pos, ctx)
        if type(r) is Error:
            return Error(r.loc, r.expected)
        return r

    return attempt


def attempt(parse_fns: ParseFns[S, A]) -> ParseFns[S, A]:
    return ParseFns(_attempt_fast(parse_fns), _attempt(parse_fns))


def _label_fast(
        parse_fns: ParseFns[S, A],
        expected: Iterable[str]) -> ParseFastFn[S, A]:
    parse_fn = parse_fns.fast_fn

    def label(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[A, S]:
        return parse_fn(stream, pos, ctx).set_expected(expected)

    return label


def _label(
        parse_fns: ParseFns[S, A], expected: Iterable[str]) -> ParseFn[S, A]:
    parse_fn = parse_fns.fn

    def label(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[A, S]:
        return parse_fn(stream, pos, ctx, ins, rem).set_expected(expected)

    return label


def label(parse_fns: ParseFns[S, A], x: str) -> ParseFns[S, A]:
    expected = [x]
    return ParseFns(
        _label_fast(parse_fns, expected),
        _label(parse_fns, expected)
    )


def _recover_fast(parse_fns: ParseFns[S, A]) -> ParseFastFn[S, A]:
    return parse_fns.fast_fn


def _recover(parse_fns: ParseFns[S, A]) -> ParseFn[S, A]:
    parse_fn = parse_fns.fn

    def recover(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[A, S]:
        r = parse_fn(stream, pos, ctx, ins, rem)
        if type(r) is Recovered:
            for p in r.repairs:
                if p.prio is None:
                    p.prio = 0
        return r

    return recover


def recover(parse_fns: ParseFns[S, A]) -> ParseFns[S, A]:
    return ParseFns(_recover_fast(parse_fns), _recover(parse_fns))


def _recover_with_fast(parse_fns: ParseFns[S, A]) -> ParseFastFn[S, A]:
    return parse_fns.fast_fn


def _recover_with(
        parse_fns: ParseFns[S, A], x: A, vs: str) -> ParseFn[S, A]:
    parse_fn = parse_fns.fn

    def recover_with(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[A, S]:
        if rem is None:
            return parse_fn(stream, pos, ctx, ins, None)
        r = parse_fn(stream, pos, ctx, ins, rem)
        if type(r) is Ok or r.consumed:
            return r
        if rem:
            loc = ctx.get_loc(stream, pos)
            rep = make_user_insert(rem, x, pos, ctx, loc, vs, r.expected)
            if type(r) is Error:
                return Recovered([rep], None, loc)
            return Recovered([rep, *r.repairs], r.min_prio, loc, r.expected)
        return r

    return recover_with


def recover_with(
        parse_fns: ParseFns[S, A], x: A,
        label: Optional[str] = None) -> ParseFns[S, A]:
    vs = repr(x) if label is None else label

    return ParseFns(
        _recover_with_fast(parse_fns),
        _recover_with(parse_fns, x, vs)
    )


def _recover_with_fn_fast(parse_fns: ParseFns[S, A]) -> ParseFastFn[S, A]:
    return parse_fns.fast_fn


def _recover_with_fn(
        parse_fns: ParseFns[S, A], fn: Callable[[S, int], A],
        label: Optional[str]) -> ParseFn[S, A]:
    parse_fn = parse_fns.fn

    def recover_with_fn(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[A, S]:
        if rem is None:
            return parse_fn(stream, pos, ctx, ins, None)
        r = parse_fn(stream, pos, ctx, ins, rem)
        if type(r) is Ok or r.consumed:
            return r
        if rem:
            x = fn(stream, pos)
            loc = ctx.get_loc(stream, pos)
            rep = make_user_insert(
                rem, x, pos, ctx, loc, repr(x) if label is None else label,
                r.expected
            )
            if type(r) is Error:
                return Recovered([rep], None, loc)
            return Recovered([rep, *r.repairs], r.min_prio, loc, r.expected)
        return r

    return recover_with_fn


def recover_with_fn(
        parse_fns: ParseFns[S, A], fn: Callable[[S, int], A],
        label: Optional[str]) -> ParseFns[S, A]:
    return ParseFns(
        _recover_with_fn_fast(parse_fns),
        _recover_with_fn(parse_fns, fn, label),
    )
