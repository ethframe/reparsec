from abc import abstractmethod
from typing import Callable, Generic, TypeVar

from typing_extensions import Literal

from .result import Result
from .state import Ctx

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)


RecoveryMode = Literal[None, False, True]


def disallow_recovery(rm: RecoveryMode) -> RecoveryMode:
    if rm is None:
        return None
    return False


def maybe_allow_recovery(rm: RecoveryMode, r: Result[V, S]) -> RecoveryMode:
    if rm is not None and r.consumed:
        return True
    return rm


ParseFn = Callable[[S_contra, int, Ctx, RecoveryMode], Result[V_co, S_contra]]


class ParseObj(Generic[S_contra, V_co]):
    @abstractmethod
    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rm: RecoveryMode) -> Result[V_co, S_contra]:
        ...

    def to_fn(self) -> ParseFn[S_contra, V_co]:
        return self.parse_fn
