from typing import Callable, Generic, NamedTuple, TypeVar

S_contra = TypeVar("S_contra", contravariant=True)


class Loc(NamedTuple):
    pos: int
    line: int
    col: int


class Ctx(Generic[S_contra]):
    __slots__ = "anchor", "loc", "max_insertions", "_get_loc"

    def __init__(
            self, anchor: int, loc: Loc, max_insertions: int,
            get_loc: Callable[[Loc, S_contra, int], Loc]):
        self.anchor = anchor
        self.loc = loc
        self.max_insertions = max_insertions
        self._get_loc = get_loc

    def get_loc(self, stream: S_contra, pos: int) -> Loc:
        return self._get_loc(self.loc, stream, pos)

    def update_loc(self, stream: S_contra, pos: int) -> "Ctx[S_contra]":
        if pos == self.loc.pos:
            return self
        return Ctx(
            self.anchor, self._get_loc(self.loc, stream, pos),
            self.max_insertions, self._get_loc
        )

    def set_anchor(self, anchor: int) -> "Ctx[S_contra]":
        return Ctx(anchor, self.loc, self.max_insertions, self._get_loc)
