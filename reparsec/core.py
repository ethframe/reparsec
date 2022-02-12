from abc import abstractmethod
from typing import Callable, Generic, Literal, TypeVar

from .result import Result

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
P = TypeVar("P")
C = TypeVar("C")
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)


RecoveryMode = Literal[None, False, True]


def disallow_recovery(rm: RecoveryMode) -> RecoveryMode:
    if rm is None:
        return None
    return False


def maybe_allow_recovery(rm: RecoveryMode, r: Result[P, C, V]) -> RecoveryMode:
    if rm is not None and r.consumed:
        return True
    return rm


ParseFnC = Callable[[S_contra, P, C, RecoveryMode], Result[P, C, V_co]]
ParseFn = ParseFnC[S, P, None, V_co]


class ParseObjC(Generic[S_contra, P, C, V_co]):
    @abstractmethod
    def parse_fn(
            self, stream: S_contra, pos: P, ctx: C,
            rm: RecoveryMode) -> Result[P, C, V_co]:
        ...

    def to_fn(self) -> ParseFnC[S_contra, P, C, V_co]:
        return self.parse_fn


ParseObj = ParseObjC[S_contra, P, None, V_co]
