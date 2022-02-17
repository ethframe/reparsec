from typing import TypeVar

from ..core import ParseFn, RecoveryMode
from ..result import Error, Result
from ..state import Ctx

S = TypeVar("S")
V = TypeVar("V")
U = TypeVar("U")


def block(parse_fn: ParseFn[S, V]) -> ParseFn[S, V]:
    def block(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[V, S]:
        ctx, inner = ctx.set_anchor(stream, pos)
        return parse_fn(stream, pos, inner, rm).with_ctx(ctx)

    return block


def same(parse_fn: ParseFn[S, V]) -> ParseFn[S, V]:
    def same(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[V, S]:
        ctx, loc = ctx.get_loc(stream, pos)
        if ctx.anchor == loc.col:
            return parse_fn(stream, pos, ctx, rm)
        return Error(pos, loc, ["indentation"])

    return same


def indented(delta: int, parse_fn: ParseFn[S, V]) -> ParseFn[S, V]:
    def indented(
            stream: S, pos: int, ctx: Ctx[S],
            rm: RecoveryMode) -> Result[V, S]:
        ctx, inner = ctx.set_anchor(stream, pos)
        if ctx.anchor + delta == inner.anchor:
            return parse_fn(stream, pos, inner, rm).with_ctx(ctx)
        ctx, loc = ctx.get_loc(stream, pos)
        return Error(pos, loc, ["indentation"])

    return indented
