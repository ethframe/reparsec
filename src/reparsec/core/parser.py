from abc import abstractmethod
from typing import Callable, Generic, TypeVar

from .result import Result
from .types import Ctx, RecoveryState

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)


ParseFn = Callable[
    [S_contra, int, Ctx[S_contra], RecoveryState],
    Result[V_co, S_contra]
]


class ParseObj(Generic[S_contra, V_co]):
    @abstractmethod
    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            rs: RecoveryState) -> Result[V_co, S_contra]:
        ...

    def to_fn(self) -> ParseFn[S_contra, V_co]:
        return self.parse_fn
