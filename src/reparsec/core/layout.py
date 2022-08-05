from typing import TypeVar

from .parser import ParseFn
from .result import Error, Result
from .types import Ctx, RecoveryState

S = TypeVar("S")
V = TypeVar("V")
U = TypeVar("U")


def block(parse_fn: ParseFn[S, V]) -> ParseFn[S, V]:
    def block(
            stream: S, pos: int, ctx: Ctx[S],
            rs: RecoveryState) -> Result[V, S]:
        ctx = ctx.update_loc(stream, pos)
        return parse_fn(
            stream, pos, ctx.set_anchor(ctx.loc.col), rs
        ).set_ctx(ctx)

    return block


def aligned(parse_fn: ParseFn[S, V]) -> ParseFn[S, V]:
    def aligned(
            stream: S, pos: int, ctx: Ctx[S],
            rs: RecoveryState) -> Result[V, S]:
        ctx = ctx.update_loc(stream, pos)
        if ctx.mark == ctx.loc.col:
            return parse_fn(stream, pos, ctx, rs)
        return Error(ctx.loc, ["indentation"])

    return aligned


def indented(delta: int, parse_fn: ParseFn[S, V]) -> ParseFn[S, V]:
    def indented(
            stream: S, pos: int, ctx: Ctx[S],
            rs: RecoveryState) -> Result[V, S]:
        ctx = ctx.update_loc(stream, pos)
        level = ctx.loc.col
        if ctx.mark + delta == level:
            return parse_fn(
                stream, pos, ctx.set_anchor(level), rs
            ).set_ctx(ctx)
        return Error(ctx.loc, ["indentation"])

    return indented
