from typing import Callable, TypeVar

from ..core import ParseFnC, RecoveryMode
from ..result import Error, Result

S = TypeVar("S")
P = TypeVar("P")
V = TypeVar("V")
U = TypeVar("U")


Ctx = int

GetLevelFn = Callable[[S, P], Ctx]


def block(
        parse_fn: ParseFnC[S, P, Ctx, V],
        fn: GetLevelFn[S, P]) -> ParseFnC[S, P, Ctx, V]:
    def block(
            stream: S, pos: P, ctx: Ctx,
            rm: RecoveryMode) -> Result[P, Ctx, V]:
        return parse_fn(
            stream, pos, fn(stream, pos), rm
        ).fmap_ctx(lambda _: ctx)

    return block


def same(
        parse_fn: ParseFnC[S, P, Ctx, V],
        fn: GetLevelFn[S, P]) -> ParseFnC[S, P, Ctx, V]:
    def same(
            stream: S, pos: P, ctx: Ctx,
            rm: RecoveryMode) -> Result[P, Ctx, V]:
        if fn(stream, pos) == ctx:
            return parse_fn(stream, pos, ctx, rm)
        return Error(pos, ["indentation"])

    return same


def indented(
        delta: int, parse_fn: ParseFnC[S, P, Ctx, V],
        fn: GetLevelFn[S, P]) -> ParseFnC[S, P, Ctx, V]:
    def indented(
            stream: S, pos: P, ctx: Ctx,
            rm: RecoveryMode) -> Result[P, Ctx, V]:
        expected = ctx + delta
        if fn(stream, pos) == expected:
            return parse_fn(stream, pos, expected, rm).fmap_ctx(lambda _: ctx)
        return Error(pos, ["indentation"])

    return indented
