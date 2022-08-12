from typing import Callable, Optional, TypeVar

from .parser import ParseObj
from .result import Ok, Result, SimpleResult
from .types import Ctx

S_contra = TypeVar("S_contra", contravariant=True)
A_co = TypeVar("A_co", covariant=True)


class Pure(ParseObj[S_contra, A_co]):
    def __init__(self, x: A_co):
        self._x = x

    def parse_fast_fn(
            self, stream: S_contra, pos: int,
            ctx: Ctx[S_contra]) -> SimpleResult[A_co, S_contra]:
        return Ok(self._x, pos, ctx)

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra], ins: int,
            rem: Optional[int]) -> Result[A_co, S_contra]:
        return Ok(self._x, pos, ctx)


class PureFn(ParseObj[S_contra, A_co]):
    def __init__(self, fn: Callable[[], A_co]):
        self._fn = fn

    def parse_fast_fn(
            self, stream: S_contra, pos: int,
            ctx: Ctx[S_contra]) -> SimpleResult[A_co, S_contra]:
        return Ok(self._fn(), pos, ctx)

    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra], ins: int,
            rem: Optional[int]) -> Result[A_co, S_contra]:
        return Ok(self._fn(), pos, ctx)
