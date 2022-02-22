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
    def __init__(self, x: V_co, label: Optional[str] = None):
        if label is None:
            label = repr(x)

        self._x = x
        self._label = label

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        loc = ctx.get_loc(stream, pos)
        if rm:
            return Recovered(
                None, [Repair(self._x, pos, ctx, Insert(self._label, loc))],
                pos, loc
            )
        return Error(pos, loc)


class InsertFn(ParseObj[S_contra, V_co]):
    def __init__(self, fn: Callable[[], V_co], label: Optional[str] = None):
        self._fn = fn
        self._label = label

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        loc = ctx.get_loc(stream, pos)
        if rm:
            x = self._fn()
            label = self._label
            if label is None:
                label = repr(x)
            return Recovered(
                None, [Repair(x, pos, ctx, Insert(label, loc))], pos, loc
            )
        return Error(pos, loc)