from typing import Optional, TypeVar

from .parser import ParseFastFn, ParseFn, ParseFns
from .result import Error, Result, SimpleResult
from .types import Ctx

S = TypeVar("S")
A = TypeVar("A")
B = TypeVar("B")


def _block_fast(parse_fns: ParseFns[S, A]) -> ParseFastFn[S, A]:
    parse_fn = parse_fns.fast_fn

    def block(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[A, S]:
        ctx = ctx.update_loc(stream, pos)
        return parse_fn(stream, pos, ctx.set_mark(ctx.loc.col)).set_ctx(ctx)

    return block


def _block(parse_fns: ParseFns[S, A]) -> ParseFn[S, A]:
    parse_fn = parse_fns.fn

    def block(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[A, S]:
        ctx = ctx.update_loc(stream, pos)
        return parse_fn(
            stream, pos, ctx.set_mark(ctx.loc.col), ins, rem
        ).set_ctx(ctx)

    return block


def block(parse_fns: ParseFns[S, A]) -> ParseFns[S, A]:
    return ParseFns(_block_fast(parse_fns), _block(parse_fns),)


def _aligned_fast(parse_fns: ParseFns[S, A]) -> ParseFastFn[S, A]:
    parse_fn = parse_fns.fast_fn

    def aligned(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[A, S]:
        ctx = ctx.update_loc(stream, pos)
        if ctx.mark == ctx.loc.col:
            return parse_fn(stream, pos, ctx)
        return Error(ctx.loc, ["indentation"])

    return aligned


def _aligned(parse_fns: ParseFns[S, A]) -> ParseFn[S, A]:
    parse_fn = parse_fns.fn

    def aligned(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[A, S]:
        ctx = ctx.update_loc(stream, pos)
        if ctx.mark == ctx.loc.col:
            return parse_fn(stream, pos, ctx, ins, rem)
        return Error(ctx.loc, ["indentation"])

    return aligned


def aligned(parse_fns: ParseFns[S, A]) -> ParseFns[S, A]:
    return ParseFns(_aligned_fast(parse_fns), _aligned(parse_fns))


def _indented_fast(delta: int, parse_fns: ParseFns[S, A]) -> ParseFastFn[S, A]:
    parse_fn = parse_fns.fast_fn

    def indented(stream: S, pos: int, ctx: Ctx[S]) -> SimpleResult[A, S]:
        ctx = ctx.update_loc(stream, pos)
        level = ctx.loc.col
        if ctx.mark + delta == level:
            return parse_fn(stream, pos, ctx.set_mark(level)).set_ctx(ctx)
        return Error(ctx.loc, ["indentation"])

    return indented


def _indented(delta: int, parse_fns: ParseFns[S, A]) -> ParseFn[S, A]:
    parse_fn = parse_fns.fn

    def indented(
            stream: S, pos: int, ctx: Ctx[S], ins: int,
            rem: Optional[int]) -> Result[A, S]:
        ctx = ctx.update_loc(stream, pos)
        level = ctx.loc.col
        if ctx.mark + delta == level:
            return parse_fn(
                stream, pos, ctx.set_mark(level), ins, rem
            ).set_ctx(ctx)
        return Error(ctx.loc, ["indentation"])

    return indented


def indented(delta: int, parse_fns: ParseFns[S, A]) -> ParseFns[S, A]:
    return ParseFns(
        _indented_fast(delta, parse_fns),
        _indented(delta, parse_fns),
    )
