from typing import Callable, Optional, TypeVar

from .result import Error, Insert, Ok, Recovered, Repair, Result
from .state import Ctx
from .types import ParseObj, RecoveryMode

S_contra = TypeVar("S_contra", contravariant=True)
V_co = TypeVar("V_co", covariant=True)


class Pure(ParseObj[S_contra, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        return Ok(self._x, pos, ctx)


class PureFn(ParseObj[S_contra, V_co]):
    def __init__(self, fn: Callable[[], V_co]):
        self._fn = fn

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        return Ok(self._fn(), pos, ctx)


class InsertValue(ParseObj[S_contra, V_co]):
    def __init__(self, x: V_co, expected: Optional[str] = None):
        self._x = x
        self._label = repr(x)
        self._expected = [] if expected is None else [expected]

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        loc = ctx.get_loc(stream, pos)
        if rm:
            return Recovered(
                None,
                [
                    Repair(
                        self._x, pos, ctx, Insert(self._label, loc),
                        self._expected
                    )
                ],
                pos, loc, self._expected
            )
        return Error(pos, loc)


class InsertFn(ParseObj[S_contra, V_co]):
    def __init__(self, fn: Callable[[], V_co], expected: Optional[str] = None):
        self._fn = fn
        self._expected = [] if expected is None else [expected]

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        loc = ctx.get_loc(stream, pos)
        if rm:
            x = self._fn()
            return Recovered(
                None,
                [Repair(x, pos, ctx, Insert(repr(x), loc), self._expected)],
                pos, loc, self._expected
            )
        return Error(pos, loc)
