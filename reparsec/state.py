from abc import abstractmethod
from typing import Generic, NamedTuple, TypeVar

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
    def get_loc(self, stream: S_contra, pos: int) -> Loc:
        ...

    @abstractmethod
    def update_loc(self, stream: S_contra, pos: int) -> "Ctx[S_contra]":
        ...

    @abstractmethod
    def set_anchor(self, anchor: int) -> "Ctx[S_contra]":
        ...
