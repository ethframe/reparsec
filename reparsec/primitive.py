from typing import Callable, Optional, TypeVar

from .core import ParseObj, RecoveryMode
from .result import Error, Insert, Ok, Recovered, Repair, Result

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)
U = TypeVar("U")
X = TypeVar("X")


class Pure(ParseObj[S_contra, V_co]):
    def __init__(self, x: V_co):
        self._x = x

    def parse_fn(
            self, stream: S_contra, pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        return Ok(self._x, pos)


pure = Pure


class PureFn(ParseObj[S_contra, V_co]):
    def __init__(self, fn: Callable[[], V_co]):
        self._fn = fn

    def parse_fn(
            self, stream: S_contra, pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        return Ok(self._fn(), pos)


pure_fn = PureFn


class RecoverValue(ParseObj[S_contra, V_co]):
    def __init__(self, x: V_co, expected: Optional[str] = None):
        self._x = x
        self._label = repr(x)
        self._expected = [] if expected is None else [expected]

    def parse_fn(
            self, stream: S_contra, pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        if rm:
            return Recovered(
                {
                    pos: Repair(
                        1, self._x, Insert(self._label, pos), self._expected
                    )
                },
                pos, self._expected
            )
        return Error(pos)


recover_value = RecoverValue


class RecoverFn(ParseObj[S_contra, V_co]):
    def __init__(self, fn: Callable[[], V_co], expected: Optional[str] = None):
        self._fn = fn
        self._expected = [] if expected is None else [expected]

    def parse_fn(
            self, stream: S_contra, pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        if rm:
            x = self._fn()
            return Recovered(
                {pos: Repair(1, x, Insert(repr(x), pos), self._expected)}, pos,
                self._expected
            )
        return Error(pos)


recover_fn = RecoverFn
