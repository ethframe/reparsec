from typing import TypeVar

from .parser import ParseFastFn, ParseFn, ParseFns, ParseSlowFn
from .result import Error, Result, SimpleResult
from .types import Ctx

S = TypeVar("S")
V = TypeVar("V")
U = TypeVar("U")


def _block_fast(parse_fns: ParseFns[S, V]) -> ParseFastFn[S, V]:
    parse_fn = parse_fns.fast_fn

    def block(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[V, S]:
        ctx = ctx.update_loc(stream, pos)
        return parse_fn(stream, pos, ctx.set_mark(ctx.loc.col)).set_ctx(ctx)

    return block


def _block(parse_fns: ParseFns[S, V]) -> ParseFn[S, V]:
    parse_fn = parse_fns.fn

    def block(stream: S, pos: int, ctx: Ctx[S], ins: int) -> Result[V, S]:
        ctx = ctx.update_loc(stream, pos)
        return parse_fn(
            stream, pos, ctx.set_mark(ctx.loc.col), ins
        ).set_ctx(ctx)

    return block


def _block_slow(parse_fns: ParseFns[S, V]) -> ParseSlowFn[S, V]:
    parse_fn = parse_fns.slow_fn

    def block(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: int) -> Result[V, S]:
        ctx = ctx.update_loc(stream, pos)
        return parse_fn(
            stream, pos, ctx.set_mark(ctx.loc.col), ins, rem
        ).set_ctx(ctx)

    return block


def block(parse_fns: ParseFns[S, V]) -> ParseFns[S, V]:
    return ParseFns(
        _block_fast(parse_fns),
        _block(parse_fns),
        _block_slow(parse_fns)
    )


def _aligned_fast(parse_fns: ParseFns[S, V]) -> ParseFastFn[S, V]:
    parse_fn = parse_fns.fast_fn

    def aligned(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[V, S]:
        ctx = ctx.update_loc(stream, pos)
        if ctx.mark == ctx.loc.col:
            return parse_fn(stream, pos, ctx)
        return Error(ctx.loc, ["indentation"])

    return aligned


def _aligned(parse_fns: ParseFns[S, V]) -> ParseFn[S, V]:
    parse_fn = parse_fns.fn

    def aligned(stream: S, pos: int, ctx: Ctx[S], ins: int) -> Result[V, S]:
        ctx = ctx.update_loc(stream, pos)
        if ctx.mark == ctx.loc.col:
            return parse_fn(stream, pos, ctx, ins)
        return Error(ctx.loc, ["indentation"])

    return aligned


def _aligned_slow(parse_fns: ParseFns[S, V]) -> ParseSlowFn[S, V]:
    parse_fn = parse_fns.slow_fn

    def aligned(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: int) -> Result[V, S]:
        ctx = ctx.update_loc(stream, pos)
        if ctx.mark == ctx.loc.col:
            return parse_fn(stream, pos, ctx, ins, rem)
        return Error(ctx.loc, ["indentation"])

    return aligned


def aligned(parse_fns: ParseFns[S, V]) -> ParseFns[S, V]:
    return ParseFns(
        _aligned_fast(parse_fns),
        _aligned(parse_fns),
        _aligned_slow(parse_fns)
    )


def _indented_fast(delta: int, parse_fns: ParseFns[S, V]) -> ParseFastFn[S, V]:
    parse_fn = parse_fns.fast_fn

    def indented(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[V, S]:
        ctx = ctx.update_loc(stream, pos)
        level = ctx.loc.col
        if ctx.mark + delta == level:
            return parse_fn(stream, pos, ctx.set_mark(level)).set_ctx(ctx)
        return Error(ctx.loc, ["indentation"])

    return indented


def _indented(delta: int, parse_fns: ParseFns[S, V]) -> ParseFn[S, V]:
    parse_fn = parse_fns.fn

    def indented(stream: S, pos: int, ctx: Ctx[S], ins: int) -> Result[V, S]:
        ctx = ctx.update_loc(stream, pos)
        level = ctx.loc.col
        if ctx.mark + delta == level:
            return parse_fn(stream, pos, ctx.set_mark(level), ins).set_ctx(ctx)
        return Error(ctx.loc, ["indentation"])

    return indented


def _indented_slow(delta: int, parse_fns: ParseFns[S, V]) -> ParseSlowFn[S, V]:
    parse_fn = parse_fns.slow_fn

    def indented(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: int) -> Result[V, S]:
        ctx = ctx.update_loc(stream, pos)
        level = ctx.loc.col
        if ctx.mark + delta == level:
            return parse_fn(
                stream, pos, ctx.set_mark(level), ins, rem
            ).set_ctx(ctx)
        return Error(ctx.loc, ["indentation"])

    return indented


def indented(delta: int, parse_fns: ParseFns[S, V]) -> ParseFns[S, V]:
    return ParseFns(
        _indented_fast(delta, parse_fns),
        _indented(delta, parse_fns),
        _indented_slow(delta, parse_fns)
    )
