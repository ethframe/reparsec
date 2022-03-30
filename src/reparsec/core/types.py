from abc import abstractmethod
from typing import Callable, Generic, Optional, TypeVar

from .result import Result
from .state import Ctx

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)


RecoveryMode = Optional[int]


def disallow_recovery(rm: RecoveryMode) -> RecoveryMode:
    if rm is None:
        return None
    return 0


def maybe_allow_recovery(
        ctx: Ctx[S], rm: RecoveryMode, consumed: bool) -> RecoveryMode:
    if rm is not None and consumed:
        return ctx.max_insertions
    return rm


def decrease_recovery_steps(rm: RecoveryMode, count: int) -> RecoveryMode:
    if rm:
        if rm > count:
            return rm - count
        return 0
    return rm


ParseFn = Callable[
    [S_contra, int, Ctx[S_contra], RecoveryMode],
    Result[V_co, S_contra]
]


class ParseObj(Generic[S_contra, V_co]):
    @abstractmethod
    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        ...

    def to_fn(self) -> ParseFn[S_contra, V_co]:
        return self.parse_fn
