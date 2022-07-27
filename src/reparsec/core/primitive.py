from typing import Callable, TypeVar

from .parser import ParseObj
from .result import Ok, Result
from .types import Ctx, RecoveryState

S_contra = TypeVar("S_contra", contravariant=True)
V_co = TypeVar("V_co", covariant=True)


class Pure(ParseObj[S_contra, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rs: RecoveryState) -> Result[V_co, S_contra]:
        return Ok(self._x, pos, ctx)


class PureFn(ParseObj[S_contra, V_co]):
    def __init__(self, fn: Callable[[], V_co]):
        self._fn = fn

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rs: RecoveryState) -> Result[V_co, S_contra]:
        return Ok(self._fn(), pos, ctx)
