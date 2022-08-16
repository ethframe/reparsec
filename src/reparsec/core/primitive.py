from typing import Callable, Optional, TypeVar

from .parser import ParseFastFn, ParseFn, ParseFns, ParseObj
from .result import Error, Ok, Result, SimpleResult
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


def _unexpected_fast(expected: str) -> ParseFastFn[object, None]:
    def unexpected(
            stream: object, pos: int,
            ctx: Ctx[object]) -> SimpleResult[None, object]:
        return Error(ctx.get_loc(stream, pos), [expected])

    return unexpected


def _unexpected(expected: str) -> ParseFn[object, None]:
    def unexpected(
            stream: object, pos: int, ctx: Ctx[object], ins: int,
            rem: Optional[int]) -> Result[None, object]:
        return Error(ctx.get_loc(stream, pos), [expected])

    return unexpected


def unexpected(expected: str) -> ParseFns[object, None]:
    return ParseFns(_unexpected_fast(expected), _unexpected(expected))
