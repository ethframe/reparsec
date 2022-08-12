from abc import abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

from .result import Result, SimpleResult
from .types import Ctx

S = TypeVar("S")
S_contra = TypeVar("S_contra", contravariant=True)
V = TypeVar("V")
V_co = TypeVar("V_co", covariant=True)


ParseFastFn = Callable[
    [S_contra, int, Ctx[S_contra]],
    SimpleResult[V_co, S_contra]
]
ParseFn = Callable[
    [S_contra, int, Ctx[S_contra], int, Optional[int]],
    Result[V_co, S_contra]
]


@dataclass(eq=False, frozen=True, repr=False)
class ParseFns(Generic[S_contra, V_co]):
    __slots__ = "fast_fn", "fn"

    fast_fn: ParseFastFn[S_contra, V_co]
    fn: ParseFn[S_contra, V_co]


class ParseObj(Generic[S_contra, V_co]):
    @abstractmethod
    def parse_fast_fn(
            self, stream: S_contra, pos: int,
            ctx: Ctx[S_contra]) -> SimpleResult[V_co, S_contra]:
        ...

    @abstractmethod
    def parse_fn(
            self, stream: S_contra, pos: int, ctx: Ctx[S_contra],
            ins: int, rem: Optional[int]) -> Result[V_co, S_contra]:
        ...

    def to_fns(self) -> ParseFns[S_contra, V_co]:
        return ParseFns(self.parse_fast_fn, self.parse_fn)
