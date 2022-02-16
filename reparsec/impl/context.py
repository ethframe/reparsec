from typing import Callable, Generic, TypeVar

from ..core import ParseFnC, ParseObjC, RecoveryMode
from ..result import Error, Ok, Result

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
P = TypeVar("P")
C = TypeVar("C")
CI = TypeVar("CI")
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")


class InCtxC(
        Generic[S_contra, P, C, V_co, CI],
        ParseObjC[S_contra, P, C, V_co]):
    def __init__(self, parse_fn: ParseFnC[S_contra, P, CI, V_co], ctx: CI):
        self._parse_fn = parse_fn
        self._ctx = ctx

    def parse_fn(
            self, stream: S_contra, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, V_co]:
        return self.to_fn()(stream, pos, ctx, rm)

    def to_fn(self) -> ParseFnC[S_contra, P, C, V_co]:
        parse_fn = self._parse_fn
        new_ctx = self._ctx

        def in_ctx(
            stream: S_contra, pos: P, ctx: C,
                rm: RecoveryMode) -> Result[P, C, V_co]:
            return parse_fn(stream, pos, new_ctx, rm).fmap_ctx(lambda _: ctx)
        return in_ctx


InCtx = InCtxC[S_contra, P, None, CI, V_co]

CtxCheckFn = Callable[[S, P, C], bool]


class CheckCtxC(ParseObjC[S_contra, P, C, None]):
    def __init__(self, fn: CtxCheckFn[S_contra, P, C]):
        self._fn = fn

    def parse_fn(
            self, stream: S_contra, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, None]:
        if self._fn(stream, pos, ctx):
            return Ok(None, pos, ctx)
        return Error(pos)


CheckCtx = CheckCtxC[S_contra, P, None]

CtxUpdateFn = Callable[[S, P, C], C]


class UpdateCtxC(ParseObjC[S_contra, P, C, None]):
    def __init__(self, fn: CtxUpdateFn[S_contra, P, C]):
        self._fn = fn

    def parse_fn(
            self, stream: S_contra, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, None]:
        ctx = self._fn(stream, pos, ctx)
        return Ok(None, pos, ctx)
