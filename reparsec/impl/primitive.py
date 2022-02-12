from typing import Callable, Optional, TypeVar

from ..core import ParseObjC, RecoveryMode
from ..result import Error, Insert, Ok, Recovered, Repair, Result

S_contra = TypeVar("S_contra", contravariant=True)
P = TypeVar("P")
C = TypeVar("C")
V_co = TypeVar("V_co", covariant=True)


class PureC(ParseObjC[S_contra, P, C, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def parse_fn(
            self, stream: S_contra, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, V_co]:
        return Ok(self._x, pos, ctx)


class PureFnC(ParseObjC[S_contra, P, C, V_co]):
    def __init__(self, fn: Callable[[], V_co]):
        self._fn = fn

    def parse_fn(
            self, stream: S_contra, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, V_co]:
        return Ok(self._fn(), pos, ctx)


class InsertValueC(ParseObjC[S_contra, P, C, V_co]):
    def __init__(self, x: V_co, expected: Optional[str] = None):
        self._x = x
        self._label = repr(x)
        self._expected = [] if expected is None else [expected]

    def parse_fn(
            self, stream: S_contra, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, V_co]:
        if rm:
            return Recovered(
                {
                    pos: Repair(
                        1, self._x, ctx, Insert(self._label, pos),
                        self._expected
                    )
                },
                pos, self._expected
            )
        return Error(pos)


class InsertFnC(ParseObjC[S_contra, P, C, V_co]):
    def __init__(self, fn: Callable[[], V_co], expected: Optional[str] = None):
        self._fn = fn
        self._expected = [] if expected is None else [expected]

    def parse_fn(
            self, stream: S_contra, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, V_co]:
        if rm:
            x = self._fn()
            return Recovered(
                {pos: Repair(1, x, ctx, Insert(repr(x), pos), self._expected)},
                pos, self._expected
            )
        return Error(pos)
