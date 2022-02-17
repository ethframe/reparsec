from abc import abstractmethod
from typing import Generic, NamedTuple, Tuple, TypeVar

S_contra = TypeVar("S_contra", contravariant=True)


class Loc(NamedTuple):
    pos: int
    line: int
    col: int


class Ctx(Generic[S_contra]):
    __slots__ = "anchor", "loc"

    def __init__(self, anchor: int, loc: Loc):
        self.anchor = anchor
        self.loc = loc

    @abstractmethod
    def get_loc(
            self, stream: S_contra, pos: int) -> Tuple["Ctx[S_contra]", Loc]:
        ...

    @abstractmethod
    def set_anchor(
            self, stream: S_contra,
            pos: int) -> Tuple["Ctx[S_contra]", "Ctx[S_contra]"]:
        ...
