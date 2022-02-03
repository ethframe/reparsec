from abc import abstractmethod
from typing import Callable, Generic, Literal, TypeVar

from .result import Result

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)


RecoveryMode = Literal[None, False, True]


def disallow_recovery(rm: RecoveryMode) -> RecoveryMode:
    if rm is None:
        return None
    return False


def maybe_allow_recovery(rm: RecoveryMode, r: Result[V]) -> RecoveryMode:
    if rm is not None and r.consumed:
        return True
    return rm


ParseFn = Callable[[S, int, RecoveryMode], Result[V]]


class ParseObj(Generic[S_contra, V_co]):
    @abstractmethod
    def parse_fn(
            self, stream: S_contra, pos: int,
            rm: RecoveryMode) -> Result[V_co]:
        ...

    def to_fn(self) -> ParseFn[S_contra, V_co]:
        return self.parse_fn
